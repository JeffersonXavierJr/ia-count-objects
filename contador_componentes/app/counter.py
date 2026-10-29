"""Lógica de contagem e máquina de estados (Sprint 7, tarefas 7.1 a 7.3 do TASKS.md).

Responsabilidade única deste módulo (RNF-05/RNF-06): a partir das detecções já
produzidas por `detector.run_inference`,

1. filtrar pela classe selecionada (RB-01) — `filter_by_class`;
2. contar os objetos filtrados — `count_objects`;
3. comparar a quantidade detectada com a quantidade alvo (RB-02) e decidir o
   estado (RB-03) — `compare_counts` / `determinar_estado`.

É lógica PURA: não importa OpenCV, YOLO nem interface, e pode ser testada sem
modelo nem webcam. As detecções são tratadas por "duck typing" (qualquer objeto
com o atributo `classe_id`, como `detector.Deteccao`), justamente para não
puxar o `ultralytics` como dependência deste módulo.

4. (Sprint 8, PRD seção 16) estabilizar o estado ao longo dos frames —
   `EstabilizadorContagem`, que só reporta `QUANTIDADE ATINGIDA` /
   `QUANTIDADE EXCEDIDA` após N frames consecutivos
   (`config.FRAMES_ESTABILIZACAO`).

A contagem bruta (`count_objects`) é separada da decisão de estado
(`compare_counts`/`determinar_estado`); o estabilizador fica por cima das duas
e reaproveita `determinar_estado`/`compare_counts` sem alterá-las.

Uso típico pelo orquestrador (futuro `main.py`), a cada frame:

    estab = counter.EstabilizadorContagem()      # uma vez, na inicialização
    ...
    filtradas = counter.filter_by_class(deteccoes, cfg.classe)
    detectado = counter.count_objects(filtradas)
    estado = estab.atualizar(cfg, detectado,
                             erro_camera=..., modelo_carregado=...)
"""

from __future__ import annotations

import operator
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

# `config` só contém constantes (sem OpenCV/YOLO): importá-lo mantém este
# módulo puro. Alias para não colidir com os parâmetros chamados `config`.
from contador_componentes.app import config as app_config

# Classes contáveis da v1 (id -> nome). Espelha `detector.CLASSES_ESPERADAS`;
# é duplicado aqui de propósito para que este módulo não importe `detector`
# (que importa `ultralytics`). Um teste garante que os dois continuam iguais.
CLASSES: dict[int, str] = {0: "parafuso", 1: "porca"}


class Estado(Enum):
    """Estados da aplicação (RB-03). O valor é o texto exibido na interface."""

    AGUARDANDO_CONFIGURACAO = "AGUARDANDO CONFIGURAÇÃO"
    CONTANDO = "CONTANDO"
    QUANTIDADE_ATINGIDA = "QUANTIDADE ATINGIDA"
    # Não consta do RB-03 do PRD; acrescentado pelo TASKS.md (tarefa 7.3.2).
    QUANTIDADE_EXCEDIDA = "QUANTIDADE EXCEDIDA"
    # Estados de erro opcionais do RB-03.
    ERRO_CAMERA = "ERRO DE CÂMERA"
    MODELO_NAO_CARREGADO = "MODELO NÃO CARREGADO"


class _ComClasseId(Protocol):
    """Qualquer detecção com `classe_id` (ex.: `detector.Deteccao`)."""

    classe_id: int


def resolver_classe(classe: str | int) -> int:
    """Converte a classe selecionada (nome ou id) no id da classe.

    Aceita o nome (`"parafuso"`/`"porca"`, sem diferenciar maiúsculas e
    ignorando espaços nas pontas) OU o id inteiro (`0`/`1`). Aceitar o nome é
    o caso principal (é o que a interface mostra); o id é aceito por
    conveniência para quem já trabalha com a saída do modelo.

    Raises:
        ValueError: se a classe não for uma das classes da v1 (inclui `None`,
            string vazia, `bool` e ids fora de `CLASSES`).
    """
    if isinstance(classe, bool):  # bool é subclasse de int: rejeitar explicitamente
        raise ValueError(f"Classe invalida: {classe!r}.")
    if isinstance(classe, int):
        if classe in CLASSES:
            return classe
    elif isinstance(classe, str):
        nome = classe.strip().lower()
        for classe_id, nome_classe in CLASSES.items():
            if nome == nome_classe:
                return classe_id
    raise ValueError(
        f"Classe invalida: {classe!r}. Esperado um destes nomes/ids: "
        + ", ".join(f"{n!r} ({i})" for i, n in CLASSES.items())
        + "."
    )


