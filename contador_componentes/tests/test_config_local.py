"""Testes do `config_local.json` (Sprint 11, tarefa 11.1.3 — empacotamento).

Cobrem `config.carregar_config_local` / `config.salvar_roi_local` usando
arquivos temporarios (nunca o `config_local.json` real).
"""

from __future__ import annotations

import json

import pytest

from contador_componentes.app import config


def _escrever(caminho, conteudo) -> None:
    caminho.write_text(
        conteudo if isinstance(conteudo, str) else json.dumps(conteudo), encoding="utf-8"
    )


def test_arquivo_inexistente_devolve_vazio(tmp_path):
    assert config.carregar_config_local(tmp_path / "nao_existe.json") == {}


def test_valores_validos(tmp_path):
    arquivo = tmp_path / "config_local.json"
    _escrever(arquivo, {"camera_index": 2, "roi": [10, 20, 300, 200]})
    assert config.carregar_config_local(arquivo) == {
        "camera_index": 2,
        "roi": (10, 20, 300, 200),
    }


def test_roi_null_desativa(tmp_path):
    arquivo = tmp_path / "config_local.json"
    _escrever(arquivo, {"roi": None})
    assert config.carregar_config_local(arquivo) == {"roi": None}


@pytest.mark.parametrize(
    "dados",
    [
        {"camera_index": -1},
        {"camera_index": "0"},
        {"camera_index": True},
        {"roi": [1, 2, 3]},
        {"roi": [0, 0, 0, 10]},
        {"roi": [-1, 0, 10, 10]},
        {"roi": [0, 0, 10.5, 10]},
        {"roi": "0,0,10,10"},
        {"outra_opcao": 1},
    ],
)
def test_valores_invalidos_sao_ignorados(tmp_path, dados):
    arquivo = tmp_path / "config_local.json"
    _escrever(arquivo, dados)
    assert config.carregar_config_local(arquivo) == {}


@pytest.mark.parametrize("conteudo", ["{nao e json", "[1, 2]", ""])
def test_arquivo_ilegivel_usa_padroes(tmp_path, conteudo):
    arquivo = tmp_path / "config_local.json"
    _escrever(arquivo, conteudo)
    assert config.carregar_config_local(arquivo) == {}


def test_salvar_roi_preserva_outras_chaves(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROI", None)
    arquivo = tmp_path / "config_local.json"
    _escrever(arquivo, {"camera_index": 1})

    config.salvar_roi_local((5, 6, 70, 80), arquivo)

    assert json.loads(arquivo.read_text(encoding="utf-8")) == {
        "camera_index": 1,
        "roi": [5, 6, 70, 80],
    }
    assert config.ROI == (5, 6, 70, 80)
    assert config.carregar_config_local(arquivo)["roi"] == (5, 6, 70, 80)


def test_salvar_roi_invalida_nao_grava(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROI", None)
    arquivo = tmp_path / "config_local.json"
    with pytest.raises(ValueError):
        config.salvar_roi_local((0, 0, 0, 10), arquivo)
    assert not arquivo.exists()
