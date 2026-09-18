"""Script isolado de validação rápida da webcam (Sprint 1, tarefa 1.1 do TASKS.md).

Este script NAO faz parte do pacote da aplicacao (`contador_componentes/app/`).
Ele reproduz o "primeiro passo pratico de codigo" descrito na secao 32 do PRD:
abrir a webcam padrao, exibir o stream ao vivo em uma janela e permitir encerrar
com uma tecla. Nao ha ROI, YOLO, contagem, MQTT ou qualquer outra logica aqui —
isso vem em sprints futuras.

A logica definitiva de abrir/ler/liberar a camera foi migrada para o modulo
`contador_componentes/app/camera.py` (tarefa 1.3). Este script serve apenas
como ferramenta manual de smoke test, independente do pacote da aplicacao.

Uso:
    python contador_componentes/scripts/webcam_preview.py

Pressione "q" com a janela da câmera em foco para encerrar.
"""

from __future__ import annotations

import logging
import sys

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Indice da webcam padrao do sistema operacional. O modelo exato da webcam e a
# resolucao final ainda nao foram decididos pelo time (PRD secao 29, pontos
# 29.1 e 29.2) — este script usa apenas o indice padrao (0) como placeholder
# de validacao rapida, sem fixar resolucao alguma.
CAMERA_INDEX = 0

WINDOW_NAME = "Webcam Preview"
QUIT_KEY = "q"


def main() -> int:
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        logger.error(
            "Nao foi possivel abrir a webcam (indice %s). Verifique se ela esta "
            "conectada, se nao esta sendo usada por outro programa, e se o "
            "indice do dispositivo esta correto.",
            CAMERA_INDEX,
        )
        return 1

    logger.info("Webcam aberta com sucesso (indice %s). Pressione '%s' para sair.", CAMERA_INDEX, QUIT_KEY)

    try:
        while True:
            ok, frame = camera.read()

            if not ok:
                logger.error("Falha ao ler frame da webcam. Encerrando o preview.")
                break

            cv2.imshow(WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == ord(QUIT_KEY):
                logger.info("Tecla '%s' pressionada. Encerrando o preview.", QUIT_KEY)
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    sys.exit(main())
