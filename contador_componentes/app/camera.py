"""Captura de vídeo via webcam (Sprint 1, tarefa 1.3) e recorte de ROI
(Sprint 6, tarefa 6.1 do TASKS.md).

Responsabilidade única deste módulo (RNF-05/RNF-06): entregar frames da
câmera — abrir, ler e liberar o dispositivo, e recortar o frame na região de
interesse (ROI, área útil da bandeja). Nenhuma lógica de inferência YOLO,
contagem, MQTT ou streaming pertence aqui — essas responsabilidades pertencem
a outros módulos de `contador_componentes/app/`.

O índice do dispositivo (`CAMERA_INDEX`) e as coordenadas da ROI (`ROI`) são
centralizados em `app/config.py`, nunca hardcoded neste módulo.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

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


def apply_roi(
    frame: np.ndarray, roi: tuple[int, int, int, int] | None = None
) -> np.ndarray:
    """Recorta o frame, retornando apenas a região da bandeja (ROI).

    O recorte é feito por fatiamento do array numpy, portanto o retorno é uma
    *view* do frame original (sem cópia). Quem precisar modificar o recorte
    sem afetar o frame original deve chamar `.copy()`.

    Args:
        frame: frame lido da câmera (array `altura x largura[ x canais]`).
        roi: retângulo `(x, y, largura, altura)` em pixels do frame. Quando
            omitido, usa `config.ROI`. Se `config.ROI` também for `None`, a
            ROI está desativada e o frame é retornado sem alteração.

    Returns:
        A região recortada do frame (ou o próprio frame, se não houver ROI).

    Raises:
        ValueError: se a ROI tiver largura/altura não positivas, ou se ficar
            vazia após ser limitada às bordas do frame (ex.: ROI inteiramente
            fora da imagem — sinal de ROI calibrada para outra resolução).
    """
    if roi is None:
        roi = config.ROI

    if roi is None:
        return frame

    x, y, largura, altura = (int(valor) for valor in roi)

    if largura <= 0 or altura <= 0:
        raise ValueError(
            f"ROI invalida {tuple(roi)!r}: largura e altura devem ser positivas "
            "(formato esperado: (x, y, largura, altura))."
        )

    altura_frame, largura_frame = frame.shape[:2]

    # Limita o retângulo às bordas do frame.
    x0 = min(max(x, 0), largura_frame)
    y0 = min(max(y, 0), altura_frame)
    x1 = min(max(x + largura, 0), largura_frame)
    y1 = min(max(y + altura, 0), altura_frame)

    if x1 <= x0 or y1 <= y0:
        raise ValueError(
            f"ROI {tuple(roi)!r} fica vazia dentro do frame de "
            f"{largura_frame}x{altura_frame} pixels. Verifique se a ROI foi "
            "calibrada para a mesma resolucao de captura atual."
        )

    if (x0, y0, x1, y1) != (x, y, x + largura, y + altura):
        logger.debug(
            "ROI %r ultrapassa o frame de %dx%d; recorte limitado a "
            "(%d, %d, %d, %d).",
            tuple(roi), largura_frame, altura_frame, x0, y0, x1 - x0, y1 - y0,
        )

    return frame[y0:y1, x0:x1]
