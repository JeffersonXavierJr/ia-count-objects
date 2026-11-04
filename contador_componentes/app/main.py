"""Orquestração da aplicação (Sprint 9, tarefa 9.2 do TASKS.md).

Ponto de entrada da v1 (a partir da raiz do repositório, com o venv ativo):

    python -m contador_componentes.app.main

Conecta os módulos existentes, sem reimplementar nenhum deles:

    camera.read_frame -> camera.apply_roi -> detector.run_inference
    -> counter.filter_by_class / count_objects -> EstabilizadorContagem.atualizar
    -> overlay.draw_detections -> interface (frame anotado + painel)

Na v1 NÃO há MQTT nem streaming de vídeo (TASKS.md, Sprint 9): a interface
Tkinter (`interface.py`) roda no mesmo processo e recebe o resultado direto
do pipeline.

Organização (lógica testável separada da parte Tk):

- `Orquestrador` — lógica de um frame (`processar_frame`) e de um erro
  (`processar_erro`), sem câmera, modelo nem Tk; guarda a configuração
  corrente (classe/quantidade) de forma thread-safe.
- `GerenciadorCamera` — abre/lê/libera a webcam garantindo que cada câmera
  aberta seja liberada exatamente uma vez.
- `PipelineWorker` — thread daemon com o loop captura + inferência +
  contagem, incluindo reconexão da câmera.
- `CaixaUltimoResultado` — "fila de tamanho 1": guarda só o resultado mais
  recente; resultados antigos são descartados.
- `AplicacaoContador` — lado Tk: consome a caixa via `root.after` e repassa
  os callbacks da interface ao orquestrador/worker.

Concorrência (tarefa 9.2.3): captura + inferência rodam numa thread worker e
a thread do Tk só consulta o resultado mais recente a cada
`config.INTERVALO_ATUALIZACAO_INTERFACE_MS`. Essa abordagem foi escolhida por
ser robusta a QUALQUER FPS, porque o FPS da tarefa 6.4 ainda NÃO foi medido
(pendência humana). REVISAR quando a 6.4 for medida: se a inferência for
rápida o bastante, um loop único via `after` seria mais simples; se for
lenta, esta estrutura já evita que a janela trave.

Regras de thread:
- Todos os métodos da interface são chamados SOMENTE na thread do Tk.
- O `EstabilizadorContagem` é usado SOMENTE na thread worker; o RESET da
  interface apenas marca um pedido, aplicado pelo worker no próximo frame.
- Troca de componente/quantidade (9.2.4) substitui a `ConfiguracaoContagem`
  compartilhada (protegida por lock); o estabilizador detecta a troca e
  reinicia a estabilização sozinho.

Bounding boxes exibidas (decisão documentada): quando há classe selecionada,
só as detecções DESSA classe são desenhadas — o que se vê na imagem é
exatamente o que entra na contagem exibida (RB-01), evitando que o operador
conte caixas de porca ao contar parafusos. Sem classe selecionada
(`AGUARDANDO CONFIGURAÇÃO`), todas as detecções são desenhadas, para que o
operador possa conferir o detector antes de configurar.

A imagem exibida é o RECORTE DA ROI anotado (mesmo critério de
`scripts/pipeline_ao_vivo.py`); o redimensionamento para caber na janela é
responsabilidade da interface.

Erros (RB-03):
- `detector.ModelError` ao carregar o modelo -> `MODELO NÃO CARREGADO`
  exibido na janela; a aplicação continua aberta (sem nova tentativa: o
  problema só se resolve copiando o `best.pt` e reiniciando a aplicação).
- `camera.CameraError` ao abrir/ler -> `ERRO DE CÂMERA`, com nova tentativa
  de abrir a cada `config.INTERVALO_RECONEXAO_CAMERA_S`. ROI incompatível
  com a resolução capturada (`ValueError` de `apply_roi`) também é tratada
  como `ERRO DE CÂMERA`, pois o frame recebido é inutilizável.

Nada é persistido (sem banco de dados nem histórico de contagens).
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Any

import numpy as np

from contador_componentes.app import config
from contador_componentes.app.camera import (
    CameraError,
    apply_roi,
    open_camera,
    read_frame,
    release_camera,
)
from contador_componentes.app.counter import (
    ConfiguracaoContagem,
    EstabilizadorContagem,
    Estado,
    count_objects,
    estado_de_erro,
    filter_by_class,
)
from contador_componentes.app.detector import ModelError, load_model, run_inference
from contador_componentes.app.overlay import draw_detections

logger = logging.getLogger(__name__)

# Função de inferência já ligada ao modelo carregado: frame -> detecções.
Inferir = Callable[[np.ndarray], Sequence[Any]]


@dataclass(frozen=True)
class ResultadoFrame:
    """Resultado de um ciclo do pipeline, pronto para a interface.

    Attributes:
        frame_anotado: recorte da ROI com as bounding boxes, ou `None` em
            estado de erro (a interface mostra um placeholder).
        detectado: contagem bruta da classe selecionada no frame; `None` sem
            classe selecionada ou em erro.
        esperado: quantidade alvo configurada (ou `None`).
        estado: estado estabilizado (`EstabilizadorContagem`).
        frames_consecutivos: progresso da estabilização (ex.: 3 de 5).
        n_frames: N exigido pela estabilização.
    """

    frame_anotado: np.ndarray | None
    detectado: int | None
    esperado: int | None
    estado: Estado
    frames_consecutivos: int = 0
    n_frames: int = 0


class Orquestrador:
    """Lógica de cada frame, sem câmera, modelo nem Tk (testável isolada).

    `definir_configuracao` e `solicitar_reset` podem ser chamados de qualquer
    thread (ex.: a do Tk). `processar_frame`/`processar_erro` devem ser
    chamados por UMA thread só (a worker), pois usam o estabilizador.

    Args:
        estabilizador: instância a usar; `None` cria uma com
            `config.FRAMES_ESTABILIZACAO`.
        aplicar_roi: função de recorte (padrão `camera.apply_roi`).
        desenhar: função de desenho (padrão `overlay.draw_detections`).
    """

    def __init__(
        self,
        estabilizador: EstabilizadorContagem | None = None,
        *,
        aplicar_roi: Callable[[np.ndarray], np.ndarray] = apply_roi,
        desenhar: Callable[[np.ndarray, Sequence[Any]], np.ndarray] = draw_detections,
    ) -> None:
        self._estabilizador = estabilizador or EstabilizadorContagem()
        self._aplicar_roi = aplicar_roi
        self._desenhar = desenhar
        self._lock = threading.Lock()
        self._configuracao = ConfiguracaoContagem()
        self._reset_pendente = False

    # ----------------------------------------------- chamados pela thread do Tk
    @property
    def configuracao(self) -> ConfiguracaoContagem:
        """Configuração corrente (cópia imutável)."""
        with self._lock:
            return self._configuracao

    @property
    def n_frames(self) -> int:
        """N da estabilização (imutável; seguro de ler de qualquer thread)."""
        return self._estabilizador.n_frames

    def definir_configuracao(self, classe: str | None, quantidade: int | None) -> None:
        """Troca componente/quantidade em tempo real (tarefa 9.2.4).

        A estabilização reinicia automaticamente no próximo frame, pois o
        `EstabilizadorContagem` detecta a troca de configuração.

        Raises:
            ValueError: se classe/quantidade forem inválidas (a configuração
                anterior é mantida).
        """
        nova = ConfiguracaoContagem(classe=classe, quantidade=quantidade)
        with self._lock:
            self._configuracao = nova
        logger.info("Configuracao alterada: classe=%r, quantidade=%r.", classe, quantidade)

    def solicitar_reset(self) -> None:
        """Pede o reinício da contagem (botão RESET, RB-05).

        Apenas marca o pedido; o worker chama `EstabilizadorContagem.reiniciar`
        no próximo frame. A configuração (classe/quantidade) é mantida: após
        a descarga manual, a mesma contagem recomeça do zero.
        """
        with self._lock:
            self._reset_pendente = True
        logger.info("Reset da contagem solicitado.")

    # ------------------------------------------------- chamados pela worker
    def _consumir_configuracao(self) -> ConfiguracaoContagem:
        """Lê a configuração corrente e aplica um reset pendente, se houver."""
        with self._lock:
            configuracao = self._configuracao
            reset = self._reset_pendente
            self._reset_pendente = False
        if reset:
            self._estabilizador.reiniciar()
        return configuracao

    def processar_frame(self, frame: np.ndarray, inferir: Inferir) -> ResultadoFrame:
        """ROI -> inferência -> filtragem/contagem -> estabilização -> desenho.

        Args:
            frame: frame BGR completo vindo da câmera.
            inferir: função frame -> detecções (ex.: `run_inference` já ligada
                ao modelo carregado).

        Raises:
            ValueError: se a ROI não couber no frame ou o frame for vazio
                (propagado de `apply_roi`/`run_inference`).
        """
        configuracao = self._consumir_configuracao()
        recorte = self._aplicar_roi(frame)
        deteccoes = list(inferir(recorte))

        if configuracao.classe is None:
            # Nada a contar; todas as caixas são desenhadas (ver docstring).
            visiveis = deteccoes
            detectado: int | None = None
        else:
            # RB-01: somente a classe selecionada é contada e desenhada.
            visiveis = filter_by_class(deteccoes, configuracao.classe)
            detectado = count_objects(visiveis)

        estado = self._estabilizador.atualizar(
            configuracao, 0 if detectado is None else detectado
        )
        return ResultadoFrame(
            frame_anotado=self._desenhar(recorte, visiveis),
            detectado=detectado,
            esperado=configuracao.quantidade,
            estado=estado,
            frames_consecutivos=self._estabilizador.frames_consecutivos,
            n_frames=self._estabilizador.n_frames,
        )

    def processar_erro(self, erro: BaseException) -> ResultadoFrame:
        """Registra um erro de câmera/modelo no estabilizador e monta o resultado.

        Usa `counter.estado_de_erro` para mapear a exceção e as flags do
        estabilizador (`erro_camera`/`modelo_carregado`), que quebram a
        sequência de frames consecutivos.

        Raises:
            ValueError: se `erro` não for `CameraError` nem `ModelError`.
        """
        estado_erro = estado_de_erro(erro)
        if estado_erro is None:
            raise ValueError(f"Erro nao previsto pela maquina de estados: {erro!r}") from erro

        configuracao = self._consumir_configuracao()
        estado = self._estabilizador.atualizar(
            configuracao,
            0,
            erro_camera=estado_erro is Estado.ERRO_CAMERA,
            modelo_carregado=estado_erro is not Estado.MODELO_NAO_CARREGADO,
        )
        return ResultadoFrame(
            frame_anotado=None,
            detectado=None,
            esperado=configuracao.quantidade,
            estado=estado,
            frames_consecutivos=0,
            n_frames=self._estabilizador.n_frames,
        )


class CaixaUltimoResultado:
    """Guarda apenas o resultado mais recente (equivale a fila de tamanho 1).

    O worker sobrescreve; a thread do Tk retira. Se o Tk atrasar, resultados
    intermediários são descartados — a tela mostra sempre o estado atual.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._resultado: ResultadoFrame | None = None

    def publicar(self, resultado: ResultadoFrame) -> None:
        with self._lock:
            self._resultado = resultado

    def retirar(self) -> ResultadoFrame | None:
        """Devolve o resultado mais recente ainda não consumido (ou `None`)."""
        with self._lock:
            resultado, self._resultado = self._resultado, None
        return resultado


