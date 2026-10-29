"""Testes de `counter.py` (Sprint 7, tarefas 7.1, 7.2 e 7.3).

Logica pura: nao usam webcam nem modelo; as deteccoes sao `Deteccao` montadas
a mao.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests
"""

from __future__ import annotations

import pytest

from contador_componentes.app import counter
from contador_componentes.app.camera import CameraError
from contador_componentes.app.counter import ConfiguracaoContagem, Estado
from contador_componentes.app.detector import CLASSES_ESPERADAS, Deteccao, ModelError


def _det(classe_id: int, confianca: float = 0.9) -> Deteccao:
    return Deteccao(
        classe_id=classe_id,
        classe_nome=CLASSES_ESPERADAS[classe_id],
        confianca=confianca,
        bbox=(0, 0, 10, 10),
    )


def _frame_misto(parafusos: int, porcas: int) -> list[Deteccao]:
    return [_det(0) for _ in range(parafusos)] + [_det(1) for _ in range(porcas)]


# --------------------------------------------------------------------------- 7.1
def test_classes_iguais_as_do_detector():
    assert counter.CLASSES == CLASSES_ESPERADAS


@pytest.mark.parametrize("classe", ["parafuso", "Parafuso", " PARAFUSO ", 0])
def test_filter_aceita_nome_ou_id(classe):
    filtradas = counter.filter_by_class(_frame_misto(3, 2), classe)
    assert len(filtradas) == 3
    assert all(d.classe_id == 0 for d in filtradas)


def test_filter_porca():
    filtradas = counter.filter_by_class(_frame_misto(3, 2), "porca")
    assert [d.classe_id for d in filtradas] == [1, 1]


def test_filter_preserva_ordem_e_nao_altera_entrada():
    deteccoes = [_det(1, 0.5), _det(0, 0.9), _det(1, 0.7), _det(0, 0.6)]
    copia = list(deteccoes)
    filtradas = counter.filter_by_class(deteccoes, "parafuso")
    assert [d.confianca for d in filtradas] == [0.9, 0.6]
    assert deteccoes == copia


def test_filter_lista_vazia():
    assert counter.filter_by_class([], "porca") == []


@pytest.mark.parametrize("classe", ["arruela", "", None, 2, -1, True, 0.0])
def test_filter_classe_invalida(classe):
    with pytest.raises(ValueError):
        counter.filter_by_class(_frame_misto(1, 1), classe)


def test_rb01_exemplo_prd_secao_17():
    """12 parafusos + 4 porcas, selecionado parafuso -> exibir 12."""
    deteccoes = _frame_misto(12, 4)
    assert counter.count_objects(counter.filter_by_class(deteccoes, "parafuso")) == 12
    assert counter.count_objects(counter.filter_by_class(deteccoes, "porca")) == 4


def test_rb01_outra_classe_nao_afeta_estado():
    """Porcas em excesso nao levam a QUANTIDADE EXCEDIDA quando o alvo e parafuso."""
    cfg = ConfiguracaoContagem("parafuso", 12)
    detectado = counter.count_objects(counter.filter_by_class(_frame_misto(12, 30), cfg.classe))
    assert counter.determinar_estado(cfg, detectado) is Estado.QUANTIDADE_ATINGIDA


# --------------------------------------------------------------------------- 7.2
def test_count_vazio():
    assert counter.count_objects([]) == 0


def test_count_aceita_iteravel():
    assert counter.count_objects(iter(_frame_misto(5, 0))) == 5


def test_count_retorna_int():
    assert type(counter.count_objects(_frame_misto(2, 0))) is int


# --------------------------------------------------------------------------- 7.3
def test_valores_exibidos_dos_estados():
    assert {e.value for e in Estado} == {
        "AGUARDANDO CONFIGURAÇÃO",
        "CONTANDO",
        "QUANTIDADE ATINGIDA",
        "QUANTIDADE EXCEDIDA",
        "ERRO DE CÂMERA",
        "MODELO NÃO CARREGADO",
    }


@pytest.mark.parametrize(
    ("detectado", "esperado", "estado"),
    [
        (0, None, Estado.AGUARDANDO_CONFIGURACAO),
        (7, None, Estado.AGUARDANDO_CONFIGURACAO),
        (0, 20, Estado.CONTANDO),
        (19, 20, Estado.CONTANDO),
        (20, 20, Estado.QUANTIDADE_ATINGIDA),
        (21, 20, Estado.QUANTIDADE_EXCEDIDA),
        (1, 1, Estado.QUANTIDADE_ATINGIDA),
    ],
)
def test_compare_counts(detectado, esperado, estado):
    assert counter.compare_counts(detectado, esperado) is estado


