"""Ferramenta de captura de frames para o dataset (Sprint 2, tarefa 2.1 do TASKS.md).

Reaproveita `app/camera.py` (Sprint 1) para exibir o stream ao vivo da webcam e,
a cada tecla `s` pressionada, salvar o frame atual em
`contador_componentes/dataset/images/raw/`. Este script NAO decide o que deve
ser fotografado (quantidade/posicao de parafusos e porcas) — isso depende do
protocolo de captura da tarefa 2.2 do TASKS.md, aplicado manualmente por quem
opera a ferramenta. Tambem nao ha ROI, YOLO, contagem ou MQTT aqui.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m contador_componentes.scripts.dataset_capture

Teclas:
    s - salva o frame atual em dataset/images/raw/
    q - encerra o script
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import cv2

from contador_componentes.app.camera import CameraError, open_camera, read_frame, release_camera

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WINDOW_NAME = "Captura de Dataset"
SAVE_KEY = "s"
QUIT_KEY = "q"

# dataset/images/raw fica na raiz de contador_componentes, dois niveis acima
# deste arquivo (contador_componentes/scripts/dataset_capture.py).
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "dataset" / "images" / "raw"


def _proximo_nome_arquivo(diretorio: Path) -> Path:
    """Gera um nome de arquivo unico baseado em timestamp, sem sobrescrever nada.

    Usa timestamp com precisao de segundos mais um contador incremental de
    desempate, para o caso (raro, mas possivel) de duas capturas caírem no
    mesmo segundo.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    contador = 0

    while True:
        sufixo = f"_{contador:03d}" if contador else ""
        caminho = diretorio / f"frame_{timestamp}{sufixo}.jpg"

        if not caminho.exists():
            return caminho

        contador += 1


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        camera = open_camera()
    except CameraError as erro:
        logger.error("%s", erro)
        return 1

    logger.info(
        "Captura de dataset iniciada. Pressione '%s' para salvar um frame e '%s' para sair. "
        "Frames salvos em: %s",
        SAVE_KEY,
        QUIT_KEY,
        OUTPUT_DIR,
    )

    total_salvos = 0

    try:
        while True:
            try:
                frame = read_frame(camera)
            except CameraError as erro:
                logger.error("%s Encerrando a captura.", erro)
                break

            cv2.imshow(WINDOW_NAME, frame)
            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord(SAVE_KEY):
                caminho = _proximo_nome_arquivo(OUTPUT_DIR)
                cv2.imwrite(str(caminho), frame)
                total_salvos += 1
                logger.info("Frame salvo (%d ate agora): %s", total_salvos, caminho)
            elif tecla == ord(QUIT_KEY):
                logger.info("Tecla '%s' pressionada. Encerrando a captura.", QUIT_KEY)
                break
    finally:
        release_camera(camera)
        cv2.destroyAllWindows()

    logger.info("Sessao de captura encerrada. Total de frames salvos: %d.", total_salvos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
