"""Ferramenta de calibracao visual da ROI (Sprint 6, tarefa 6.1.3 do TASKS.md).

Exibe o stream ao vivo da webcam (via `app/camera.py`) com o retangulo da ROI
desenhado por cima, permite ajusta-lo com o mouse e/ou teclado, e mostra numa
segunda janela o resultado do recorte (`camera.apply_roi`). Ao pressionar `p`
(ou Enter), imprime no terminal a linha exata para colar em `app/config.py`.

Este script NAO grava `config.py` automaticamente: a decisao de travar as
coordenadas (tarefa 6.1.1) e de quem opera a ferramenta, com a camera ja na
posicao fisica definitiva.

As coordenadas sao sempre exibidas e impressas em pixels do frame ORIGINAL
capturado (ex.: 1920x1080), mesmo que a janela seja exibida reduzida para
caber na tela.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m contador_componentes.scripts.calibrar_roi

Controles:
    mouse (botao esquerdo) - arrastar para desenhar um novo retangulo
    w / a / s / d          - mover o retangulo (cima / esquerda / baixo / direita)
    j / l                  - diminuir / aumentar a largura
    i / k                  - diminuir / aumentar a altura
    f                      - alternar passo do teclado (fino 1 px / grosso 10 px)
    r                      - resetar para o frame inteiro
    p ou Enter             - imprimir a linha `ROI = (...)` para colar em config.py
    q ou Esc               - encerrar
"""

from __future__ import annotations

import logging
import sys

import cv2
import numpy as np

from contador_componentes.app import config
from contador_componentes.app.camera import (
    CameraError,
    apply_roi,
    open_camera,
    read_frame,
    release_camera,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WINDOW_NAME = "Calibracao da ROI"
PREVIEW_WINDOW_NAME = "Recorte da ROI (previa)"

# Tamanho maximo das janelas de exibicao. Frames maiores (ex.: 1080p) sao
# reduzidos apenas para exibicao; as coordenadas continuam no frame original.
MAX_LARGURA_JANELA = 1280
MAX_ALTURA_JANELA = 720

PASSO_FINO = 1
PASSO_GROSSO = 10
TAMANHO_MINIMO = 2  # px; arrastos menores que isso sao ignorados (clique simples)

COR_RETANGULO = (0, 255, 0)
COR_TEXTO = (0, 255, 255)

Roi = tuple[int, int, int, int]


def _escala_exibicao(largura: int, altura: int) -> float:
    """Fator de reducao para que o frame caiba na janela (nunca amplia)."""
    return min(1.0, MAX_LARGURA_JANELA / largura, MAX_ALTURA_JANELA / altura)


def _redimensionar(imagem: np.ndarray, escala: float) -> np.ndarray:
    if escala >= 1.0:
        return imagem
    altura, largura = imagem.shape[:2]
    return cv2.resize(
        imagem,
        (max(1, round(largura * escala)), max(1, round(altura * escala))),
        interpolation=cv2.INTER_AREA,
    )


def _limitar_roi(roi: Roi, largura_frame: int, altura_frame: int) -> Roi:
    """Mantem a ROI dentro do frame, com tamanho minimo de 1 px."""
    x, y, largura, altura = roi
    largura = min(max(largura, 1), largura_frame)
    altura = min(max(altura, 1), altura_frame)
    x = min(max(x, 0), largura_frame - largura)
    y = min(max(y, 0), altura_frame - altura)
    return (x, y, largura, altura)


def _roi_inicial(largura_frame: int, altura_frame: int) -> Roi:
    """ROI de partida: `config.ROI` se valida para este frame, senao o frame inteiro."""
    frame_inteiro = (0, 0, largura_frame, altura_frame)

    if config.ROI is None:
        logger.info("config.ROI = None (ROI desativada). Partindo do frame inteiro.")
        return frame_inteiro

    try:
        x, y, largura, altura = (int(v) for v in config.ROI)
        if largura <= 0 or altura <= 0:
            raise ValueError
    except (TypeError, ValueError):
        logger.warning("config.ROI invalida (%r). Partindo do frame inteiro.", config.ROI)
        return frame_inteiro

    if x >= largura_frame or y >= altura_frame or x + largura <= 0 or y + altura <= 0:
        logger.warning(
            "config.ROI %r fica fora do frame de %dx%d (calibrada para outra "
            "resolucao?). Partindo do frame inteiro.",
            config.ROI, largura_frame, altura_frame,
        )
        return frame_inteiro

    # Interseccao com o frame, para nao distorcer o retangulo ao limitar.
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + largura, largura_frame), min(y + altura, altura_frame)
    logger.info("Partindo de config.ROI = %r.", config.ROI)
    return (x0, y0, x1 - x0, y1 - y0)


class _EstadoMouse:
    """Estado do arrasto do mouse, em coordenadas do frame original."""

    def __init__(self, escala: float, largura_frame: int, altura_frame: int) -> None:
        self.escala = escala
        self.largura_frame = largura_frame
        self.altura_frame = altura_frame
        self.arrastando = False
        self.inicio: tuple[int, int] = (0, 0)
        self.atual: tuple[int, int] = (0, 0)
        self.roi_nova: Roi | None = None  # preenchida ao soltar o botao

    def _para_frame(self, x: int, y: int) -> tuple[int, int]:
        """Converte coordenadas da janela (possivelmente reduzida) para o frame original."""
        fx = round(x / self.escala)
        fy = round(y / self.escala)
        return (min(max(fx, 0), self.largura_frame), min(max(fy, 0), self.altura_frame))

    def retangulo_em_arrasto(self) -> Roi:
        (xa, ya), (xb, yb) = self.inicio, self.atual
        return (min(xa, xb), min(ya, yb), abs(xb - xa), abs(yb - ya))

    def callback(self, evento: int, x: int, y: int, _flags: int, _param: object) -> None:
        if evento == cv2.EVENT_LBUTTONDOWN:
            self.arrastando = True
            self.inicio = self.atual = self._para_frame(x, y)
        elif evento == cv2.EVENT_MOUSEMOVE and self.arrastando:
            self.atual = self._para_frame(x, y)
        elif evento == cv2.EVENT_LBUTTONUP and self.arrastando:
            self.arrastando = False
            self.atual = self._para_frame(x, y)
            retangulo = self.retangulo_em_arrasto()
            if retangulo[2] >= TAMANHO_MINIMO and retangulo[3] >= TAMANHO_MINIMO:
                self.roi_nova = retangulo


