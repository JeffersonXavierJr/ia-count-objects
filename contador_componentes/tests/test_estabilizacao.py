"""Testes da estabilizacao da contagem (Sprint 8, tarefas 8.1 e 8.3).

Logica pura: nao usam webcam nem modelo.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests/test_estabilizacao.py
"""

from __future__ import annotations

import numpy as np
import pytest

from contador_componentes.app import config as app_config
from contador_componentes.app.counter import (
    ConfiguracaoContagem,
    EstabilizadorContagem,
    Estado,
)

CFG = ConfiguracaoContagem(classe="parafuso", quantidade=12)


def _alimentar(estab: EstabilizadorContagem, leituras, cfg=CFG) -> list[Estado]:
    return [estab.atualizar(cfg, n) for n in leituras]


# ------------------------------------------------------------------ 8.1.3
def test_n_padrao_vem_do_config():
    assert app_config.FRAMES_ESTABILIZACAO == 5
    assert EstabilizadorContagem().n_frames == app_config.FRAMES_ESTABILIZACAO


def test_n_padrao_lido_na_criacao(monkeypatch):
    monkeypatch.setattr(app_config, "FRAMES_ESTABILIZACAO", 3)
    assert EstabilizadorContagem().n_frames == 3


@pytest.mark.parametrize("n", [0, -1, 2.0, "5", True, False])
def test_n_invalido(n):
    with pytest.raises(ValueError):
        EstabilizadorContagem(n)


# ------------------------------------------------------------------ 8.1.1 / 8.1.2
def test_historico_limitado_a_n():
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [1, 2, 3, 4, 5])
    assert estab.historico == (3, 4, 5)
    assert estab.ultima_contagem == 5


def test_n_frames_exatos_atinge():
    estab = EstabilizadorContagem(5)
    estados = _alimentar(estab, [12] * 5)
    assert estados[:4] == [Estado.CONTANDO] * 4
    assert estados[4] is Estado.QUANTIDADE_ATINGIDA
    assert estab.frames_consecutivos == 5
    # Continua atingida enquanto a leitura se mantiver.
    assert estab.atualizar(CFG, 12) is Estado.QUANTIDADE_ATINGIDA


def test_n_menos_1_ainda_contando():
    estab = EstabilizadorContagem(5)
    estados = _alimentar(estab, [12] * 4)
    assert estados[-1] is Estado.CONTANDO
    assert estab.frames_consecutivos == 4


def test_n_igual_1_sem_espera():
    estab = EstabilizadorContagem(1)
    assert estab.atualizar(CFG, 12) is Estado.QUANTIDADE_ATINGIDA
    assert estab.atualizar(CFG, 13) is Estado.QUANTIDADE_EXCEDIDA
    assert estab.atualizar(CFG, 11) is Estado.CONTANDO


def test_oscilacao_nunca_atinge():
    estab = EstabilizadorContagem(5)
    estados = _alimentar(estab, [12, 11] * 10)
    assert set(estados) == {Estado.CONTANDO}


def test_oscilacao_atingido_excedido_nunca_estabiliza():
    estab = EstabilizadorContagem(3)
    estados = _alimentar(estab, [12, 13] * 6)
    assert set(estados) == {Estado.CONTANDO}


# ------------------------------------------------------------------ 8.3.1
def test_queda_abaixo_do_alvo_reinicia_sequencia():
    estab = EstabilizadorContagem(5)
    _alimentar(estab, [12] * 4)
    assert estab.atualizar(CFG, 11) is Estado.CONTANDO
    assert estab.frames_consecutivos == 1  # sequencia "abaixo" recomecou
    # Precisa de N novos frames no alvo.
    estados = _alimentar(estab, [12] * 5)
    assert estados[:4] == [Estado.CONTANDO] * 4
    assert estados[4] is Estado.QUANTIDADE_ATINGIDA


def test_queda_apos_atingida_volta_a_contando():
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [12] * 3)
    assert estab.estado is Estado.QUANTIDADE_ATINGIDA
    assert estab.atualizar(CFG, 11) is Estado.CONTANDO
    assert estab.atualizar(CFG, 12) is Estado.CONTANDO
    assert estab.atualizar(CFG, 12) is Estado.CONTANDO
    assert estab.atualizar(CFG, 12) is Estado.QUANTIDADE_ATINGIDA


# ------------------------------------------------------------------ EXCEDIDA
def test_excedida_estabilizada():
    estab = EstabilizadorContagem(4)
    estados = _alimentar(estab, [13, 14, 13, 15])
    assert estados[:3] == [Estado.CONTANDO] * 3
    assert estados[3] is Estado.QUANTIDADE_EXCEDIDA


