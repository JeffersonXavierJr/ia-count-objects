"""Testes da parte de simulação de `scripts/avaliar_estabilizacao.py` (tarefa 8.2).

Só lógica pura: contagens brutas sintéticas -> `EstabilizadorContagem` com
vários N -> métricas. Nada aqui abre câmera nem carrega modelo; os modos
`--webcam` / `--imagens` dependem de hardware/modelo e são cobertos pelo
checklist manual em `tests/relatorio_estabilizacao.md`.

Observação: os testes NÃO fixam qual N é o "certo" (ponto em aberto do PRD,
seção 29 — "número de frames para confirmação"); só verificam que as métricas
usadas para comparar os N estão corretas.
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import pytest

from contador_componentes.app.counter import Estado
from contador_componentes.scripts import avaliar_estabilizacao as av

C = Estado.CONTANDO
A = Estado.QUANTIDADE_ATINGIDA
E = Estado.QUANTIDADE_EXCEDIDA

# Exemplo literal do PRD, seção 16 (alvo 20).
SEQ_PRD = [19, 20, 19, 20, 20]


# ------------------------------------------------------------------ simular
def test_simular_exemplo_prd_n1_pisca():
    estados, r = av.simular(SEQ_PRD, "parafuso", 20, 1)
    assert estados == [C, A, C, A, A]
    assert (r.mudancas_estado, r.entradas_atingida, r.saidas_atingida) == (3, 2, 1)
    assert r.primeira_atingida == 2
    assert r.frames_atingida == 3


def test_simular_exemplo_prd_n2_so_no_fim():
    estados, r = av.simular(SEQ_PRD, "parafuso", 20, 2)
    assert estados == [C, C, C, C, A]
    assert (r.mudancas_estado, r.entradas_atingida, r.saidas_atingida) == (1, 1, 0)
    assert r.primeira_atingida == 5


@pytest.mark.parametrize("n", [3, 5])
def test_simular_exemplo_prd_n_maior_nao_atinge(n):
    estados, r = av.simular(SEQ_PRD, "parafuso", 20, n)
    assert estados == [C] * 5
    assert r.mudancas_estado == 0
    assert r.primeira_atingida is None


def test_primeiro_frame_no_alvo_com_n1_conta_como_entrada():
    # Convenção documentada: estado anterior ao 1º frame = CONTANDO.
    _, r = av.simular([4], "porca", 4, 1)
    assert (r.mudancas_estado, r.entradas_atingida, r.primeira_atingida) == (1, 1, 1)


def test_simular_conta_entradas_em_excedida():
    estados, r = av.simular([5, 6, 5, 3], "porca", 4, 3)
    assert estados == [C, C, E, C]
    assert r.entradas_excedida == 1
    assert r.mudancas_estado == 2
    assert r.entradas_atingida == 0


def test_elegivel_depende_do_tamanho_da_sequencia():
    _, r5 = av.simular([4, 4, 4], "porca", 4, 5)
    _, r3 = av.simular([4, 4, 4], "porca", 4, 3)
    assert not r5.elegivel and r5.primeira_atingida is None
    assert r3.elegivel and r3.primeira_atingida == 3


def test_simular_varios_mesma_sequencia_na_ordem_dos_ns():
    resultados = av.simular_varios(SEQ_PRD, 0, 20, [1, 2, 5])
    assert [r.n for r in resultados] == [1, 2, 5]
    assert [r.frames for r in resultados] == [5, 5, 5]
    assert [r.entradas_atingida for r in resultados] == [2, 1, 0]


def test_aceita_classe_por_nome_ou_id():
    assert av.simular(SEQ_PRD, 0, 20, 2)[1] == av.simular(SEQ_PRD, "Parafuso", 20, 2)[1]


def test_alvo_invalido_rejeitado():
    with pytest.raises(ValueError):
        av.simular([1, 2], "parafuso", 0, 3)


@pytest.mark.parametrize("semente", range(5))
def test_n_maior_nunca_gera_mais_entradas_em_atingida(semente):
    """Sem histerese de saída, entradas = nº de trechos no alvo com tamanho >= N,
    logo não podem crescer com N (propriedade usada no relatório)."""
    rnd = random.Random(semente)
    seq = [rnd.choice([3, 4, 4, 4, 5]) for _ in range(200)]
    entradas = [r.entradas_atingida for r in av.simular_varios(seq, "porca", 4, range(1, 12))]
    assert entradas == sorted(entradas, reverse=True)


# ------------------------------------------------------ oscilação / parse
def test_oscilacao_bruta():
    o = av.oscilacao_bruta(SEQ_PRD, 20)
    assert (o.frames, o.mudancas, o.valores, o.frames_no_alvo) == (5, 3, (19, 20), 3)
    assert av.oscilacao_bruta([], 1).mudancas == 0


def test_parse_ns_ordena_e_remove_repetidos():
    assert av.parse_ns("5, 1,3,3") == [1, 3, 5]


@pytest.mark.parametrize("texto", ["", "0,3", "a,b", "-1"])
def test_parse_ns_invalido(texto):
    with pytest.raises(ValueError):
        av.parse_ns(texto)


# ------------------------------------------- nomes de frame e ordenação
@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("frame_20261021_202930.jpg", ("20261021", "202930", 0)),
        ("frame_20261021_202930_004.jpg", ("20261021", "202930", 4)),
        ("frame_20260923_204758_jpg.rf.c79.jpg", ("20260923", "204758", 0)),
        ("frame_20260923_204758_006_jpg.rf.025.txt", ("20260923", "204758", 6)),
        ("WhatsApp-Image-2026-10-22_jpeg.rf.b16.jpg", None),
    ],
)
def test_chave_frame(nome, esperado):
    assert av.chave_frame(nome) == esperado


def test_ordenacao_como_video_corrige_ordem_alfabetica_do_roboflow():
    nomes = [
        "frame_20260923_204759_jpg.rf.x.jpg",
        "frame_20260923_204758_006_jpg.rf.x.jpg",
        "frame_20260923_204758_jpg.rf.x.jpg",
        "frame_20260923_204758_002_jpg.rf.x.jpg",
        "outra.jpg",
    ]
    ordenados = [p.name for p in sorted(map(Path, nomes), key=av.chave_ordenacao)]
    assert ordenados == [
        "frame_20260923_204758_jpg.rf.x.jpg",
        "frame_20260923_204758_002_jpg.rf.x.jpg",
        "frame_20260923_204758_006_jpg.rf.x.jpg",
        "frame_20260923_204759_jpg.rf.x.jpg",
        "outra.jpg",
    ]


# --------------------------------------------------------------- cenas
def _reg(i, t, gt=None, n=0):
    return av.Registro(indice=i, contagens={"parafuso": n, "porca": 0}, tempo_s=t, gt=gt)


def test_agrupar_cenas_por_intervalo_de_tempo_e_mudanca_de_gt():
    g1 = {"parafuso": 3, "porca": 0}
    g2 = {"parafuso": 4, "porca": 0}
    regs = [_reg(0, 100, g1), _reg(1, 100, g1), _reg(2, 101, g1),  # cena 0
            _reg(3, 105, g1),                                      # gap > 1 s
            _reg(4, 105, g2),                                      # GT mudou
            _reg(5, None, g2)]                                     # tempo desconhecido
    cenas = av.agrupar_cenas(regs, gap_s=1.0)
    assert [[r.indice for r in c] for c in cenas] == [[0, 1, 2], [3], [4], [5]]
    assert [r.cena for r in regs] == [0, 0, 0, 1, 2, 3]


def test_agrupar_cenas_respeita_coluna_cena_existente():
    regs = [_reg(0, None), _reg(1, None), _reg(2, None)]
    for r, c in zip(regs, [7, 7, 9]):
        r.cena = c
    assert [[r.indice for r in c] for c in av.agrupar_cenas(regs)] == [[0, 1], [2]]


def test_contar_label_yolo(tmp_path):
    p = tmp_path / "frame_20261021_202930.txt"
    p.write_text("0 0.5 0.5 0.1 0.1\n1 0.2 0.2 0.1 0.1\n0 0.1 0.1 0.1 0.1\n\n",
                 encoding="utf-8")
    assert av.contar_label(p) == {"parafuso": 2, "porca": 1}


# ------------------------------------------------------------------ CSV
def test_csv_ida_e_volta(tmp_path):
    regs = [
        av.Registro(0, {"parafuso": 3, "porca": 1}, tempo_s=0.0),
        av.Registro(1, {"parafuso": 4, "porca": 1}, tempo_s=0.1, arquivo="a.jpg",
                    origem="val", gt={"parafuso": 4, "porca": 1}, cena=2),
    ]
    p = tmp_path / "c.csv"
    av.salvar_csv(p, regs)
    lidos = av.ler_csv(p)
    assert [r.contagens for r in lidos] == [r.contagens for r in regs]
    assert lidos[0].gt is None and lidos[1].gt == {"parafuso": 4, "porca": 1}
    assert (lidos[1].cena, lidos[1].origem, lidos[1].arquivo) == (2, "val", "a.jpg")


def test_ler_csv_sem_coluna_de_classe(tmp_path):
    p = tmp_path / "ruim.csv"
    p.write_text("indice,parafuso\n0,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="porca"):
        av.ler_csv(p)


def test_fps_so_e_derivado_de_csv_da_webcam():
    webcam = [av.Registro(i, {"parafuso": 0, "porca": 0}, tempo_s=i / 10) for i in range(11)]
    assert av._fps_de_tempos(webcam) == pytest.approx(10.0)
    # CSV vindo de --imagens: tempo_s = horário do nome do arquivo, não é FPS.
    imagens = [av.Registro(i, {"parafuso": 0, "porca": 0}, tempo_s=float(i), arquivo="x.jpg")
               for i in range(3)]
    assert av._fps_de_tempos(imagens) is None


# ------------------------------------------------- main --csv (sem modelo)
def test_main_csv_sequencia_unica(tmp_path, capsys):
    p = tmp_path / "webcam.csv"
    regs = [av.Registro(i, {"parafuso": c, "porca": 0}, tempo_s=i * 0.1)
            for i, c in enumerate(SEQ_PRD)]
    av.salvar_csv(p, regs)
    assert av.main(["--csv", str(p), "--classe", "parafuso", "--alvo", "20", "--ns", "1,2"]) == 0
    out = capsys.readouterr().out
    assert "FPS (medido ou --fps)=10.00" in out
    assert "| 1 | 5 | 3 | 2 | 1 |" in out  # N=1: 3 mudanças, 2 entradas, 1 saída
    assert "| 2 | 5 | 1 | 1 | 0 |" in out


def test_main_csv_alvo_gt_com_offsets(tmp_path, capsys):
    gt = {"parafuso": 2, "porca": 0}
    regs = [av.Registro(i, {"parafuso": c, "porca": 0}, tempo_s=100.0, arquivo=f"f{i}.jpg",
                        gt=gt) for i, c in enumerate([2, 3, 2, 2, 2])]
    p = tmp_path / "imgs.csv"
    av.salvar_csv(p, regs)
    assert av.main(["--csv", str(p), "--alvo-gt", "--ns", "1,3", "--offsets", "0,1",
                    "--fps", "20"]) == 0
    out = capsys.readouterr().out
    assert "Sequencias (cena x classe presente): 1." in out
    assert "alvo = GT+1" in out
    assert "| 2 3 2 2 2 |" in out


def test_main_exige_classe_e_alvo_sem_alvo_gt(tmp_path):
    p = tmp_path / "x.csv"
    av.salvar_csv(p, [av.Registro(0, {"parafuso": 1, "porca": 0})])
    with pytest.raises(SystemExit):
        av.main(["--csv", str(p)])


def test_importar_modulo_nao_carrega_opencv_nem_ultralytics():
    codigo = (
        "import sys; import contador_componentes.scripts.avaliar_estabilizacao; "
        "print('cv2' in sys.modules, 'ultralytics' in sys.modules)"
    )
    raiz_repo = Path(__file__).resolve().parents[2]
    saida = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                           check=True, cwd=raiz_repo).stdout.strip()
    assert saida == "False False"