def _desenhar_overlay(
    frame: np.ndarray, roi: Roi, escala: float, passo: int
) -> np.ndarray:
    """Desenha a ROI e as coordenadas sobre uma copia reduzida do frame."""
    exibicao = _redimensionar(frame, escala).copy()
    x, y, largura, altura = roi
    p0 = (round(x * escala), round(y * escala))
    p1 = (round((x + largura) * escala) - 1, round((y + altura) * escala) - 1)
    cv2.rectangle(exibicao, p0, p1, COR_RETANGULO, 2)

    altura_frame, largura_frame = frame.shape[:2]
    linhas = [
        f"ROI = {roi}  (frame {largura_frame}x{altura_frame})",
        f"passo: {passo}px | wasd mover | j/l largura | i/k altura | f passo",
        "mouse: arrastar | r reset | p/Enter imprimir | q sair",
    ]
    for i, texto in enumerate(linhas):
        origem = (10, 25 + 25 * i)
        cv2.putText(exibicao, texto, origem, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(exibicao, texto, origem, cv2.FONT_HERSHEY_SIMPLEX, 0.6, COR_TEXTO, 1, cv2.LINE_AA)
    return exibicao


def _aplicar_tecla(tecla: int, roi: Roi, passo: int) -> Roi:
    """Move/redimensiona a ROI conforme a tecla (sem limitar ao frame)."""
    x, y, largura, altura = roi
    ajustes = {
        ord("w"): (0, -passo, 0, 0),
        ord("s"): (0, passo, 0, 0),
        ord("a"): (-passo, 0, 0, 0),
        ord("d"): (passo, 0, 0, 0),
        ord("j"): (0, 0, -passo, 0),
        ord("l"): (0, 0, passo, 0),
        ord("i"): (0, 0, 0, -passo),
        ord("k"): (0, 0, 0, passo),
    }
    dx, dy, dl, da = ajustes.get(tecla, (0, 0, 0, 0))
    return (x + dx, y + dy, largura + dl, altura + da)


def main() -> int:
    try:
        camera = open_camera()
    except CameraError as erro:
        logger.error("%s", erro)
        return 1

    try:
        try:
            frame = read_frame(camera)
        except CameraError as erro:
            logger.error("%s Encerrando a calibracao.", erro)
            return 1

        altura_frame, largura_frame = frame.shape[:2]
        escala = _escala_exibicao(largura_frame, altura_frame)
        logger.info(
            "Resolucao do frame capturado: %dx%d (exibicao em escala %.2f). "
            "As coordenadas da ROI sao sempre em pixels do frame capturado.",
            largura_frame, altura_frame, escala,
        )

        roi = _roi_inicial(largura_frame, altura_frame)
        passo = PASSO_GROSSO
        mouse = _EstadoMouse(escala, largura_frame, altura_frame)

        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(PREVIEW_WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW_NAME, mouse.callback)

        while True:
            if mouse.roi_nova is not None:
                roi = _limitar_roi(mouse.roi_nova, largura_frame, altura_frame)
                mouse.roi_nova = None

            roi_exibida = mouse.retangulo_em_arrasto() if mouse.arrastando else roi
            if roi_exibida[2] < 1 or roi_exibida[3] < 1:
                roi_exibida = roi

            cv2.imshow(WINDOW_NAME, _desenhar_overlay(frame, roi_exibida, escala, passo))
            recorte = apply_roi(frame, roi_exibida)
            cv2.imshow(
                PREVIEW_WINDOW_NAME,
                _redimensionar(recorte, _escala_exibicao(recorte.shape[1], recorte.shape[0])),
            )

            tecla = cv2.waitKey(1) & 0xFF

            if tecla in (ord("q"), 27):
                logger.info("Encerrando a calibracao (nenhum arquivo foi alterado).")
                break
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("Janela fechada. Encerrando a calibracao.")
                break

            if tecla in (ord("p"), 13, 10):
                print(
                    "\nCole a linha abaixo em contador_componentes/app/config.py "
                    f"(calibrada em frame {largura_frame}x{altura_frame}):\n"
                    f"ROI = {roi}\n",
                    flush=True,
                )
            elif tecla == ord("f"):
                passo = PASSO_FINO if passo == PASSO_GROSSO else PASSO_GROSSO
            elif tecla == ord("r"):
                roi = (0, 0, largura_frame, altura_frame)
            elif tecla != 0xFF:
                roi = _limitar_roi(_aplicar_tecla(tecla, roi, passo), largura_frame, altura_frame)

            try:
                frame = read_frame(camera)
            except CameraError as erro:
                logger.error("%s Encerrando a calibracao.", erro)
                return 1

            if frame.shape[:2] != (altura_frame, largura_frame):
                logger.error(
                    "A resolucao do frame mudou durante a calibracao (%dx%d -> %dx%d). "
                    "Encerrando.",
                    largura_frame, altura_frame, frame.shape[1], frame.shape[0],
                )
                return 1
    finally:
        release_camera(camera)
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