def filter_by_class(
    detections: Iterable[_ComClasseId], classe_selecionada: str | int
) -> list[_ComClasseId]:
    """Mantém apenas as detecções da classe selecionada (RB-01).

    Detecções de qualquer outra classe são descartadas por completo — não
    entram na contagem exibida. A comparação é feita pelo `classe_id`, cujo
    mapeamento id -> nome é validado por `detector.load_model`.

    Args:
        detections: detecções do frame (ex.: retorno de `run_inference`).
        classe_selecionada: nome (`"parafuso"`/`"porca"`) ou id (`0`/`1`).

    Returns:
        Nova lista com as detecções da classe selecionada, na ordem original.

    Raises:
        ValueError: se `classe_selecionada` for inválida.
    """
    classe_id = resolver_classe(classe_selecionada)
    return [d for d in detections if d.classe_id == classe_id]


def count_objects(detections_filtradas: Iterable[object]) -> int:
    """Retorna a quantidade de objetos detectados (contagem bruta de um frame).

    Espera receber a saída de `filter_by_class`; não filtra por conta própria.
    """
    return sum(1 for _ in detections_filtradas)


def _validar_detectado(detectado: int) -> None:
    if isinstance(detectado, bool) or not isinstance(detectado, int) or detectado < 0:
        raise ValueError(
            f"Quantidade detectada invalida: {detectado!r} (esperado inteiro >= 0)."
        )


def _validar_esperado(esperado: int) -> None:
    if isinstance(esperado, bool) or not isinstance(esperado, int) or esperado <= 0:
        raise ValueError(
            f"Quantidade alvo invalida: {esperado!r} (esperado inteiro positivo)."
        )


def compare_counts(detectado: int, esperado: int | None) -> Estado:
    """Compara quantidade detectada x quantidade alvo (RB-02) e devolve o estado.

    - `esperado` é `None` (alvo não configurado) -> `AGUARDANDO_CONFIGURACAO`;
    - `detectado < esperado` -> `CONTANDO`;
    - `detectado == esperado` -> `QUANTIDADE_ATINGIDA`;
    - `detectado > esperado` -> `QUANTIDADE_EXCEDIDA`.

    Não considera erros de câmera/modelo nem a classe selecionada; para isso
    use `determinar_estado`.

    Raises:
        ValueError: se `detectado` não for inteiro >= 0 ou se `esperado`
            (quando informado) não for inteiro positivo.
    """
    _validar_detectado(detectado)
    if esperado is None:
        return Estado.AGUARDANDO_CONFIGURACAO
    _validar_esperado(esperado)
    if detectado < esperado:
        return Estado.CONTANDO
    if detectado == esperado:
        return Estado.QUANTIDADE_ATINGIDA
    return Estado.QUANTIDADE_EXCEDIDA


@dataclass(frozen=True)
class ConfiguracaoContagem:
    """Configuração corrente escolhida pelo usuário (não é persistida).

    Attributes:
        classe: classe selecionada (nome ou id), ou `None` se não escolhida.
        quantidade: quantidade alvo (inteiro positivo), ou `None` se não
            definida.

    Os valores são validados na criação (`ValueError` se inválidos). Como é
    imutável, trocar de configuração = criar outra instância — o que facilita
    a Sprint 8 detectar a troca e reiniciar a estabilização.
    """

    classe: str | int | None = None
    quantidade: int | None = None

    def __post_init__(self) -> None:
        if self.classe is not None:
            resolver_classe(self.classe)
        if self.quantidade is not None:
            _validar_esperado(self.quantidade)

    @property
    def configurada(self) -> bool:
        """`True` quando classe E quantidade alvo foram definidas."""
        return self.classe is not None and self.quantidade is not None


def determinar_estado(
    config: ConfiguracaoContagem,
    detectado: int,
    *,
    erro_camera: bool = False,
    modelo_carregado: bool = True,
) -> Estado:
    """Estado final da aplicação, com erros tendo prioridade sobre a contagem.

    Ordem de prioridade:
        1. `MODELO_NAO_CARREGADO` — sem modelo nada pode ser contado, e o
           problema só se resolve com ação do usuário (copiar `best.pt`).
        2. `ERRO_CAMERA` — falha (possivelmente transitória) de captura.
        3. `AGUARDANDO_CONFIGURACAO` — classe ou quantidade alvo não definida.
        4. Resultado de `compare_counts` (CONTANDO / ATINGIDA / EXCEDIDA).

    Conexão com os módulos existentes: o orquestrador deve passar
    `modelo_carregado=False` quando `detector.load_model` levantar
    `detector.ModelError`, e `erro_camera=True` quando `camera.open_camera` /
    `camera.read_frame` levantarem `camera.CameraError` (ver
    `estado_de_erro`). Em estado de erro, `detectado` é ignorado (use 0).

    Raises:
        ValueError: se `detectado` for inválido (só validado quando não há
            erro, pois em erro não existe contagem real).
    """
    if not modelo_carregado:
        return Estado.MODELO_NAO_CARREGADO
    if erro_camera:
        return Estado.ERRO_CAMERA
    if not config.configurada:
        _validar_detectado(detectado)
        return Estado.AGUARDANDO_CONFIGURACAO
    return compare_counts(detectado, config.quantidade)