def test_excedida_interrompida_por_atingida():
    estab = EstabilizadorContagem(3)
    estados = _alimentar(estab, [13, 13, 12, 13, 13])
    assert set(estados) == {Estado.CONTANDO}
    assert estab.atualizar(CFG, 13) is Estado.QUANTIDADE_EXCEDIDA


# ------------------------------------------------------------------ 8.3.2
def test_troca_de_quantidade_reinicia():
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [12] * 3)
    assert estab.estado is Estado.QUANTIDADE_ATINGIDA
    nova = ConfiguracaoContagem(classe="parafuso", quantidade=10)
    estados = _alimentar(estab, [10] * 3, cfg=nova)
    assert estados == [Estado.CONTANDO, Estado.CONTANDO, Estado.QUANTIDADE_ATINGIDA]


def test_troca_de_classe_reinicia():
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [12] * 2)
    nova = ConfiguracaoContagem(classe="porca", quantidade=12)
    assert estab.atualizar(nova, 12) is Estado.CONTANDO
    assert estab.historico == (12,)
    assert estab.atualizar(nova, 12) is Estado.CONTANDO
    assert estab.atualizar(nova, 12) is Estado.QUANTIDADE_ATINGIDA


def test_mesma_classe_por_nome_ou_id_nao_reinicia():
    estab = EstabilizadorContagem(3)
    estab.atualizar(ConfiguracaoContagem(classe="parafuso", quantidade=12), 12)
    estab.atualizar(ConfiguracaoContagem(classe="Parafuso", quantidade=12), 12)
    assert (
        estab.atualizar(ConfiguracaoContagem(classe=0, quantidade=12), 12)
        is Estado.QUANTIDADE_ATINGIDA
    )


def test_reiniciar():
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [12] * 3)
    assert estab.estado is Estado.QUANTIDADE_ATINGIDA
    estab.reiniciar()
    assert estab.historico == ()
    assert estab.frames_consecutivos == 0
    assert estab.ultima_contagem is None
    assert estab.n_frames == 3
    estados = _alimentar(estab, [12] * 3)
    assert estados == [Estado.CONTANDO, Estado.CONTANDO, Estado.QUANTIDADE_ATINGIDA]


# ------------------------------------------------------------------ erros / config
def test_modelo_nao_carregado_imediato_e_prioritario():
    estab = EstabilizadorContagem(5)
    assert (
        estab.atualizar(CFG, 0, erro_camera=True, modelo_carregado=False)
        is Estado.MODELO_NAO_CARREGADO
    )


def test_erro_camera_imediato_e_quebra_sequencia():
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [12] * 2)
    assert estab.atualizar(CFG, 0, erro_camera=True) is Estado.ERRO_CAMERA
    assert estab.historico == ()
    assert estab.ultima_contagem is None
    estados = _alimentar(estab, [12] * 3)
    assert estados == [Estado.CONTANDO, Estado.CONTANDO, Estado.QUANTIDADE_ATINGIDA]


def test_erro_ignora_detectado_invalido():
    estab = EstabilizadorContagem(3)
    assert estab.atualizar(CFG, None, erro_camera=True) is Estado.ERRO_CAMERA  # type: ignore[arg-type]


def test_aguardando_configuracao_imediato():
    estab = EstabilizadorContagem(5)
    sem_qtd = ConfiguracaoContagem(classe="parafuso")
    assert estab.atualizar(sem_qtd, 3) is Estado.AGUARDANDO_CONFIGURACAO
    assert estab.atualizar(ConfiguracaoContagem(), 3) is Estado.AGUARDANDO_CONFIGURACAO
    assert estab.historico == ()
    assert estab.ultima_contagem == 3


# ------------------------------------------------------------------ tipos
@pytest.mark.parametrize("tipo", [np.int64, np.int32, np.uint8, np.intp])
def test_aceita_inteiro_numpy(tipo):
    estab = EstabilizadorContagem(2)
    estab.atualizar(CFG, tipo(12))
    assert estab.atualizar(CFG, tipo(12)) is Estado.QUANTIDADE_ATINGIDA
    assert type(estab.ultima_contagem) is int


@pytest.mark.parametrize("valor", [True, False, np.True_, 12.0, np.float64(12), "12", None, -1])
def test_rejeita_detectado_invalido_sem_alterar_estado(valor):
    estab = EstabilizadorContagem(3)
    _alimentar(estab, [12] * 2)
    with pytest.raises(ValueError):
        estab.atualizar(CFG, valor)
    assert estab.historico == (12, 12)
    # A sequencia nao foi quebrada pela leitura invalida.
    assert estab.atualizar(CFG, 12) is Estado.QUANTIDADE_ATINGIDA
