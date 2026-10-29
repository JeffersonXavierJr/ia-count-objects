"""Testes de `overlay.draw_detections` (Sprint 6, tarefa 6.3.1) com frames sinteticos.

Nao usam webcam nem modelo: as deteccoes sao `Deteccao` montadas a mao.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests
"""

from __future__ import annotations

import numpy as np
import pytest

from contador_componentes.app import overlay
from contador_componentes.app.detector import Deteccao


def _frame(largura: int = 200, altura: int = 150) -> np.ndarray:
    """Frame BGR sintetico cinza uniforme."""
    return np.full((altura, largura, 3), 50, dtype=np.uint8)


def _det(classe_id: int = 0, bbox=(40, 60, 120, 130), confianca: float = 0.87) -> Deteccao:
    nome = {0: "parafuso", 1: "porca"}.get(classe_id, str(classe_id))
    return Deteccao(classe_id=classe_id, classe_nome=nome, confianca=confianca, bbox=bbox)


def test_retorna_mesmo_shape_e_dtype():
    frame = _frame()
    anotado = overlay.draw_detections(frame, [_det()])
    assert anotado.shape == frame.shape
    assert anotado.dtype == frame.dtype


def test_nao_modifica_o_frame_original():
    frame = _frame()
    original = frame.copy()
    anotado = overlay.draw_detections(frame, [_det(0), _det(1, bbox=(10, 5, 60, 40))])
    np.testing.assert_array_equal(frame, original)
    assert anotado is not frame
    assert not np.shares_memory(anotado, frame)


def test_nao_modifica_frame_quando_recebe_view_de_roi():
    frame = _frame()
    original = frame.copy()
    recorte = frame[20:120, 30:180]  # view, como camera.apply_roi devolve
    overlay.draw_detections(recorte, [_det(bbox=(5, 30, 80, 90))])
    np.testing.assert_array_equal(frame, original)


def test_desenha_na_borda_da_caixa():
    frame = _frame()
    x1, y1, x2, y2 = 40, 60, 120, 130
    anotado = overlay.draw_detections(frame, [_det(0, bbox=(x1, y1, x2, y2))])

    cor = np.array(overlay.cor_da_classe(0), dtype=np.uint8)
    # Borda inferior da caixa (o rotulo fica acima, entao aqui so ha o retangulo).
    np.testing.assert_array_equal(anotado[y2, (x1 + x2) // 2], cor)
    # Pixels mudaram na regiao da caixa + rotulo, e o miolo da caixa nao foi preenchido.
    assert np.any(anotado[: y2 + 1, x1 : x2 + 1] != frame[: y2 + 1, x1 : x2 + 1])
    np.testing.assert_array_equal(anotado[(y1 + y2) // 2, (x1 + x2) // 2], frame[0, 0])
    # Longe da caixa nada muda.
    np.testing.assert_array_equal(anotado[-5:, -5:], frame[-5:, -5:])


def test_lista_vazia_retorna_copia_inalterada():
    frame = _frame()
    anotado = overlay.draw_detections(frame, [])
    np.testing.assert_array_equal(anotado, frame)
    assert anotado is not frame
    assert not np.shares_memory(anotado, frame)


def test_cores_distintas_por_classe():
    assert overlay.cor_da_classe(0) != overlay.cor_da_classe(1)
    frame = _frame()
    a = overlay.draw_detections(frame, [_det(0)])
    b = overlay.draw_detections(frame, [_det(1)])
    assert not np.array_equal(a, b)


def test_classe_fora_da_v1_usa_cor_de_reserva():
    anotado = overlay.draw_detections(_frame(), [_det(7)])
    assert anotado.shape == _frame().shape


def test_caixa_no_topo_e_na_borda_nao_quebra():
    frame = _frame()
    altura, largura = frame.shape[:2]
    anotado = overlay.draw_detections(frame, [_det(1, bbox=(largura - 10, 0, largura, altura))])
    assert anotado.shape == frame.shape
    assert np.any(anotado != frame)


@pytest.mark.parametrize("invalido", [None, np.zeros((0, 0, 3), dtype=np.uint8), np.zeros((10, 10), dtype=np.uint8)])
def test_frame_invalido_gera_value_error(invalido):
    with pytest.raises(ValueError):
        overlay.draw_detections(invalido, [_det()])
