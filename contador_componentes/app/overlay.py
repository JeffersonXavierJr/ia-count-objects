"""Desenho das detecções sobre um frame (Sprint 6, tarefa 6.3.1 do TASKS.md).

Responsabilidade única deste módulo (RNF-05/RNF-06): receber um frame e a
lista de `Deteccao` já calculada e devolver uma IMAGEM ANOTADA (bounding
boxes + rótulo "classe confiança"). É apenas apresentação visual.

Por que um módulo próprio, e não `camera.py` ou `detector.py`:
- `camera.py` entrega frames (abrir, ler, liberar, recortar ROI) e não deve
  depender dos tipos do detector; colocar o desenho lá acoplaria a câmera à
  inferência.
- `detector.py` devolve dados (classe/confiança/bbox), não imagens; o
  próprio módulo declara que o desenho não pertence a ele.
- O desenho será reutilizado pelo pipeline ao vivo
  (`scripts/pipeline_ao_vivo.py`, tarefa 6.3) e depois pelo
  `video_stream.py` (Sprint 11), que serve o frame anotado ao Home
  Assistant. Um módulo pequeno e sem estado atende os dois sem duplicação.

NÃO pertencem a este módulo: filtragem pela classe selecionada, contagem,
estabilização, status/máquina de estados (`counter.py`, Sprint 7), MQTT e
streaming.

O frame recebido NUNCA é modificado: o desenho é feito sobre uma cópia.
Isso importa porque `camera.apply_roi` devolve uma *view* do frame da câmera.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    # Apenas para type hints: evita que importar o desenho carregue o
    # ultralytics/torch (usados pelo detector) sem necessidade.
    from contador_componentes.app.detector import Deteccao

# Cores por classe, em BGR (formato do OpenCV). Escolhidas para contrastar
# entre si e com bandeja clara/escura: parafuso = laranja, porca = ciano.
CORES_CLASSES: dict[int, tuple[int, int, int]] = {
    0: (0, 140, 255),  # parafuso
    1: (255, 200, 0),  # porca
}

# Paleta de reserva para ids fora da v1 (ex.: modelo com classes extras, que
# `detector.load_model` aceita com aviso). Indexada por `classe_id % len`.
_PALETA_RESERVA: tuple[tuple[int, int, int], ...] = (
    (255, 0, 255),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
)

_FONTE = cv2.FONT_HERSHEY_SIMPLEX

# Medidas de referência para um frame com lado maior de 1280 px. Frames
# maiores (ex.: 1080p) usam traço/fonte proporcionalmente maiores, para que
# o texto continue legível quando a imagem for reduzida para exibição.
_LADO_REFERENCIA = 1280
_ESCALA_FONTE_BASE = 0.6
_ESPESSURA_CAIXA_BASE = 2
_ESPESSURA_TEXTO_BASE = 1


def cor_da_classe(classe_id: int) -> tuple[int, int, int]:
    """Retorna a cor BGR usada para desenhar uma classe."""
    if classe_id in CORES_CLASSES:
        return CORES_CLASSES[classe_id]
    return _PALETA_RESERVA[classe_id % len(_PALETA_RESERVA)]


def _cor_texto_sobre(fundo: tuple[int, int, int]) -> tuple[int, int, int]:
    """Preto ou branco, o que tiver melhor contraste com a cor de fundo (BGR)."""
    azul, verde, vermelho = fundo
    luminancia = 0.114 * azul + 0.587 * verde + 0.299 * vermelho
    return (0, 0, 0) if luminancia > 140 else (255, 255, 255)


def draw_detections(frame: np.ndarray, deteccoes: Iterable[Deteccao]) -> np.ndarray:
    """Desenha bounding boxes e rótulos "classe confiança" sobre uma cópia do frame.

    Args:
        frame: imagem BGR (`altura x largura x 3`), tipicamente o recorte da
            ROI que foi passado para `detector.run_inference`. Não é
            modificado.
        deteccoes: detecções retornadas por `run_inference` PARA ESTE MESMO
            frame (as bboxes estão nas coordenadas dele).

    Returns:
        Nova imagem, com o mesmo `shape` e `dtype` do frame, contendo as
        anotações. Com lista vazia, retorna uma cópia inalterada.

    Raises:
        ValueError: se o frame for `None`/vazio ou não for BGR de 3 canais.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        raise ValueError("Frame vazio ou None recebido para desenho.")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(
            f"Frame com formato {frame.shape!r} nao suportado (esperado BGR "
            "altura x largura x 3)."
        )

    anotado = frame.copy()
    altura_frame, largura_frame = anotado.shape[:2]

    fator = max(1.0, max(largura_frame, altura_frame) / _LADO_REFERENCIA)
    escala_fonte = _ESCALA_FONTE_BASE * fator
    espessura_caixa = max(1, round(_ESPESSURA_CAIXA_BASE * fator))
    espessura_texto = max(1, round(_ESPESSURA_TEXTO_BASE * fator))
    margem = max(2, round(3 * fator))

    for deteccao in deteccoes:
        x1, y1, x2, y2 = (int(v) for v in deteccao.bbox)
        # Limita às bordas (o modelo pode devolver coordenadas na borda exata).
        x1 = min(max(x1, 0), largura_frame - 1)
        x2 = min(max(x2, 0), largura_frame - 1)
        y1 = min(max(y1, 0), altura_frame - 1)
        y2 = min(max(y2, 0), altura_frame - 1)

        cor = cor_da_classe(deteccao.classe_id)
        cv2.rectangle(anotado, (x1, y1), (x2, y2), cor, espessura_caixa, cv2.LINE_AA)

        rotulo = f"{deteccao.classe_nome} {deteccao.confianca:.2f}"
        (largura_txt, altura_txt), linha_base = cv2.getTextSize(
            rotulo, _FONTE, escala_fonte, espessura_texto
        )
        altura_rotulo = altura_txt + linha_base + 2 * margem
        largura_rotulo = largura_txt + 2 * margem

        # Rótulo acima da caixa; se não couber (caixa no topo), dentro dela.
        topo = y1 - altura_rotulo if y1 - altura_rotulo >= 0 else y1
        # Mantém o rótulo inteiro dentro do frame na horizontal.
        esquerda = min(x1, max(0, largura_frame - largura_rotulo))

        cv2.rectangle(
            anotado,
            (esquerda, topo),
            (esquerda + largura_rotulo, topo + altura_rotulo),
            cor,
            cv2.FILLED,
        )
        cv2.putText(
            anotado,
            rotulo,
            (esquerda + margem, topo + margem + altura_txt),
            _FONTE,
            escala_fonte,
            _cor_texto_sobre(cor),
            espessura_texto,
            cv2.LINE_AA,
        )

    return anotado