def estado_de_erro(erro: BaseException) -> Estado | None:
    """Mapeia uma exceção do pipeline para o estado de erro correspondente.

    - `detector.ModelError` -> `MODELO_NAO_CARREGADO`;
    - `camera.CameraError` -> `ERRO_CAMERA`;
    - qualquer outra exceção -> `None` (não é um estado de erro previsto).

    Os imports são locais para que importar `counter` não carregue OpenCV nem
    `ultralytics`; quando esta função é chamada, o orquestrador já os carregou.
    """
    from contador_componentes.app.camera import CameraError
    from contador_componentes.app.detector import ModelError

    if isinstance(erro, ModelError):
        return Estado.MODELO_NAO_CARREGADO
    if isinstance(erro, CameraError):
        return Estado.ERRO_CAMERA
    return None


# --------------------------------------------------------------------------
# Sprint 8 — Estabilização da contagem (PRD seção 16, tarefas 8.1 e 8.3)
# --------------------------------------------------------------------------

# Estados que só são reportados após N frames consecutivos.
_ESTADOS_ESTABILIZADOS = (Estado.QUANTIDADE_ATINGIDA, Estado.QUANTIDADE_EXCEDIDA)


def _validar_n_frames(n_frames: int) -> int:
    if isinstance(n_frames, bool) or not isinstance(n_frames, int) or n_frames < 1:
        raise ValueError(
            f"Numero de frames de estabilizacao invalido: {n_frames!r} "
            "(esperado inteiro >= 1)."
        )
    return n_frames


def _normalizar_detectado(detectado: object) -> int:
    """Converte a contagem para `int` puro aceitando inteiros numpy.

    Usa `operator.index`, que aceita `int` e inteiros numpy (`numpy.int64`
    etc.) mas recusa `float`, `str` e `numpy.bool_`. `bool` nativo é recusado
    explicitamente (é subclasse de `int`).
    """
    if isinstance(detectado, bool):
        raise ValueError(
            f"Quantidade detectada invalida: {detectado!r} (esperado inteiro >= 0)."
        )
    try:
        valor = operator.index(detectado)  # type: ignore[arg-type]
    except TypeError:
        raise ValueError(
            f"Quantidade detectada invalida: {detectado!r} (esperado inteiro >= 0)."
        ) from None
    _validar_detectado(valor)
    return valor


def _chave_configuracao(config: ConfiguracaoContagem) -> tuple[int | None, int | None]:
    """Forma normalizada da configuração, para detectar troca de alvo.

    A classe é reduzida ao id, de modo que `"parafuso"`, `"Parafuso"` e `0`
    contam como a MESMA configuração (não reiniciam a estabilização).
    """
    classe_id = None if config.classe is None else resolver_classe(config.classe)
    return (classe_id, config.quantidade)


