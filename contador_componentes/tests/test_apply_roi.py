"""Testes de `camera.apply_roi` (Sprint 6, tarefa 6.1.2) com frames sinteticos.

Nao usam a webcam: os frames sao arrays numpy gerados no proprio teste.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests
"""

from __future__ import annotations

import numpy as np
import pytest

from contador_componentes.app import camera, config


def _frame(largura: int = 64, altura: int = 48) -> np.ndarray:
    """Frame BGR sintetico em que cada pixel codifica sua posicao (x, y)."""
    frame = np.zeros((altura, largura, 3), dtype=np.uint8)
    frame[:, :, 0] = np.arange(largura, dtype=np.uint8)[np.newaxis, :]
    frame[:, :, 1] = np.arange(altura, dtype=np.uint8)[:, np.newaxis]
    return frame


@pytest.fixture
def roi_config(monkeypatch):
    """Permite definir `config.ROI` apenas durante o teste."""

    def _definir(valor):
        monkeypatch.setattr(config, "ROI", valor)

    return _definir


def test_sem_roi_em_lugar_nenhum_retorna_frame_inalterado(roi_config):
    roi_config(None)
    frame = _frame()
    assert camera.apply_roi(frame) is frame


def test_roi_explicita_recorta_regiao_correta(roi_config):
    roi_config(None)
    frame = _frame()
    recorte = camera.apply_roi(frame, (10, 5, 20, 15))

    assert recorte.shape == (15, 20, 3)
    assert recorte[0, 0, 0] == 10 and recorte[0, 0, 1] == 5  # canto superior esquerdo
    assert recorte[-1, -1, 0] == 29 and recorte[-1, -1, 1] == 19  # canto inferior direito
    np.testing.assert_array_equal(recorte, frame[5:20, 10:30])


def test_roi_none_usa_config_roi(roi_config):
    roi_config((1, 2, 3, 4))
    frame = _frame()
    np.testing.assert_array_equal(camera.apply_roi(frame), frame[2:6, 1:4])


def test_roi_explicita_tem_prioridade_sobre_config(roi_config):
    roi_config((1, 2, 3, 4))
    frame = _frame()
    np.testing.assert_array_equal(camera.apply_roi(frame, (0, 0, 8, 8)), frame[0:8, 0:8])


def test_roi_do_frame_inteiro_retorna_mesmo_conteudo(roi_config):
    roi_config(None)
    frame = _frame(64, 48)
    np.testing.assert_array_equal(camera.apply_roi(frame, (0, 0, 64, 48)), frame)


def test_roi_que_ultrapassa_o_frame_e_limitada_as_bordas(roi_config):
    roi_config(None)
    frame = _frame(64, 48)
    recorte = camera.apply_roi(frame, (50, 40, 100, 100))
    np.testing.assert_array_equal(recorte, frame[40:48, 50:64])


def test_roi_com_origem_negativa_e_limitada_as_bordas(roi_config):
    roi_config(None)
    frame = _frame(64, 48)
    recorte = camera.apply_roi(frame, (-5, -3, 10, 10))
    np.testing.assert_array_equal(recorte, frame[0:7, 0:5])


def test_funciona_com_frame_em_escala_de_cinza(roi_config):
    roi_config(None)
    frame = _frame()[:, :, 0]
    recorte = camera.apply_roi(frame, (2, 3, 4, 5))
    assert recorte.shape == (5, 4)


@pytest.mark.parametrize("roi", [(0, 0, 0, 10), (0, 0, 10, 0), (0, 0, -5, 10), (0, 0, 10, -1)])
def test_tamanho_nao_positivo_gera_value_error(roi_config, roi):
    roi_config(None)
    with pytest.raises(ValueError, match="positivas"):
        camera.apply_roi(_frame(), roi)


@pytest.mark.parametrize("roi", [(100, 0, 10, 10), (0, 100, 10, 10), (-20, 0, 10, 10), (64, 48, 5, 5)])
def test_roi_totalmente_fora_do_frame_gera_value_error(roi_config, roi):
    roi_config(None)
    with pytest.raises(ValueError, match="vazia"):
        camera.apply_roi(_frame(64, 48), roi)


def test_config_roi_invalida_tambem_gera_value_error(roi_config):
    roi_config((0, 0, 0, 0))
    with pytest.raises(ValueError):
        camera.apply_roi(_frame())