class GerenciadorCamera:
    """Abre, lê e libera a webcam de forma segura entre threads.

    Garante que cada câmera aberta seja liberada EXATAMENTE uma vez, mesmo
    que o worker (ao terminar) e o fechamento da janela (após o join) tentem
    liberar: a referência é trocada por `None` sob lock antes de liberar.
    Depois de `encerrar()`, nenhuma câmera nova é aberta.

    Args:
        abrir/ler/liberar: funções de `camera.py` (substituíveis em testes).
    """

    def __init__(
        self,
        abrir: Callable[[], Any] = open_camera,
        ler: Callable[[Any], np.ndarray] = read_frame,
        liberar: Callable[[Any], None] = release_camera,
    ) -> None:
        self._abrir = abrir
        self._ler = ler
        self._liberar = liberar
        self._lock = threading.Lock()
        self._camera: Any = None
        self._encerrado = False

    def ler_frame(self) -> np.ndarray:
        """Lê um frame, abrindo a câmera antes se necessário.

        Raises:
            CameraError: falha ao abrir/ler, ou gerenciador já encerrado.
        """
        with self._lock:
            if self._encerrado:
                raise CameraError("Camera ja encerrada.")
            camera = self._camera

        if camera is None:
            # Abertura fora do lock (pode demorar) para não bloquear `encerrar`.
            camera = self._abrir()
            with self._lock:
                encerrado_no_meio = self._encerrado
                if not encerrado_no_meio:
                    self._camera = camera
            if encerrado_no_meio:
                self._liberar(camera)
                raise CameraError("Camera encerrada durante a abertura.")

        return self._ler(camera)

    def descartar(self) -> None:
        """Libera a câmera atual (após falha) para tentar reabrir depois."""
        with self._lock:
            camera, self._camera = self._camera, None
        if camera is not None:
            self._liberar(camera)

    def encerrar(self) -> None:
        """Libera a câmera (se aberta) e impede novas aberturas. Idempotente."""
        with self._lock:
            self._encerrado = True
            camera, self._camera = self._camera, None
        if camera is not None:
            self._liberar(camera)


