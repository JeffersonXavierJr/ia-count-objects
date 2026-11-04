"""Interface local Tkinter/ttk (Sprint 9, tarefa 9.1 do TASKS.md).

Responsabilidade única deste módulo (RNF-05/RNF-06): APRESENTAR o estado da
aplicação e EMITIR eventos do usuário. A janela roda no mesmo computador e no
mesmo processo em que a webcam está conectada (TASKS.md, Sprint 9).

O que este módulo faz:
- exibe o frame JÁ ANOTADO (bounding boxes desenhadas por `overlay.py`),
  redimensionado para caber na área de vídeo SEM distorcer (letterbox);
- oferece o seletor de componente (somente `Parafuso` / `Porca`, RB-01), o
  campo de quantidade desejada (somente inteiros positivos) e o botão RESET
  (RB-05);
- mostra a quantidade detectada, a desejada, o status textual (RB-03) com cor
  por estado e, opcionalmente, o progresso da estabilização
  ("estabilizando 3/5").

O que este módulo NÃO faz (fica em outros módulos):
- abrir câmera, rodar YOLO, contar, estabilizar ou decidir estado
  (`camera.py`, `detector.py`, `counter.py`);
- criar threads ou loops: quem chama (`main.py`) entrega os dados SEMPRE na
  thread principal do Tk (via `root.after`); o Tkinter não é thread-safe;
- gravar contagens, logs de uso ou histórico (fora do escopo da v1);
- acionar hardware: o RESET só emite o callback; a descarga é manual (RB-04).

Contrato usado pelo orquestrador (`main.py`):

    ui = InterfaceContador(root, on_config_change=..., on_reset=..., on_close=...)
    ui.mostrar_frame(frame_bgr_ou_None)
    ui.atualizar_painel(detectado, esperado, estado, frames_consecutivos, n_frames)

Conversão do frame para o Tk sem dependência nova: o frame BGR é
redimensionado com `cv2.resize` (uma vez por atualização), convertido para
RGB e entregue a `tk.PhotoImage` como bytes PPM binário (P6), formato lido
nativamente pelo Tk 8.6. Não usa Pillow.

As partes lógicas (validação da quantidade, cálculo do letterbox, mapeamento
estado -> texto/cor, texto de progresso, conversão para PPM) são funções
puras no nível do módulo e podem ser testadas sem abrir janela.

PONTOS EM ABERTO (perguntar ao time, não inventar):
- Layout final da janela (PRD seção 29, item 13; tarefa 9.1.6): o layout
  abaixo (vídeo à esquerda, painel lateral à direita; painel vai para baixo
  do vídeo em janelas estreitas) é uma PROPOSTA PROVISÓRIA e ainda precisa
  ser validado pelo time. Paleta, tamanhos e `minsize` também são
  provisórios.
- Método definitivo de reset (PRD seção 29, item 14): o botão RESET na
  janela é apenas o baseline.
- Quantidade máxima de componentes (PRD seção 29, item 6): respeitada via
  `config.QUANTIDADE_MAXIMA`, que por enquanto é `None` (sem limite).
- Resolução/tamanho da tela do computador final (PRD seção 29, item 11).

Observação: o PRD/CLAUDE.md ainda descrevem o Home Assistant como interface;
esta interface local segue o TASKS.md (Sprint 9), que substitui aquela
decisão na v1.
"""

from __future__ import annotations

import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from tkinter import ttk

import cv2
import numpy as np

from contador_componentes.app import config as app_config
from contador_componentes.app.counter import CLASSES, Estado

# ---------------------------------------------------------------------------
# Tema (único lugar com cores, fontes e espaçamentos) — PROVISÓRIO (PRD 29.13)
# ---------------------------------------------------------------------------

TEMA: dict[str, str] = {
    "fundo": "#F4F5F7",          # fundo neutro da janela
    "painel": "#FFFFFF",         # fundo do painel lateral
    "video_fundo": "#1E1F22",    # faixas do letterbox / placeholder
    "texto": "#1F2328",
    "texto_secundario": "#5F6670",
    "texto_placeholder": "#9AA0A6",
    "destaque": "#2563EB",       # cor de destaque (botão RESET, foco)
    "destaque_ativo": "#1D4ED8",
    "borda": "#D0D4DA",
}

