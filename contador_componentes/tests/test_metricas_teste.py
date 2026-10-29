"""Testes de `training/metricas_teste.py` (Sprint 5, tarefa 5.2): IoU, matching e contagem.

Usam caixas montadas a mao — nao precisam de modelo, dataset nem webcam.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests
"""

from __future__ import annotations

from datetime import datetime

import pytest

from contador_componentes.training import metricas_teste as mt


def _p(classe, bbox, conf=0.9):
    return {"classe_id": classe, "conf": conf, "bbox_xyxy": list(bbox)}


def _g(classe, bbox):
    return {"classe_id": classe, "bbox_xyxy": list(bbox)}


def test_iou_casos_basicos():
    assert mt.iou([0, 0, 10, 10], [0, 0, 10, 10]) == pytest.approx(1.0)
    assert mt.iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    # metade sobreposta: inter 50, uniao 150
    assert mt.iou([0, 0, 10, 10], [5, 0, 15, 10]) == pytest.approx(50 / 150)


def test_casar_tp_fn_e_tipos_de_fp():
    gt = [_g(0, (0, 0, 10, 10)), _g(1, (50, 50, 60, 60)), _g(0, (100, 100, 110, 110))]
    preds = [
        _p(0, (0, 0, 10, 10), 0.95),       # TP
        _p(0, (0, 0, 10, 10.5), 0.80),     # mesmo objeto de novo -> duplicata
        _p(0, (50, 50, 60, 60), 0.70),     # sobre a porca -> classe errada
        _p(1, (200, 200, 210, 210), 0.60), # nada ali -> inexistente
    ]
    r = mt.casar(preds, gt, 0.5)
    assert [p["conf"] for p in r["tp"]] == [0.95]
    assert sorted(t for _, t in r["fp"]) == ["classe_errada", "duplicata", "inexistente"]
    # a porca e o segundo parafuso nao foram encontrados
    assert sorted(g["classe_id"] for g in r["fn"]) == [0, 1]


def test_casar_guloso_prioriza_maior_confianca():
    gt = [_g(0, (0, 0, 10, 10))]
    preds = [_p(0, (0, 0, 10, 12), 0.6), _p(0, (0, 0, 10, 10), 0.9)]
    r = mt.casar(preds, gt, 0.5)
    assert r["tp"][0]["conf"] == 0.9
    assert r["fp"][0][0]["conf"] == 0.6


def test_casar_respeita_iou_minimo():
    gt = [_g(0, (0, 0, 10, 10))]
    r = mt.casar([_p(0, (6, 0, 16, 10))], gt, 0.5)  # IoU = 4*10/160 = 0.25
    assert not r["tp"] and len(r["fp"]) == 1 and len(r["fn"]) == 1


def test_metricas_contagem_e_limiar():
    imagens = [
        {"imagem": "a.jpg", "gt": [_g(0, (0, 0, 10, 10)), _g(0, (20, 0, 30, 10))],
         "predicoes": [_p(0, (0, 0, 10, 10), 0.9), _p(0, (20, 0, 30, 10), 0.3)]},
        {"imagem": "b.jpg", "gt": [_g(1, (0, 0, 10, 10))],
         "predicoes": [_p(1, (0, 0, 10, 10), 0.8)]},
    ]
    m = mt.metricas(imagens, [0, 1], conf=0.5, iou_min=0.5)
    par, por = m["classes"]["0"], m["classes"]["1"]
    assert (par["tp"], par["fp"], par["fn"]) == (1, 0, 1)
    assert par["mae_contagem"] == 0.5          # erro 1 em a.jpg, 0 em b.jpg
    assert par["pct_contagem_exata"] == 50.0
    assert par["maior_erro"] == {"erro": -1, "imagem": "a.jpg"}
    assert por["precisao"] == 1.0 and por["recall"] == 1.0
    # limiar mais baixo aceita a caixa de 0.3 -> contagem exata
    m2 = mt.metricas(imagens, [0, 1], conf=0.25, iou_min=0.5)
    assert m2["classes"]["0"]["pct_contagem_exata"] == 100.0


def test_ap_perfeito_e_vazio():
    # como no ultralytics, o AP "perfeito" da 0.995 (sentinela de recall 1 -> precisao 0)
    assert mt.ap_101([(0.9, True), (0.8, True)], 2) == pytest.approx(0.995, abs=1e-3)
    assert mt.ap_101([], 3) == pytest.approx(0.0, abs=1e-3)


def test_horario_do_nome():
    assert mt.horario_do_nome("frame_20260923_204759_008_jpg.rf.x.jpg") == datetime(2026, 9, 23, 20, 47, 59)
    assert mt.horario_do_nome("WhatsApp-Image-2026-10-22-at-19-40-31_jpeg.rf.y.jpg") == \
        datetime(2026, 10, 22, 19, 40, 31)
    assert mt.horario_do_nome("outra.jpg") is None