def _carregar_inferencia_padrao() -> Inferir:
    """Carrega o modelo de `config.MODEL_PATH` e devolve a função de inferência.

    Raises:
        ModelError: modelo ausente/incompatível (ver `detector.load_model`).
    """
    modelo = load_model()
    return partial(run_inference, modelo)


class PipelineWorker:
    """Thread daemon: carrega o modelo e roda captura + inferência + contagem.

    Publica cada resultado na `CaixaUltimoResultado`. O modelo é carregado na
    própria thread para que a janela abra sem esperar o `ultralytics`.

    Args:
        orquestrador: lógica de frame/erro.
        caixa: destino dos resultados.
        camera: gerenciador da webcam.
        carregar_inferencia: devolve a função de inferência ou levanta
            `ModelError` (padrão: `detector.load_model` + `run_inference`).
        intervalo_reconexao_s: espera entre tentativas após erro de câmera
            (padrão `config.INTERVALO_RECONEXAO_CAMERA_S`).
    """

    def __init__(
        self,
        orquestrador: Orquestrador,
        caixa: CaixaUltimoResultado,
        camera: GerenciadorCamera,
        *,
        carregar_inferencia: Callable[[], Inferir] = _carregar_inferencia_padrao,
        intervalo_reconexao_s: float | None = None,
    ) -> None:
        self._orquestrador = orquestrador
        self._caixa = caixa
        self._camera = camera
        self._carregar_inferencia = carregar_inferencia
        self._intervalo = (
            config.INTERVALO_RECONEXAO_CAMERA_S
            if intervalo_reconexao_s is None
            else intervalo_reconexao_s
        )
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------ controle
    def iniciar(self) -> None:
        """Inicia a thread daemon (não bloqueia)."""
        self._thread = threading.Thread(
            target=self.executar, name="pipeline-contador", daemon=True
        )
        self._thread.start()

    def sinalizar_parada(self) -> None:
        self._parar.set()

    def aguardar(self, timeout: float | None = None) -> bool:
        """Faz join da thread; `True` se ela terminou (ou nunca iniciou)."""
        if self._thread is None:
            return True
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def liberar_camera(self) -> None:
        """Libera a câmera definitivamente (idempotente)."""
        self._camera.encerrar()

    # ------------------------------------------------------------ loop
    def executar(self) -> None:
        """Corpo da thread. Sempre libera a câmera ao sair."""
        try:
            self._executar()
        except Exception:  # noqa: BLE001 - não deixar a thread morrer em silêncio
            logger.exception("Erro inesperado no pipeline; worker encerrado.")
        finally:
            self._camera.encerrar()

    def _publicar_erro(self, erro: BaseException) -> None:
        self._caixa.publicar(self._orquestrador.processar_erro(erro))

    def _executar(self) -> None:
        try:
            inferir = self._carregar_inferencia()
        except ModelError as erro:
            logger.error("%s", erro)
            # A janela continua aberta exibindo MODELO NÃO CARREGADO. O estado
            # é republicado periodicamente para refletir mudanças de
            # configuração (quantidade esperada) no painel.
            self._publicar_erro(erro)
            while not self._parar.wait(self._intervalo):
                self._publicar_erro(erro)
            return

        while not self._parar.is_set():
            try:
                frame = self._camera.ler_frame()
            except CameraError as erro:
                if self._parar.is_set():
                    break
                logger.warning(
                    "%s Nova tentativa de abrir a camera em %.1f s.", erro, self._intervalo
                )
                self._camera.descartar()
                self._publicar_erro(erro)
                self._parar.wait(self._intervalo)
                continue

            try:
                resultado = self._orquestrador.processar_frame(frame, inferir)
            except ValueError as erro:
                # ROI incompatível com a resolução / frame vazio: frame inutilizável.
                logger.error(
                    "%s Ajuste config.ROI (python -m "
                    "contador_componentes.scripts.calibrar_roi).",
                    erro,
                )
                self._publicar_erro(CameraError(f"Frame inutilizavel: {erro}"))
                self._parar.wait(self._intervalo)
                continue
            except Exception:  # noqa: BLE001 - falha pontual de inferência
                logger.exception("Falha ao processar frame; tentando o proximo.")
                self._parar.wait(self._intervalo)
                continue

            self._caixa.publicar(resultado)