class EstabilizadorContagem:
    """Estabiliza o estado da contagem ao longo dos frames (PRD seção 16).

    Mantém o histórico das últimas N contagens brutas (`collections.deque`
    com `maxlen=N`) e aplica as regras abaixo a cada chamada de `atualizar`:

    - `QUANTIDADE_ATINGIDA` só é reportado quando as últimas N leituras são
      todas iguais ao alvo.
    - `QUANTIDADE_EXCEDIDA` só é reportado quando as últimas N leituras estão
      todas acima do alvo (não precisam ser o mesmo valor: 13, 14, 13... com
      alvo 12 é "excedido" de forma estável).
    - Em qualquer outro caso com configuração completa o estado é
      `CONTANDO` — inclusive enquanto a sequência ainda não completou N
      frames. Não há histerese de saída: uma única leitura fora do alvo
      derruba ATINGIDA/EXCEDIDA para CONTANDO e a sequência recomeça do zero
      (tarefa 8.3.1). Isso é conservador (não diz "atingida" sem certeza);
      se na validação experimental (tarefa 8.2) a saída oscilar demais,
      ajustar aqui.
    - `MODELO_NAO_CARREGADO`, `ERRO_CAMERA` e `AGUARDANDO_CONFIGURACAO` são
      imediatos (sem espera), com a mesma prioridade de `determinar_estado`.

    Frames com erro (câmera/modelo) ou sem configuração completa LIMPAM o
    histórico: não houve contagem real naquele frame, então a sequência de
    frames consecutivos é quebrada e, ao voltar ao normal, recomeça do zero.

    Troca de configuração (classe ou quantidade alvo) é detectada
    automaticamente comparando com a configuração da chamada anterior e
    também reinicia o histórico (tarefa 8.3.2). `reiniciar()` faz o mesmo
    sob demanda (ex.: botão de reset, RB-05).

    Não persiste nada além do estado corrente (sem histórico em banco).

    Args:
        n_frames: N, número de frames consecutivos exigido. `None` (padrão)
            usa `config.FRAMES_ESTABILIZACAO`, lido no momento da criação.

    Raises:
        ValueError: se `n_frames` não for inteiro >= 1.
    """

    def __init__(self, n_frames: int | None = None) -> None:
        if n_frames is None:
            n_frames = app_config.FRAMES_ESTABILIZACAO
        self._n_frames = _validar_n_frames(n_frames)
        self._historico: deque[int] = deque(maxlen=self._n_frames)
        self._chave_config: tuple[int | None, int | None] | None = None
        self._ultima_contagem: int | None = None
        self._frames_consecutivos = 0
        self._estado = Estado.AGUARDANDO_CONFIGURACAO

    # ------------------------------------------------------------ leitura
    @property
    def n_frames(self) -> int:
        """N configurado (frames consecutivos exigidos)."""
        return self._n_frames

    @property
    def historico(self) -> tuple[int, ...]:
        """Cópia das últimas leituras válidas (no máximo N, mais antiga primeiro)."""
        return tuple(self._historico)

    @property
    def ultima_contagem(self) -> int | None:
        """Contagem bruta do último frame válido; `None` após erro/reinício."""
        return self._ultima_contagem

    @property
    def frames_consecutivos(self) -> int:
        """Quantos frames seguidos (até N) mantêm o mesmo resultado da última
        leitura em relação ao alvo (abaixo / igual / acima). Útil para exibir
        progresso, ex.: "estabilizando 3/5". 0 sem configuração ou após erro.
        """
        return self._frames_consecutivos

    @property
    def estado(self) -> Estado:
        """Último estado devolvido por `atualizar`."""
        return self._estado

    # ------------------------------------------------------------ ações
    def reiniciar(self) -> None:
        """Descarta o histórico e volta a exigir N frames (ex.: botão RESET).

        Não altera N nem esquece a configuração corrente; o estado volta a
        `AGUARDANDO_CONFIGURACAO` até a próxima chamada de `atualizar`.
        """
        self._historico.clear()
        self._ultima_contagem = None
        self._frames_consecutivos = 0
        self._estado = Estado.AGUARDANDO_CONFIGURACAO

    def atualizar(
        self,
        config: ConfiguracaoContagem,
        detectado: int,
        *,
        erro_camera: bool = False,
        modelo_carregado: bool = True,
    ) -> Estado:
        """Registra a contagem bruta de um frame e devolve o estado estável.

        Args:
            config: configuração corrente (classe e quantidade alvo).
            detectado: contagem bruta do frame (`count_objects`). Aceita `int`
                ou inteiro numpy; `bool`/`float` são recusados. Ignorado (e
                não validado) quando há erro de câmera/modelo.
            erro_camera: `True` se a captura deste frame falhou.
            modelo_carregado: `False` se o modelo não pôde ser carregado.

        Returns:
            O estado estabilizado (ver docstring da classe).

        Raises:
            ValueError: se `detectado` for inválido (nesse caso o estado
                interno não é alterado).
        """
        em_erro = (not modelo_carregado) or erro_camera
        if not em_erro:
            detectado = _normalizar_detectado(detectado)

        chave = _chave_configuracao(config)
        if chave != self._chave_config:
            self.reiniciar()
            self._chave_config = chave

        # Reaproveita a regra/prioridade da Sprint 7 para o estado "bruto".
        estado_bruto = determinar_estado(
            config,
            0 if em_erro else detectado,
            erro_camera=erro_camera,
            modelo_carregado=modelo_carregado,
        )

        if em_erro or estado_bruto is Estado.AGUARDANDO_CONFIGURACAO:
            # Sem contagem válida contra um alvo: quebra a sequência.
            self._historico.clear()
            self._frames_consecutivos = 0
            self._ultima_contagem = None if em_erro else detectado
            self._estado = estado_bruto
            return estado_bruto

        self._historico.append(detectado)
        self._ultima_contagem = detectado

        # Classifica cada leitura do histórico (abaixo/igual/acima do alvo)
        # com `compare_counts` e conta quantas das mais recentes coincidem
        # com a leitura atual.
        consecutivos = 0
        for contagem in reversed(self._historico):
            if compare_counts(contagem, config.quantidade) is not estado_bruto:
                break
            consecutivos += 1
        self._frames_consecutivos = consecutivos

        if estado_bruto in _ESTADOS_ESTABILIZADOS and consecutivos >= self._n_frames:
            self._estado = estado_bruto
        else:
            self._estado = Estado.CONTANDO
        return self._estado
