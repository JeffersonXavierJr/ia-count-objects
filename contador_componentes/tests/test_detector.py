"""Testes de `detector.py` (Sprint 6, tarefas 6.2.1 e 6.2.2).

Os testes que precisam do modelo treinado (`models/best.pt`) ou de imagens do
dataset sao pulados quando esses arquivos nao existem — ambos ficam fora do
Git (ver .gitignore), entao podem estar ausentes em um clone novo.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from contador_componentes.app import config, detector

_PASTA_TESTE = Path(__file__).resolve().parent.parent / "dataset" / "images" / "test"

requer_modelo = pytest.mark.skipif(
    not Path(config.MODEL_PATH).is_file(),
    reason=f"modelo treinado ausente em {config.MODEL_PATH} (fora do Git)",
)


def _imagem_de_teste() -> Path | None:
    if not _PASTA_TESTE.is_dir():
        return None
    imagens = sorted(p for p in _PASTA_TESTE.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    return imagens[0] if imagens else None


@pytest.fixture(scope="module")
def modelo():
    """Carrega o modelo uma unica vez para todos os testes do modulo."""
    return detector.load_model()


# --- load_model -------------------------------------------------------------


def test_arquivo_inexistente_gera_model_error(tmp_path):
    with pytest.raises(detector.ModelError, match="nao encontrado"):
        detector.load_model(tmp_path / "nao_existe.pt")


def test_model_path_padrao_inexistente_gera_model_error(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODEL_PATH", tmp_path / "ausente.pt")
    with pytest.raises(detector.ModelError):
        detector.load_model()


def test_extensao_nao_suportada_gera_model_error(tmp_path):
    arquivo = tmp_path / "modelo.txt"
    arquivo.write_text("x")
    with pytest.raises(detector.ModelError, match="nao suportada"):
        detector.load_model(arquivo)


def test_arquivo_corrompido_gera_model_error(tmp_path):
    arquivo = tmp_path / "corrompido.pt"
    arquivo.write_bytes(b"isto nao e um modelo")
    with pytest.raises(detector.ModelError, match="Falha ao carregar"):
        detector.load_model(arquivo)


def test_model_path_e_absoluto_e_aponta_para_models():
    caminho = Path(config.MODEL_PATH)
    assert caminho.is_absolute()
    assert caminho.parent.name == "models" and caminho.name == "best.pt"


@pytest.mark.parametrize(
    "nomes",
    [{0: "porca", 1: "parafuso"}, {0: "person", 1: "bicycle"}, {0: "parafuso"}],
)
def test_classes_incompativeis_geram_model_error(nomes):
    with pytest.raises(detector.ModelError, match="incompativel"):
        detector._validar_classes(nomes, Path("x.pt"))


def test_classes_extras_geram_apenas_aviso(caplog):
    detector._validar_classes({0: "parafuso", 1: "porca", 2: "arruela"}, Path("x.pt"))
    assert "arruela" in caplog.text


@requer_modelo
def test_modelo_real_tem_classes_da_v1(modelo):
    assert dict(modelo.names) == detector.CLASSES_ESPERADAS


# --- run_inference ----------------------------------------------------------


@requer_modelo
def test_inferencia_em_imagem_de_teste_retorna_deteccoes_validas(modelo):
    caminho = _imagem_de_teste()
    if caminho is None:
        pytest.skip(f"nenhuma imagem em {_PASTA_TESTE} (dataset fora do Git)")

    frame = cv2.imread(str(caminho))
    assert frame is not None
    altura, largura = frame.shape[:2]

    deteccoes = detector.run_inference(modelo, frame)

    assert isinstance(deteccoes, list)
    assert len(deteccoes) > 0, f"nenhuma deteccao em {caminho.name}"
    for d in deteccoes:
        assert isinstance(d, detector.Deteccao)
        assert d.classe_id in detector.CLASSES_ESPERADAS
        assert d.classe_nome == detector.CLASSES_ESPERADAS[d.classe_id]
        assert config.CONFIDENCE_THRESHOLD <= d.confianca <= 1.0
        x1, y1, x2, y2 = d.bbox
        assert all(isinstance(v, int) for v in d.bbox)
        assert 0 <= x1 < x2 <= largura and 0 <= y1 < y2 <= altura

    confiancas = [d.confianca for d in deteccoes]
    assert confiancas == sorted(confiancas, reverse=True)


@requer_modelo
def test_imagem_em_branco_retorna_lista(modelo):
    branco = np.full((480, 640, 3), 255, dtype=np.uint8)
    deteccoes = detector.run_inference(modelo, branco)
    assert isinstance(deteccoes, list)
    assert deteccoes == []


@requer_modelo
def test_conf_maior_reduz_ou_mantem_deteccoes(modelo):
    caminho = _imagem_de_teste()
    if caminho is None:
        pytest.skip(f"nenhuma imagem em {_PASTA_TESTE} (dataset fora do Git)")
    frame = cv2.imread(str(caminho))
    baixa = detector.run_inference(modelo, frame, conf=0.25)
    alta = detector.run_inference(modelo, frame, conf=0.9)
    assert len(alta) <= len(baixa)
    assert all(d.confianca >= 0.9 for d in alta)


def test_deteccao_e_imutavel():
    d = detector.Deteccao(0, "parafuso", 0.9, (1, 2, 3, 4))
    with pytest.raises(Exception):
        d.confianca = 0.1  # type: ignore[misc]


@pytest.mark.parametrize("frame", [None, np.zeros((0, 0, 3), dtype=np.uint8)])
def test_frame_vazio_gera_value_error(frame):
    with pytest.raises(ValueError, match="vazio"):
        detector.run_inference(object(), frame)  # modelo nao e usado


@pytest.mark.parametrize("conf", [-0.1, 1.5])
def test_conf_fora_do_intervalo_gera_value_error(conf):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Confianca"):
        detector.run_inference(object(), frame, conf=conf)
