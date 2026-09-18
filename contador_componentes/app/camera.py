"""Captura de vídeo via webcam (Sprint 1, tarefa 1.3 do TASKS.md).

Responsabilidade única deste módulo (RNF-05/RNF-06): abrir, ler e liberar o
dispositivo de câmera. Nenhuma lógica de ROI, inferência YOLO, contagem,
MQTT ou streaming pertence aqui — essas responsabilidades pertencem a outros
módulos de `contador_componentes/app/` em sprints futuras.

O índice do dispositivo de câmera é centralizado em `app/config.py`
(`CAMERA_INDEX`), nunca hardcoded neste módulo.
"""

from __future__ import annotations

import logging

import cv2

from contador_componentes.app import config

logger = logging.getLogger(__name__)


class CameraError(RuntimeError):
    """Erro ao abrir ou ler a câmera.

    Serve de base para o futuro estado `ERRO DE CÂMERA` da máquina de
    estados do projeto (RB-03), que será implementado em sprint posterior
    (Sprint 7). Este módulo apenas detecta e sinaliza a falha de forma
    clara — não implementa a máquina de estados em si.
    """


def open_camera(indice_ou_config: int | None = None) -> cv2.VideoCapture:
    """Abre o dispositivo de câmera e retorna o objeto de captura.

    Args:
        indice_ou_config: índice do dispositivo (ex.: 0) a ser repassado a
            `cv2.VideoCapture`. Quando omitido, usa `config.CAMERA_INDEX`.

    Returns:
        Instância de `cv2.VideoCapture` já aberta.

    Raises:
        CameraError: se o dispositivo não puder ser aberto.
    """
    indice = config.CAMERA_INDEX if indice_ou_config is None else indice_ou_config

    camera = cv2.VideoCapture(indice)

    if not camera.isOpened():
        camera.release()
        raise CameraError(
            f"Nao foi possivel abrir a webcam (indice/config={indice!r}). "
            "Verifique se ela esta conectada, se nao esta sendo usada por "
            "outro programa, e se o indice do dispositivo esta correto."
        )

    logger.info("Camera aberta com sucesso (indice/config=%r).", indice)
    return camera


def read_frame(camera: cv2.VideoCapture):
    """Lê e retorna o frame atual da câmera.

    Args:
        camera: objeto de captura retornado por `open_camera`.

    Returns:
        O frame lido (array do OpenCV/numpy).

    Raises:
        CameraError: se a leitura do frame falhar.
    """
    ok, frame = camera.read()

    if not ok:
        raise CameraError("Falha ao ler frame da webcam.")

    return frame


def release_camera(camera: cv2.VideoCapture) -> None:
    """Libera o dispositivo de câmera corretamente.

    Args:
        camera: objeto de captura retornado por `open_camera`. Aceita
            valores `None` de forma silenciosa, para facilitar o uso em
            blocos `finally` mesmo quando `open_camera` nunca chegou a
            suceder.
    """
    if camera is None:
        return

    camera.release()
    logger.info("Camera liberada.")