class AplicacaoContador:
    """Lado Tk: liga interface, orquestrador e worker.

    Tudo aqui roda na thread principal do Tk. A interface é criada por
    `criar_interface(root, on_config_change=..., on_reset=..., on_close=...)`
    (normalmente `interface.InterfaceContador`; substituível em testes).
    """

    def __init__(
        self,
        root: Any,
        orquestrador: Orquestrador,
        caixa: CaixaUltimoResultado,
        worker: PipelineWorker,
        *,
        criar_interface: Callable[..., Any],
        intervalo_ms: int | None = None,
        timeout_encerramento_s: float | None = None,
    ) -> None:
        self._root = root
        self._orquestrador = orquestrador
        self._caixa = caixa
        self._worker = worker
        self._intervalo_ms = (
            config.INTERVALO_ATUALIZACAO_INTERFACE_MS if intervalo_ms is None else intervalo_ms
        )
        self._timeout_s = (
            config.TIMEOUT_ENCERRAMENTO_WORKER_S
            if timeout_encerramento_s is None
            else timeout_encerramento_s
        )
        self._id_after: Any = None
        self._encerrado = False
        self._interface = criar_interface(
            root,
            on_config_change=self._ao_mudar_configuracao,
            on_reset=self._ao_resetar,
            on_close=self.encerrar,
        )

    def iniciar(self) -> None:
        """Mostra o estado inicial, inicia o worker e agenda o consumo."""
        self._interface.mostrar_frame(None)
        self._interface.atualizar_painel(
            None, None, Estado.AGUARDANDO_CONFIGURACAO, 0, self._orquestrador.n_frames
        )
        self._worker.iniciar()
        self._agendar()

    def _agendar(self) -> None:
        self._id_after = self._root.after(self._intervalo_ms, self._consumir)

    def _consumir(self) -> None:
        """Exibe o resultado mais recente (se houver) e reagenda."""
        if self._encerrado:
            return
        resultado = self._caixa.retirar()
        if resultado is not None:
            self._interface.mostrar_frame(resultado.frame_anotado)
            self._interface.atualizar_painel(
                resultado.detectado,
                resultado.esperado,
                resultado.estado,
                resultado.frames_consecutivos,
                resultado.n_frames,
            )
        self._agendar()

    def _ao_mudar_configuracao(self, classe: str | None, quantidade: int | None) -> None:
        try:
            self._orquestrador.definir_configuracao(classe, quantidade)
        except ValueError as erro:
            # A interface deveria validar; se não validou, mantém a anterior.
            logger.warning("Configuracao ignorada: %s", erro)

    def _ao_resetar(self) -> None:
        self._orquestrador.solicitar_reset()

    def encerrar(self) -> None:
        """Fechamento da janela (9.2.5). Idempotente.

        Sinaliza parada, faz join do worker com timeout, libera a câmera
        (exatamente uma vez, via `GerenciadorCamera`) e destrói a janela.
        Se o join estourar o timeout (inferência travada), a câmera é
        liberada mesmo assim — a thread é daemon e morre com o processo.
        """
        if self._encerrado:
            return
        self._encerrado = True

        if self._id_after is not None:
            try:
                self._root.after_cancel(self._id_after)
            except Exception:  # noqa: BLE001 - janela pode já estar destruída
                pass
            self._id_after = None

        self._worker.sinalizar_parada()
        if not self._worker.aguardar(self._timeout_s):
            logger.warning(
                "Worker nao terminou em %.1f s; liberando a camera mesmo assim.",
                self._timeout_s,
            )
        self._worker.liberar_camera()

        try:
            self._root.destroy()
        except Exception:  # noqa: BLE001 - ex.: tkinter.TclError se já destruída
            logger.debug("Janela ja havia sido destruida.")
        logger.info("Aplicacao encerrada.")


def main() -> int:
    """Cria a janela Tk, inicia o pipeline e entra no loop do Tk."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Imports locais: Tk e a interface só são necessários na aplicação real
    # (os testes usam `AplicacaoContador` com fakes, sem display).
    import tkinter as tk

    from contador_componentes.app.interface import (
        InterfaceContador,
        habilitar_dpi_awareness,
    )

    # Precisa vir ANTES de criar o Tk (senão a janela fica borrada no Windows).
    habilitar_dpi_awareness()
    root = tk.Tk()
    orquestrador = Orquestrador()
    caixa = CaixaUltimoResultado()
    worker = PipelineWorker(orquestrador, caixa, GerenciadorCamera())
    aplicacao = AplicacaoContador(
        root, orquestrador, caixa, worker, criar_interface=InterfaceContador
    )
    aplicacao.iniciar()
    try:
        root.mainloop()
    finally:
        # Cobre saídas do mainloop sem passar por on_close (ex.: Ctrl+C).
        aplicacao.encerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