def test_transicoes_sequencia_completa():
    """AGUARDANDO -> CONTANDO -> ATINGIDA -> EXCEDIDA -> (retirada) CONTANDO."""
    sem_cfg = ConfiguracaoContagem()
    cfg = ConfiguracaoContagem("parafuso", 3)
    sequencia = [
        (sem_cfg, 0, Estado.AGUARDANDO_CONFIGURACAO),
        (cfg, 0, Estado.CONTANDO),
        (cfg, 2, Estado.CONTANDO),
        (cfg, 3, Estado.QUANTIDADE_ATINGIDA),
        (cfg, 4, Estado.QUANTIDADE_EXCEDIDA),
        (cfg, 3, Estado.QUANTIDADE_ATINGIDA),
        (cfg, 0, Estado.CONTANDO),
    ]
    for c, detectado, esperado in sequencia:
        assert counter.determinar_estado(c, detectado) is esperado


@pytest.mark.parametrize(
    "cfg",
    [
        ConfiguracaoContagem(),
        ConfiguracaoContagem(classe="porca"),
        ConfiguracaoContagem(quantidade=10),
    ],
)
def test_configuracao_incompleta_aguarda(cfg):
    assert not cfg.configurada
    assert counter.determinar_estado(cfg, 10) is Estado.AGUARDANDO_CONFIGURACAO


@pytest.mark.parametrize("detectado", [-1, 1.5, "3", None, True])
def test_compare_detectado_invalido(detectado):
    with pytest.raises(ValueError):
        counter.compare_counts(detectado, 5)


@pytest.mark.parametrize("esperado", [0, -3, 2.0, "5", True])
def test_compare_esperado_invalido(esperado):
    with pytest.raises(ValueError):
        counter.compare_counts(3, esperado)


@pytest.mark.parametrize(
    "kwargs", [{"classe": "arruela"}, {"quantidade": 0}, {"quantidade": -1}, {"quantidade": 2.5}]
)
def test_configuracao_invalida(kwargs):
    with pytest.raises(ValueError):
        ConfiguracaoContagem(**kwargs)


def test_determinar_estado_detectado_invalido():
    with pytest.raises(ValueError):
        counter.determinar_estado(ConfiguracaoContagem("porca", 2), -1)


# ------------------------------------------------------------------ 7.3.3 erros
def test_erro_camera_tem_prioridade_sobre_contagem():
    cfg = ConfiguracaoContagem("parafuso", 5)
    assert counter.determinar_estado(cfg, 5, erro_camera=True) is Estado.ERRO_CAMERA


def test_erro_camera_tem_prioridade_sobre_aguardando():
    assert (
        counter.determinar_estado(ConfiguracaoContagem(), 0, erro_camera=True)
        is Estado.ERRO_CAMERA
    )


def test_modelo_nao_carregado_tem_prioridade_maxima():
    cfg = ConfiguracaoContagem("parafuso", 5)
    for c in (cfg, ConfiguracaoContagem()):
        estado = counter.determinar_estado(c, 0, erro_camera=True, modelo_carregado=False)
        assert estado is Estado.MODELO_NAO_CARREGADO


def test_erro_ignora_detectado():
    """Em erro nao ha contagem real; o valor de `detectado` nao e validado."""
    cfg = ConfiguracaoContagem("parafuso", 5)
    assert counter.determinar_estado(cfg, -1, erro_camera=True) is Estado.ERRO_CAMERA


def test_camera_recuperada_volta_a_contar():
    cfg = ConfiguracaoContagem("porca", 4)
    assert counter.determinar_estado(cfg, 0, erro_camera=True) is Estado.ERRO_CAMERA
    assert counter.determinar_estado(cfg, 2) is Estado.CONTANDO


@pytest.mark.parametrize(
    ("erro", "estado"),
    [
        (ModelError("sem best.pt"), Estado.MODELO_NAO_CARREGADO),
        (CameraError("falha"), Estado.ERRO_CAMERA),
        (ValueError("outro"), None),
        (RuntimeError("outro"), None),
    ],
)
def test_estado_de_erro(erro, estado):
    assert counter.estado_de_erro(erro) is estado