# Cor de fundo / cor do texto do "selo" de status por estado. A cor nunca é o
# único sinal: o texto do estado (`Estado.value`) sempre aparece junto.
CORES_ESTADO: dict[Estado, tuple[str, str]] = {
    Estado.AGUARDANDO_CONFIGURACAO: ("#E3E5E8", "#1F2328"),  # neutro
    Estado.CONTANDO: ("#2563EB", "#FFFFFF"),                 # azul
    Estado.QUANTIDADE_ATINGIDA: ("#16A34A", "#FFFFFF"),      # verde
    Estado.QUANTIDADE_EXCEDIDA: ("#F59E0B", "#1F2328"),      # âmbar
    Estado.ERRO_CAMERA: ("#DC2626", "#FFFFFF"),              # vermelho
    Estado.MODELO_NAO_CARREGADO: ("#DC2626", "#FFFFFF"),     # vermelho
}

# Multiplicadores de tamanho em relação à `TkDefaultFont` do sistema (não se
# fixa família: usa-se a fonte padrão de cada plataforma).
ESCALA_FONTE: dict[str, float] = {
    "contagem": 6.0,     # quantidade detectada: o maior número da tela
    "desejado": 2.6,
    "status": 1.5,
    "titulo": 1.1,
    "legenda": 1.0,
}

# Espaçamento base (px a 96 DPI); todos os espaços são múltiplos dele.
ESPACO = 8

# Tamanho inicial e mínimo da janela (px a 96 DPI; o mínimo efetivo é
# aumentado, se preciso, para caber o painel) — PROVISÓRIOS (PRD 29.11 e
# 29.13: tela do computador final e layout ainda não definidos).
TAMANHO_INICIAL = (1100, 680)
TAMANHO_MINIMO = (560, 520)

# Abaixo desta largura (px a 96 DPI) o painel vai para baixo do vídeo.
LARGURA_LAYOUT_ESTREITO = 820

# Altura mínima reservada ao vídeo (px a 96 DPI), inclusive no layout estreito.
ALTURA_MINIMA_VIDEO = 200

# Largura mínima do painel lateral (px a 96 DPI).
LARGURA_MINIMA_PAINEL = 300

TEXTO_SEM_VALOR = "—"
TEXTO_SEM_IMAGEM = "Sem imagem da câmera"

_RE_INTEIRO_POSITIVO = re.compile(r"[1-9][0-9]*")


# ---------------------------------------------------------------------------
# Funções puras (testáveis sem janela)
# ---------------------------------------------------------------------------


