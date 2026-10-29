"""Pipeline ao vivo webcam -> ROI -> YOLO -> bounding boxes (Sprint 6, tarefa 6.3).

Loop: `camera.read_frame` -> `camera.apply_roi` -> `detector.run_inference`
-> `overlay.draw_detections` -> janela local (`cv2.imshow`), para validação
manual do detector com a câmera real (tarefa 6.3.2), ainda SEM MQTT/Home
Assistant.

O que é exibido é o RECORTE DA ROI anotado (não o frame inteiro): é
exatamente a imagem que o modelo analisa e a mesma que o `video_stream.py`
servirá ao Home Assistant na Sprint 11. Com `config.ROI = None`, o recorte é
o frame inteiro.

Fora do escopo deste script (sprints posteriores): filtragem pela classe
selecionada, contagem, estabilização, máquina de estados (Sprint 7+), MQTT e
streaming. O indicador de FPS na tela é apenas uma referência visual; a
medição formal de FPS/CPU/RAM é a tarefa 6.4.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m contador_componentes.scripts.pipeline_ao_vivo

Controles:
    q ou Esc (ou fechar a janela) - encerrar
"""

from __future__ import annotations

import logging
import sys
import time

import cv2
import numpy as np

from contador_componentes.app.camera import (
    CameraError,
    apply_roi,
    open_camera,
    read_frame,
    release_camera,
)
from contador_componentes.app.detector import ModelError, load_model, run_inference
from contador_componentes.app.overlay import draw_detections

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WINDOW_NAME = "Pipeline ao vivo (ROI + YOLO)"

# Tamanho maximo da janela de exibicao (mesmo criterio de calibrar_roi.py).
# A imagem anotada e reduzida apenas para exibicao, preservando a proporcao.
MAX_LARGURA_JANELA = 1280
MAX_ALTURA_JANELA = 720

# Suavizacao do FPS exibido (media movel exponencial), so para leitura na tela.
_PESO_FPS = 0.1

_COR_FPS = (0, 255, 255)


def _escala_exibicao(largura: int, altura: int) -> float:
    """Fator de reducao para que a imagem caiba na janela (nunca amplia)."""
    return min(1.0, MAX_LARGURA_JANELA / largura, MAX_ALTURA_JANELA / altura)


def _redimensionar_para_exibicao(imagem: np.ndarray) -> np.ndarray:
    altura, largura = imagem.shape[:2]
    escala = _escala_exibicao(largura, altura)
    if escala >= 1.0:
        return imagem
    return cv2.resize(
        imagem,
        (max(1, round(largura * escala)), max(1, round(altura * escala))),
        interpolation=cv2.INTER_AREA,
    )


def _desenhar_fps(imagem: np.ndarray, fps: float, n_deteccoes: int) -> None:
    """Escreve FPS e numero bruto de deteccoes no canto (modifica `imagem`).

    Chamado sobre a imagem JA reduzida para exibicao, que e uma copia
    propria deste script — o frame da camera nao e afetado.
    """
    texto = f"FPS: {fps:.1f} | deteccoes: {n_deteccoes} | q/Esc: sair"
    origem = (10, 25)
    cv2.putText(imagem, texto, origem, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(imagem, texto, origem, cv2.FONT_HERSHEY_SIMPLEX, 0.6, _COR_FPS, 1, cv2.LINE_AA)


def main() -> int:
    # Modelo carregado UMA vez, antes de abrir a camera (falha rapida e sem
    # deixar o dispositivo ocupado se o modelo estiver ausente/incompativel).
    try:
        modelo = load_model()
    except ModelError as erro:
        logger.error("%s", erro)
        return 1

    try:
        camera = open_camera()
    except CameraError as erro:
        logger.error("%s", erro)
        return 1

    try:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        fps = 0.0
        instante_anterior = time.perf_counter()

        while True:
            try:
                frame = read_frame(camera)
            except CameraError as erro:
                logger.error("%s Encerrando o pipeline.", erro)
                return 1

            try:
                recorte = apply_roi(frame)
            except ValueError as erro:
                logger.error(
                    "%s Ajuste config.ROI (python -m "
                    "contador_componentes.scripts.calibrar_roi). Encerrando.",
                    erro,
                )
                return 1

            deteccoes = run_inference(modelo, recorte)
            anotado = draw_detections(recorte, deteccoes)

            agora = time.perf_counter()
            intervalo = agora - instante_anterior
            instante_anterior = agora
            if intervalo > 0:
                instantaneo = 1.0 / intervalo
                fps = instantaneo if fps == 0.0 else (
                    _PESO_FPS * instantaneo + (1 - _PESO_FPS) * fps
                )

            # `anotado` ja e copia propria (draw_detections), entao escrever o
            # FPS nela (quando nao ha reducao) nao afeta o frame da camera.
            exibicao = _redimensionar_para_exibicao(anotado)
            _desenhar_fps(exibicao, fps, len(deteccoes))
            cv2.imshow(WINDOW_NAME, exibicao)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):
                logger.info("Encerrando o pipeline ao vivo.")
                break
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                logger.info("Janela fechada. Encerrando o pipeline ao vivo.")
                break
    finally:
        release_camera(camera)
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
