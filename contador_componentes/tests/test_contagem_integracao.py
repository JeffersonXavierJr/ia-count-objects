"""Testes de integração detector -> counter com imagens reais (Sprint 7, tarefa 7.4).

Automatiza os cenários "manuais" da 7.4 usando fotos do split `test` do
dataset (nunca vistas no treino) e o ground truth (GT) dos labels YOLO:

- 7.4.1 quantidade exata de parafusos como alvo -> QUANTIDADE ATINGIDA;
- 7.4.2 cena mista (parafusos + porcas): a contagem exibida só considera a
  classe selecionada (RB-01);
- 7.4.3 transições AGUARDANDO -> CONTANDO -> ATINGIDA -> EXCEDIDA com uma
  sequência de fotos de quantidades crescentes (simula peças sendo colocadas
  na bandeja) + estados de erro (modelo inexistente, câmera inválida).

Rodam com os dois modelos disponíveis: "A" = `models/best.pt` (baseline,
config.MODEL_PATH) e "B" = `training/runs/yolo26n_porcas_v2/weights/best.pt`.
Cada modelo/imagem ausente (ficam fora do Git) faz o teste ser PULADO.

Erros de contagem do MODELO já conhecidos (varredura de 28/10/2026, conf=0.5)
são marcados como `xfail` (não são bugs do counter, e sim da detecção); se o
modelo melhorar e acertar, o teste passa normalmente. Imagens com labels
incompletos (validacao_sprint5.md, 5.3) NÃO são usadas como verdade.

SUPOSIÇÃO: sem estabilização temporal (Sprint 8) — cada imagem é um frame.

Uso (raiz do repositório): python -m pytest contador_componentes/tests -q
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from contador_componentes.app import camera, config, counter, detector
from contador_componentes.app.counter import ConfiguracaoContagem, Estado

_RAIZ = Path(__file__).resolve().parent.parent
_IMAGENS = _RAIZ / "dataset" / "images" / "test"
_LABELS = _RAIZ / "dataset" / "labels" / "test"

MODELOS = {
    "A": Path(config.MODEL_PATH),
    "B": _RAIZ / "training" / "runs" / "yolo26n_porcas_v2" / "weights" / "best.pt",
}

# (modelo, prefixo da imagem, classe) -> contagem errada observada do modelo.
FALHAS_CONHECIDAS: dict[tuple[str, str, str], int] = {
    ("B", "frame_20260930_210437", "parafuso"): 9,   # GT 12, parafusos encostados
    ("A", "frame_20261021_202903", "parafuso"): 5,   # GT 4, objeto estranho
    ("A", "frame_20260930_204903", "parafuso"): 13,  # GT 14
    ("B", "frame_20260930_204903", "parafuso"): 13,  # GT 14
    ("A", "frame_20260930_210643", "parafuso"): 5,   # GT 6, encostados
    ("B", "frame_20260930_210643", "parafuso"): 5,   # GT 6, encostados
    ("A", "frame_20261021_202458_001", "parafuso"): 5,  # GT 4
    ("A", "frame_20261021_202458_001", "porca"): 1,     # GT 2
    ("A", "frame_20261021_202525", "parafuso"): 7,      # GT 4, bits/objetos
    ("A", "frame_20261021_202525", "porca"): 1,         # GT 2
    ("A", "frame_20261021_202334", "parafuso"): 6,      # GT 4, objetos estranhos
    ("A", "frame_20261021_202334", "porca"): 2,         # GT 1, parafuso de topo
    # A quase não detecta porcas nas fotos WhatsApp (outro domínio).
    ("A", "WhatsApp-Image-2026-10-26-at-21-59-24_", "porca"): 0,      # GT 4
    ("A", "WhatsApp-Image-2026-10-26-at-21-59-25-4-", "porca"): 0,    # GT 6
    ("A", "WhatsApp-Image-2026-10-26-at-21-59-23-2-", "porca"): 0,    # GT 11
}


# ---------------------------------------------------------------- utilitários

def _imagem(prefixo: str) -> Path:
    candidatas = sorted(_IMAGENS.glob(f"{prefixo}*")) if _IMAGENS.is_dir() else []
    if len(candidatas) != 1:
        pytest.skip(f"imagem de teste {prefixo!r} ausente ou ambígua")
    return candidatas[0]


def _gt(img: Path, classe: str) -> int:
    classe_id = counter.resolver_classe(classe)
    linhas = (_LABELS / f"{img.stem}.txt").read_text().splitlines()
    return sum(1 for l in linhas if l.strip() and int(l.split()[0]) == classe_id)


@pytest.fixture(scope="module", params=sorted(MODELOS))
def modelo(request):
    """(nome, modelo carregado) para cada modelo disponível."""
    caminho = MODELOS[request.param]
    if not caminho.is_file():
        pytest.skip(f"modelo {request.param} ausente em {caminho} (fora do Git)")
    return request.param, detector.load_model(caminho)


_cache: dict[tuple[str, Path], list] = {}


def _deteccoes(modelo, img: Path) -> list:
    nome, m = modelo
    if (nome, img) not in _cache:
        _cache[(nome, img)] = detector.run_inference(m, cv2.imread(str(img)))
    return _cache[(nome, img)]


def _contar(modelo, prefixo: str, classe: str) -> tuple[int, int, Path]:
    """(detectado pelo modelo na classe, GT da classe, imagem)."""
    img = _imagem(prefixo)
    dets = _deteccoes(modelo, img)
    detectado = counter.count_objects(counter.filter_by_class(dets, classe))
    return detectado, _gt(img, classe), img


def _xfail_se_falha_conhecida(nome: str, prefixo: str, classe: str, detectado: int, gt: int):
    if detectado != gt and (nome, prefixo, classe) in FALHAS_CONHECIDAS:
        pytest.xfail(f"erro conhecido do modelo {nome}: contou {detectado}, GT {gt}")


# ------------------------------------------------- 7.4.1 quantidade exata alvo

PARAFUSOS_SO = [
    "frame_20260923_204911_001",  # 1
    "frame_20260930_205533",      # 3
    "frame_20261021_202903",      # 4 (+ objetos estranhos)
    "frame_20260923_205522",      # 6
    "frame_20260923_205009_003",  # 7
    "frame_20260930_210437",      # 12 (encostados)
    "frame_20260923_204759_008",  # 14
]


@pytest.mark.parametrize("prefixo", PARAFUSOS_SO)
def test_7_4_1_alvo_igual_gt_atinge(modelo, prefixo):
    detectado, gt, _ = _contar(modelo, prefixo, "parafuso")
    _xfail_se_falha_conhecida(modelo[0], prefixo, "parafuso", detectado, gt)
    cfg = ConfiguracaoContagem("parafuso", gt)
    assert detectado == gt
    assert counter.determinar_estado(cfg, detectado) is Estado.QUANTIDADE_ATINGIDA


# ------------------------------------------------------------ 7.4.2 cena mista

MISTAS = [
    "frame_20260930_204903",      # 14 parafusos + 2 porcas
    "frame_20260930_210643",      # 6 + 2
    "frame_20261021_202458_001",  # 4 + 2
    "frame_20261021_202525",      # 4 + 2
    "frame_20261021_202334",      # 4 + 1
]


@pytest.mark.parametrize("prefixo", MISTAS)
def test_7_4_2_rb01_outra_classe_ignorada(modelo, prefixo):
    """Vale mesmo quando o modelo erra: o exibido é só a classe selecionada."""
    img = _imagem(prefixo)
    dets = _deteccoes(modelo, img)
    n_par = counter.count_objects(counter.filter_by_class(dets, "parafuso"))
    n_por = counter.count_objects(counter.filter_by_class(dets, "porca"))
    assert n_par == sum(d.classe_id == 0 for d in dets)
    assert n_por == sum(d.classe_id == 1 for d in dets)
    assert n_par + n_por == len(dets)  # só existem as 2 classes da v1
    assert n_por > 0, "cena mista deveria ter porcas detectadas"


@pytest.mark.parametrize("classe", ["parafuso", "porca"])
@pytest.mark.parametrize("prefixo", MISTAS)
def test_7_4_2_misto_alvo_igual_gt_da_classe(modelo, prefixo, classe):
    detectado, gt, _ = _contar(modelo, prefixo, classe)
    _xfail_se_falha_conhecida(modelo[0], prefixo, classe, detectado, gt)
    assert detectado == gt
    assert counter.determinar_estado(
        ConfiguracaoContagem(classe, gt), detectado
    ) is Estado.QUANTIDADE_ATINGIDA


# ------------------------------------------------------------ 7.4.3 transições

# Fotos com quantidades crescentes da mesma classe; alvo fixo = 6.
SEQ_PARAFUSO = [
    ("frame_20260930_210535", Estado.CONTANDO),             # 0 (bandeja vazia)
    ("frame_20260923_204911_001", Estado.CONTANDO),         # 1
    ("frame_20260930_205533", Estado.CONTANDO),             # 3
    ("frame_20260923_205522", Estado.QUANTIDADE_ATINGIDA),  # 6
    ("frame_20260923_205009_003", Estado.QUANTIDADE_EXCEDIDA),  # 7
]
SEQ_PORCA = [
    ("frame_20261021_202611", Estado.CONTANDO),                       # 2
    ("WhatsApp-Image-2026-10-26-at-21-59-24_", Estado.CONTANDO),      # 4
    ("WhatsApp-Image-2026-10-26-at-21-59-25-4-", Estado.QUANTIDADE_ATINGIDA),  # 6
    ("WhatsApp-Image-2026-10-26-at-21-59-23-2-", Estado.QUANTIDADE_EXCEDIDA),  # 11
]


@pytest.mark.parametrize("classe, sequencia", [("parafuso", SEQ_PARAFUSO), ("porca", SEQ_PORCA)])
def test_7_4_3_transicoes_com_imagens_reais(modelo, classe, sequencia):
    alvo = 6
    # Antes de configurar: aguardando, qualquer que seja a cena.
    det0, _, _ = _contar(modelo, sequencia[0][0], classe)
    assert counter.determinar_estado(ConfiguracaoContagem(), det0) is Estado.AGUARDANDO_CONFIGURACAO

    cfg = ConfiguracaoContagem(classe, alvo)
    obtidos, esperados = [], []
    for prefixo, esperado in sequencia:
        detectado, gt, _ = _contar(modelo, prefixo, classe)
        _xfail_se_falha_conhecida(modelo[0], prefixo, classe, detectado, gt)
        obtidos.append(counter.determinar_estado(cfg, detectado))
        esperados.append(esperado)
    assert obtidos == esperados


def test_7_4_3_modelo_inexistente(tmp_path):
    with pytest.raises(detector.ModelError) as exc:
        detector.load_model(tmp_path / "nao_existe.pt")
    assert counter.estado_de_erro(exc.value) is Estado.MODELO_NAO_CARREGADO
    cfg = ConfiguracaoContagem("parafuso", 6)
    assert counter.determinar_estado(cfg, 0, modelo_carregado=False) is Estado.MODELO_NAO_CARREGADO


def test_7_4_3_camera_invalida():
    # SUPOSIÇÃO: nenhuma máquina de teste tem câmera no índice 99.
    with pytest.raises(camera.CameraError) as exc:
        camera.open_camera(99)
    assert counter.estado_de_erro(exc.value) is Estado.ERRO_CAMERA
    cfg = ConfiguracaoContagem("parafuso", 6)
    assert counter.determinar_estado(cfg, 0, erro_camera=True) is Estado.ERRO_CAMERA


# ------------------------------------------------- script de teste manual (CLI)

def test_script_testar_contagem(capsys):
    from contador_componentes.scripts import testar_contagem

    if not Path(config.MODEL_PATH).is_file():
        pytest.skip("modelo A ausente")
    img = _imagem("frame_20260923_205522")  # 6 parafusos
    assert testar_contagem.main([str(img), "--classe", "parafuso", "--alvo", "6"]) == 0
    saida = capsys.readouterr().out
    assert "detectado=6" in saida and "QUANTIDADE ATINGIDA" in saida

    assert testar_contagem.main([str(img), "--modelo", "nao_existe.pt"]) == 1
    assert "MODELO NÃO CARREGADO" in capsys.readouterr().err