def habilitar_dpi_awareness() -> None:
    """Liga o DPI awareness no Windows para a janela não ficar borrada.

    Deve ser chamada pelo `main.py` ANTES de criar o `tk.Tk()`. Em outros
    sistemas (ou se a API não existir) não faz nada. Nunca levanta exceção.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - API ausente em Windows antigos
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass


def texto_quantidade_aceitavel(texto: str, maximo: int | None = None) -> bool:
    """Diz se `texto` pode ficar no campo de quantidade durante a digitação.

    Aceita o campo vazio (o usuário está apagando/redigitando) ou um inteiro
    positivo sem zeros à esquerda e, se `maximo` não for `None`, menor ou
    igual a `maximo`. Recusa sinais, espaços, decimais, letras e `0`.
    Usada no `validatecommand` do campo (validação a cada tecla).
    """
    if texto == "":
        return True
    if not _RE_INTEIRO_POSITIVO.fullmatch(texto):
        return False
    return maximo is None or int(texto) <= maximo


def interpretar_quantidade(texto: str, maximo: int | None = None) -> int | None:
    """Converte o texto do campo em quantidade desejada.

    Returns:
        O inteiro positivo (respeitando `maximo`, se houver) ou `None` se o
        texto estiver vazio ou inválido.
    """
    texto = texto.strip()
    if texto == "" or not texto_quantidade_aceitavel(texto, maximo):
        return None
    return int(texto)


def calcular_tamanho_letterbox(
    largura_origem: int, altura_origem: int, largura_area: int, altura_area: int
) -> tuple[int, int]:
    """Maior tamanho (largura, altura) que cabe na área mantendo a proporção.

    O resultado tem sempre pelo menos 1x1 px (mesmo com área ainda não
    dimensionada, ex.: 1x1 antes do primeiro `<Configure>`).

    Raises:
        ValueError: se o tamanho de origem não for positivo.
    """
    if largura_origem <= 0 or altura_origem <= 0:
        raise ValueError(
            f"Tamanho de origem invalido: {largura_origem}x{altura_origem}."
        )
    largura_area = max(1, int(largura_area))
    altura_area = max(1, int(altura_area))
    escala = min(largura_area / largura_origem, altura_area / altura_origem)
    largura = max(1, min(largura_area, round(largura_origem * escala)))
    altura = max(1, min(altura_area, round(altura_origem * escala)))
    return largura, altura


def redimensionar_letterbox(
    frame_bgr: np.ndarray, largura_area: int, altura_area: int
) -> np.ndarray:
    """Redimensiona o frame para caber na área sem distorcer (uma única vez).

    Usa `INTER_AREA` ao reduzir (melhor qualidade e rápido) e `INTER_LINEAR`
    ao ampliar. Se o tamanho já for o desejado, devolve o próprio frame.
    """
    altura_origem, largura_origem = frame_bgr.shape[:2]
    largura, altura = calcular_tamanho_letterbox(
        largura_origem, altura_origem, largura_area, altura_area
    )
    if (largura, altura) == (largura_origem, altura_origem):
        return frame_bgr
    interpolacao = cv2.INTER_AREA if largura < largura_origem else cv2.INTER_LINEAR
    return cv2.resize(frame_bgr, (largura, altura), interpolation=interpolacao)


def frame_para_ppm(frame_bgr: np.ndarray) -> bytes:
    """Converte um frame do OpenCV (BGR, BGRA ou cinza, uint8) em PPM P6 (RGB).

    O PPM binário é lido nativamente por `tk.PhotoImage(data=..., format="PPM")`,
    dispensando o Pillow.

    Raises:
        ValueError: se o frame não for uint8 com 1, 3 ou 4 canais.
    """
    if not isinstance(frame_bgr, np.ndarray) or frame_bgr.dtype != np.uint8:
        raise ValueError("Frame invalido: esperado numpy.ndarray uint8.")
    if frame_bgr.ndim == 2:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_GRAY2RGB)
    elif frame_bgr.ndim == 3 and frame_bgr.shape[2] == 3:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    elif frame_bgr.ndim == 3 and frame_bgr.shape[2] == 4:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGRA2RGB)
    else:
        raise ValueError(f"Frame invalido: shape {frame_bgr.shape}.")
    altura, largura = rgb.shape[:2]
    cabecalho = f"P6 {largura} {altura} 255\n".encode("ascii")
    return cabecalho + np.ascontiguousarray(rgb).tobytes()


def estilo_do_estado(estado: Estado) -> tuple[str, str, str]:
    """Mapeia o estado em (texto exibido, cor de fundo, cor do texto).

    O texto é o próprio `Estado.value` (ex.: "QUANTIDADE ATINGIDA").
    """
    fundo, texto = CORES_ESTADO[estado]
    return estado.value, fundo, texto


def formatar_quantidade(valor: int | None) -> str:
    """Texto de uma quantidade no painel (`None` -> travessão)."""
    return TEXTO_SEM_VALOR if valor is None else str(valor)


def texto_estabilizacao(
    estado: Estado,
    detectado: int | None,
    esperado: int | None,
    frames_consecutivos: int,
    n_frames: int,
) -> str:
    """Texto opcional de progresso da estabilização (ex.: "estabilizando 3/5").

    Regra só de APRESENTAÇÃO (o estado em si vem pronto do `counter.py`):
    aparece apenas em `CONTANDO`, quando o detectado já alcançou ou passou o
    desejado (ou seja, o sistema está confirmando ATINGIDA/EXCEDIDA) e a
    sequência ainda não completou N. `n_frames <= 1` (sem estabilização) ou
    valores ausentes -> texto vazio.
    """
    if (
        estado is not Estado.CONTANDO
        or detectado is None
        or esperado is None
        or n_frames <= 1
        or detectado < esperado
        or not 0 < frames_consecutivos < n_frames
    ):
        return ""
    return f"estabilizando {frames_consecutivos}/{n_frames}"


def _fonte_derivada(base: tkfont.Font, fator: float, negrito: bool = False) -> tkfont.Font:
    """Cria uma fonte a partir da padrão do sistema, escalando o tamanho.

    O Tk usa tamanho positivo em pontos e negativo em pixels; o sinal é
    preservado para respeitar a convenção da plataforma.
    """
    tamanho = int(base.cget("size")) or 10
    sinal = -1 if tamanho < 0 else 1
    nova = base.copy()
    nova.configure(
        size=sinal * max(1, round(abs(tamanho) * fator)),
        weight="bold" if negrito else "normal",
    )
    return nova


# ---------------------------------------------------------------------------
# Janela
# ---------------------------------------------------------------------------


class InterfaceContador:
    """Janela principal: vídeo anotado + painel de status + controles.

    Todos os métodos públicos devem ser chamados SOMENTE na thread principal
    do Tk. A classe não cria threads e não conhece câmera, detector nem
    contador; só apresenta dados e chama os callbacks.

    Args:
        root: janela raiz já criada pelo `main.py`.
        on_config_change: chamado com `(classe, quantidade)` quando o usuário
            troca o componente (`"parafuso"`/`"porca"`) ou confirma a
            quantidade (Enter, setas do campo ou saída de foco). `classe` é
            `None` enquanto nada foi selecionado; `quantidade` é `None` se o
            campo estiver vazio/inválido. Chamadas repetidas com o mesmo par
            são suprimidas.
        on_reset: chamado pelo botão RESET (RB-05). Só emite o evento.
        on_close: chamado ao fechar a janela (WM_DELETE_WINDOW) para o
            `main.py` liberar a câmera; nesse caso é ELE quem deve destruir a
            janela (`root.destroy()`). Se `None`, a janela é destruída aqui.
    """

    def __init__(
        self,
        root: tk.Tk,
        *,
        on_config_change: Callable[[str | None, int | None], None],
        on_reset: Callable[[], None],
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self._root = root
        self._on_config_change = on_config_change
        self._on_reset = on_reset
        self._on_close = on_close
        self._maximo = app_config.QUANTIDADE_MAXIMA
        self._destruida = False

        # Escala de DPI (1.0 a 96 DPI) para espaçamentos/tamanhos em px.
        try:
            self._escala = max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
        except tk.TclError:
            self._escala = 1.0

        # Estado de apresentação (só para evitar redesenho desnecessário).
        self._ultimo_frame: np.ndarray | None = None
        self._photo: tk.PhotoImage | None = None
        self._tamanho_photo: tuple[int, int] | None = None
        self._area_video = (1, 1)
        self._redesenho_pendente: str | None = None
        self._layout_estreito: bool | None = None
        self._ultima_config_emitida: tuple[str | None, int | None] = (None, None)
        self._painel_atual: dict[str, object] = {}

        self._configurar_janela()
        self._configurar_estilos()
        self._construir_widgets()
        self._aplicar_layout(estreito=False)
        self._ajustar_tamanho_minimo()

        # Estado inicial: sem componente, sem quantidade, aguardando config.
        self.mostrar_frame(None)
        self.atualizar_painel(None, None, Estado.AGUARDANDO_CONFIGURACAO)

        root.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        root.bind("<Configure>", self._ao_redimensionar_janela, add="+")
        root.bind("<Destroy>", self._ao_destruir, add="+")

    # ------------------------------------------------------------ API pública
    def mostrar_frame(self, frame_bgr: np.ndarray | None) -> None:
        """Exibe o frame anotado (BGR) ou, com `None`, o placeholder.

        O frame é redimensionado uma única vez para a área de vídeo atual,
        mantendo a proporção. Só o último frame é guardado (nada é
        enfileirado) para reexibição quando a janela muda de tamanho.
        """
        if self._destruida:
            return
        self._ultimo_frame = frame_bgr
        try:
            self._desenhar_frame()
        except tk.TclError:
            # A janela pode ter sido destruída entre o agendamento e a chamada.
            pass

    def atualizar_painel(
        self,
        detectado: int | None,
        esperado: int | None,
        estado: Estado,
        frames_consecutivos: int = 0,
        n_frames: int = 0,
    ) -> None:
        """Atualiza quantidades, status e progresso de estabilização.

        Só reconfigura os widgets cujos valores mudaram.
        """
        if self._destruida:
            return
        texto_estado = estilo_do_estado(estado)[0]
        novos = {
            "detectado": formatar_quantidade(detectado),
            "esperado": formatar_quantidade(esperado),
            "estado": estado,
            "progresso": texto_estabilizacao(
                estado, detectado, esperado, frames_consecutivos, n_frames
            ),
        }
        try:
            if self._painel_atual.get("detectado") != novos["detectado"]:
                self._lbl_detectado.configure(text=novos["detectado"])
            if self._painel_atual.get("esperado") != novos["esperado"]:
                self._lbl_esperado.configure(text=novos["esperado"])
            if self._painel_atual.get("estado") is not estado:
                self._lbl_status.configure(
                    text=texto_estado, style=self._nome_estilo_status(estado)
                )
            if self._painel_atual.get("progresso") != novos["progresso"]:
                self._lbl_progresso.configure(text=novos["progresso"])
        except tk.TclError:
            return
        self._painel_atual = novos

    # ----------------------------------------------- acesso para testes/uso
    @property
    def classe_selecionada(self) -> str | None:
        """Componente selecionado (`"parafuso"`/`"porca"`) ou `None`."""
        valor = self._var_classe.get()
        return valor if valor in CLASSES.values() else None

    @property
    def quantidade_desejada(self) -> int | None:
        """Quantidade válida no campo, ou `None`."""
        return interpretar_quantidade(self._var_quantidade.get(), self._maximo)

    # ------------------------------------------------------------ construção
    def _px(self, valor: float) -> int:
        return max(0, round(valor * self._escala))

    def _configurar_janela(self) -> None:
        root = self._root
        root.title("Contador de Componentes")
        largura, altura = TAMANHO_INICIAL
        root.geometry(f"{self._px(largura)}x{self._px(altura)}")
        root.configure(background=TEMA["fundo"])
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

    def _configurar_estilos(self) -> None:
        estilo = ttk.Style(self._root)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        base = tkfont.nametofont("TkDefaultFont", root=self._root)
        self._fontes = {
            "contagem": _fonte_derivada(base, ESCALA_FONTE["contagem"], negrito=True),
            "desejado": _fonte_derivada(base, ESCALA_FONTE["desejado"], negrito=True),
            "status": _fonte_derivada(base, ESCALA_FONTE["status"], negrito=True),
            "titulo": _fonte_derivada(base, ESCALA_FONTE["titulo"], negrito=True),
            "legenda": _fonte_derivada(base, ESCALA_FONTE["legenda"]),
        }

        estilo.configure("TFrame", background=TEMA["fundo"])
        estilo.configure("Painel.TFrame", background=TEMA["painel"])
        estilo.configure("Video.TFrame", background=TEMA["video_fundo"])
        estilo.configure(
            "TLabel", background=TEMA["painel"], foreground=TEMA["texto"]
        )
        estilo.configure(
            "Video.TLabel",
            background=TEMA["video_fundo"],
            foreground=TEMA["texto_placeholder"],
            font=self._fontes["titulo"],
            anchor="center",
        )
        estilo.configure(
            "Legenda.TLabel",
            background=TEMA["painel"],
            foreground=TEMA["texto_secundario"],
            font=self._fontes["legenda"],
        )
        estilo.configure(
            "Titulo.TLabel", background=TEMA["painel"], font=self._fontes["titulo"]
        )
        estilo.configure(
            "Contagem.TLabel", background=TEMA["painel"], font=self._fontes["contagem"]
        )
        estilo.configure(
            "Desejado.TLabel", background=TEMA["painel"], font=self._fontes["desejado"]
        )
        estilo.configure("TSeparator", background=TEMA["borda"])
        estilo.configure(
            "TRadiobutton",
            background=TEMA["painel"],
            foreground=TEMA["texto"],
            font=self._fontes["legenda"],
            indicatorsize=self._px(12),
        )
        estilo.map("TRadiobutton", background=[("active", TEMA["painel"])])
        estilo.configure("TSpinbox", padding=self._px(4), arrowsize=self._px(14))
        estilo.configure(
            "Reset.TButton",
            background=TEMA["destaque"],
            foreground="#FFFFFF",
            font=self._fontes["titulo"],
            padding=(self._px(16), self._px(8)),
            borderwidth=0,
            focuscolor=TEMA["destaque_ativo"],
        )
        estilo.map(
            "Reset.TButton",
            background=[("pressed", TEMA["destaque_ativo"]), ("active", TEMA["destaque_ativo"])],
            foreground=[("disabled", TEMA["texto_placeholder"])],
        )
        # Um estilo de "selo" por estado; trocar o estilo troca as cores.
        for estado in Estado:
            _, fundo, cor_texto = estilo_do_estado(estado)
            estilo.configure(
                self._nome_estilo_status(estado),
                background=fundo,
                foreground=cor_texto,
                font=self._fontes["status"],
                anchor="center",
                padding=(self._px(12), self._px(8)),
            )

    @staticmethod
    def _nome_estilo_status(estado: Estado) -> str:
        return f"Status{estado.name.title().replace('_', '')}.TLabel"

    def _construir_widgets(self) -> None:
        root = self._root
        e = self._px(ESPACO)

        self._conteudo = ttk.Frame(root, padding=e * 2)
        self._conteudo.grid(row=0, column=0, sticky="nsew")

        # --- Área de vídeo: o rótulo é posicionado com `place` no centro,
        # para que o tamanho da imagem NÃO realimente o tamanho do grid
        # (evita laço de redimensionamento).
        self._area = ttk.Frame(self._conteudo, style="Video.TFrame")
        self._lbl_video = ttk.Label(self._area, style="Video.TLabel")
        self._lbl_video.place(relx=0.5, rely=0.5, anchor="center")
        self._area.bind("<Configure>", self._ao_redimensionar_video)

        # --- Painel: dois blocos (status/contagens e controles). Em janela
        # larga ficam empilhados à direita do vídeo; em janela estreita o
        # painel vai para baixo do vídeo e os blocos ficam lado a lado, para
        # o vídeo não perder toda a altura.
        self._painel = ttk.Frame(
            self._conteudo, style="Painel.TFrame", padding=e * 2
        )
        self._bloco_status = ttk.Frame(self._painel, style="Painel.TFrame")
        self._bloco_status.columnconfigure(0, weight=1)
        self._separador = ttk.Separator(self._painel)
        self._bloco_controles = ttk.Frame(self._painel, style="Painel.TFrame")
        self._bloco_controles.columnconfigure(0, weight=1)

        b = self._bloco_status
        self._lbl_status = ttk.Label(b, anchor="center")
        self._lbl_status.grid(row=0, column=0, sticky="ew")

        ttk.Label(b, text="Quantidade detectada", style="Legenda.TLabel").grid(
            row=1, column=0, sticky="w", pady=(e * 2, 0)
        )
        self._lbl_detectado = ttk.Label(b, style="Contagem.TLabel")
        self._lbl_detectado.grid(row=2, column=0, sticky="w")

        ttk.Label(b, text="Quantidade desejada", style="Legenda.TLabel").grid(
            row=3, column=0, sticky="w", pady=(e, 0)
        )
        self._lbl_esperado = ttk.Label(b, style="Desejado.TLabel")
        self._lbl_esperado.grid(row=4, column=0, sticky="w")

        self._lbl_progresso = ttk.Label(b, style="Legenda.TLabel")
        self._lbl_progresso.grid(row=5, column=0, sticky="w", pady=(e, 0))

        b = self._bloco_controles
        # Seletor de componente (RB-01): somente as classes da v1.
        ttk.Label(b, text="Componente", style="Titulo.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._var_classe = tk.StringVar(root, value="")  # nada selecionado
        linha_classes = ttk.Frame(b, style="Painel.TFrame")
        linha_classes.grid(row=1, column=0, sticky="w", pady=(e // 2, e * 2))
        self._radios: dict[str, ttk.Radiobutton] = {}
        for coluna, classe_id in enumerate(sorted(CLASSES)):
            nome = CLASSES[classe_id]
            radio = ttk.Radiobutton(
                linha_classes,
                text=nome.capitalize(),
                value=nome,
                variable=self._var_classe,
                command=self._emitir_config,
            )
            radio.grid(row=0, column=coluna, sticky="w", padx=(0, e * 2))
            self._radios[nome] = radio

        # Quantidade desejada: só inteiros positivos (validação por tecla).
        ttk.Label(b, text="Definir quantidade", style="Titulo.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        self._var_quantidade = tk.StringVar(root, value="")
        validar = (root.register(self._validar_tecla_quantidade), "%P")
        self._spin_quantidade = ttk.Spinbox(
            b,
            from_=1,
            # PONTO EM ABERTO (PRD 29.6): sem limite enquanto
            # `config.QUANTIDADE_MAXIMA` for None.
            to=float("inf") if self._maximo is None else self._maximo,
            increment=1,
            textvariable=self._var_quantidade,
            validate="key",
            validatecommand=validar,
            command=self._emitir_config,  # setas do Spinbox
            font=self._fontes["titulo"],
            width=8,
        )
        self._spin_quantidade.grid(row=3, column=0, sticky="ew", pady=(e // 2, 0))
        self._spin_quantidade.bind("<Return>", self._emitir_config_evento)
        self._spin_quantidade.bind("<KP_Enter>", self._emitir_config_evento)
        self._spin_quantidade.bind("<FocusOut>", self._emitir_config_evento)

        dica = "Enter para confirmar"
        if self._maximo is not None:
            dica += f" (máx. {self._maximo})"
        ttk.Label(b, text=dica, style="Legenda.TLabel").grid(
            row=4, column=0, sticky="w", pady=(e // 2, e * 2)
        )

        # RESET (RB-05) — baseline; método definitivo em aberto (PRD 29.14).
        self._btn_reset = ttk.Button(
            b, text="RESET", style="Reset.TButton", command=self._ao_reset
        )
        self._btn_reset.grid(row=5, column=0, sticky="ew")

    def _aplicar_layout(self, *, estreito: bool) -> None:
        """Vídeo à esquerda e painel à direita; em janelas estreitas, o painel
        vai para baixo do vídeo (blocos lado a lado). Só reorganiza se o modo
        mudar."""
        if estreito == self._layout_estreito:
            return
        self._layout_estreito = estreito
        e = self._px(ESPACO)
        c, p = self._conteudo, self._painel
        for indice in range(3):
            for alvo in (c, p):
                alvo.columnconfigure(indice, weight=0, minsize=0)
                alvo.rowconfigure(indice, weight=0, minsize=0)
        self._area.grid(row=0, column=0, sticky="nsew")
        c.columnconfigure(0, weight=1)
        c.rowconfigure(0, weight=1, minsize=self._px(ALTURA_MINIMA_VIDEO))
        if estreito:
            self._painel.grid(row=1, column=0, sticky="nsew", pady=(e * 2, 0), padx=0)
            self._bloco_status.grid(row=0, column=0, sticky="nsew")
            self._separador.configure(orient="vertical")
            self._separador.grid(row=0, column=1, sticky="ns", padx=e * 2, pady=0)
            self._bloco_controles.grid(row=0, column=2, sticky="nsew")
            p.columnconfigure(0, weight=1)
            p.columnconfigure(2, weight=1)
        else:
            self._painel.grid(row=0, column=1, sticky="nsew", padx=(e * 2, 0), pady=0)
            self._bloco_status.grid(row=0, column=0, sticky="new")
            self._separador.configure(orient="horizontal")
            self._separador.grid(row=1, column=0, sticky="ew", padx=0, pady=e * 2)
            self._bloco_controles.grid(row=2, column=0, sticky="sew")
            p.columnconfigure(0, weight=1)
            # Espaço elástico entre os blocos: controles no pé do painel.
            p.rowconfigure(1, weight=1)
            c.columnconfigure(1, weight=0, minsize=self._px(LARGURA_MINIMA_PAINEL))

    def _ajustar_tamanho_minimo(self) -> None:
        """Define o `minsize` da janela a partir do tamanho pedido pelos
        widgets nos dois layouts, para os controles nunca se sobreporem."""
        root = self._root
        borda = self._px(ESPACO) * 4  # padding do conteúdo (2 lados)
        espaco = self._px(ESPACO) * 2
        estreito_atual = bool(self._layout_estreito)
        self._aplicar_layout(estreito=True)
        root.update_idletasks()
        larg_estreito = self._painel.winfo_reqwidth()
        alt_estreito = self._painel.winfo_reqheight()
        self._aplicar_layout(estreito=False)
        root.update_idletasks()
        alt_largo = self._painel.winfo_reqheight()
        self._aplicar_layout(estreito=estreito_atual)
        largura = max(self._px(TAMANHO_MINIMO[0]), larg_estreito + borda)
        altura = max(
            self._px(TAMANHO_MINIMO[1]),
            alt_largo + borda,
            alt_estreito + self._px(ALTURA_MINIMA_VIDEO) + espaco + borda,
        )
        root.minsize(largura, altura)

    # ------------------------------------------------------------ desenho
    def _desenhar_frame(self) -> None:
        frame = self._ultimo_frame
        if frame is None:
            self._photo = None
            self._tamanho_photo = None
            self._lbl_video.configure(image="", text=TEXTO_SEM_IMAGEM)
            return
        largura_area, altura_area = self._area_video
        reduzido = redimensionar_letterbox(frame, largura_area, altura_area)
        dados = frame_para_ppm(reduzido)
        tamanho = (reduzido.shape[1], reduzido.shape[0])
        if self._photo is None or self._tamanho_photo != tamanho:
            # Nova imagem só quando o tamanho muda; a referência fica em
            # `self._photo` para o Tk não perder a imagem por coleta de lixo.
            self._photo = tk.PhotoImage(master=self._root, data=dados, format="PPM")
            self._tamanho_photo = tamanho
            self._lbl_video.configure(image=self._photo, text="")
        else:
            self._photo.configure(data=dados, format="PPM")

    def _ao_redimensionar_video(self, evento: tk.Event) -> None:
        novo = (max(1, int(evento.width)), max(1, int(evento.height)))
        if novo == self._area_video:
            return
        self._area_video = novo
        # Agrupa vários <Configure> seguidos em um único redesenho.
        if self._redesenho_pendente is None and self._ultimo_frame is not None:
            self._redesenho_pendente = self._root.after_idle(self._redesenhar_pendente)

    def _redesenhar_pendente(self) -> None:
        self._redesenho_pendente = None
        if self._destruida:
            return
        try:
            self._desenhar_frame()
        except tk.TclError:
            pass

    def _ao_redimensionar_janela(self, evento: tk.Event) -> None:
        if evento.widget is not self._root or self._destruida:
            return
        self._aplicar_layout(estreito=evento.width < self._px(LARGURA_LAYOUT_ESTREITO))

    # ------------------------------------------------------------ eventos
    def _validar_tecla_quantidade(self, texto_proposto: str) -> bool:
        return texto_quantidade_aceitavel(texto_proposto, self._maximo)

    def _emitir_config_evento(self, _evento: tk.Event | None = None) -> None:
        self._emitir_config()

    def _emitir_config(self) -> None:
        """Emite `on_config_change` se o par (classe, quantidade) mudou."""
        if self._destruida:
            return
        par = (self.classe_selecionada, self.quantidade_desejada)
        if par == self._ultima_config_emitida:
            return
        self._ultima_config_emitida = par
        self._on_config_change(*par)

    def _ao_reset(self) -> None:
        if not self._destruida:
            self._on_reset()

    def _ao_fechar(self) -> None:
        """WM_DELETE_WINDOW: avisa o `main.py` (liberar câmera) ou destrói."""
        if self._on_close is not None:
            self._on_close()
            return
        try:
            self._root.destroy()
        except tk.TclError:
            pass

    def _ao_destruir(self, evento: tk.Event) -> None:
        if evento.widget is not self._root:
            return
        self._destruida = True
        self._photo = None
        if self._redesenho_pendente is not None:
            try:
                self._root.after_cancel(self._redesenho_pendente)
            except tk.TclError:
                pass
            self._redesenho_pendente = None
