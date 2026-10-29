"""Calcula metricas de IA no split `test` a partir do `predicoes.json` (Sprint 5, tarefa 5.2).

Le o JSON gerado por `avaliar_teste.py` (predicoes brutas com confianca baixa
+ ground truth em pixels) e calcula, para um limiar de confianca (default
`config.CONFIDENCE_THRESHOLD`):

- 5.2.1/5.2.2 precisao e recall por classe e geral (matching guloso por
  confianca, IoU >= --iou e mesma classe; o NMS ja foi feito pelo ultralytics);
- 5.2.3 falsos positivos por classe, separados em "classe_errada" (a caixa
  casa com um GT de OUTRA classe com IoU >= --iou), "duplicata" (casa com um
  GT da mesma classe que ja foi usado por outra predicao) e "inexistente"
  (nao casa com nenhum GT: objeto que nao existe ou caixa mal localizada);
- 5.2.4 falsos negativos por classe;
- 5.2.5 erro de contagem por imagem e por classe, usando so a CONTAGEM de
  caixas (e o que a aplicacao usa — RB-01 conta apenas a classe selecionada):
  MAE, % de imagens com contagem exata e maior erro;
- AP50 / AP50-95 por classe (estilo ultralytics, interpolacao de 101 pontos)
  calculados sobre as predicoes brutas, para poder separar por grupo. O valor
  "oficial" do ultralytics pode ser obtido com `--com-map` (roda `YOLO.val`);
- varredura de limiares (`--varrer`): % de contagem exata e MAE por classe.

Todas as metricas saem no total e por grupo de risco de vazamento
(test x train/val, achado da tarefa 5.1):
- "independente": nenhuma foto de train/val tirada a <= 2 s;
- "risco_forte": ha foto de train/val a <= 2 s E quase identica
  (dHash de 256 bits com distancia de Hamming <= 30);
- "risco_moderado": ha foto a <= 2 s, mas nenhuma quase identica.
O horario vem do nome do arquivo (`frame_AAAAMMDD_HHMMSS*` ou
`WhatsApp-Image-AAAA-MM-DD-at-HH-MM-SS*`). Use `--sem-grupos` se as imagens
de train/val nao estiverem disponiveis.

Saida: `metricas.json` ao lado do `predicoes.json` (ou `--saida`) e tabelas
no terminal. Sem banco de dados (fora do escopo da v1).

Uso (a partir da RAIZ do repositorio, com o venv do projeto ativo):
    python contador_componentes/training/metricas_teste.py \\
        contador_componentes/training/runs/sprint5/baseline/predicoes.json
    python contador_componentes/training/metricas_teste.py <predicoes.json> \\
        --conf 0.5 --excluir 19-40-31 --saida <outro.json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent
PACOTE_DIR = TRAINING_DIR.parent
DATASET_DIR = PACOTE_DIR / "dataset"
DATASET_YAML = TRAINING_DIR / "dataset.yaml"

if str(PACOTE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PACOTE_DIR.parent))

from contador_componentes.app import config  # noqa: E402

LIMIARES_VARREDURA = (0.25, 0.35, 0.5, 0.6, 0.7)
JANELA_RAJADA_S = 2.0
HAMMING_QUASE_IDENTICA = 30
GRUPOS = ("independente", "risco_forte", "risco_moderado")
EXTENSOES = (".jpg", ".jpeg", ".png", ".bmp")


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

def iou(a: list[float], b: list[float]) -> float:
    """IoU de duas caixas xyxy (pixels)."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    uniao = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / uniao if uniao > 0 else 0.0


def casar(predicoes: list[dict], gt: list[dict], iou_min: float = 0.5) -> dict:
    """Matching guloso por confianca (maior primeiro) com o GT de maior IoU da mesma classe.

    Retorna {"tp": [pred...], "fp": [(pred, tipo)...], "fn": [gt...]}, com
    tipo em {"classe_errada", "duplicata", "inexistente"}.
    """
    usados: set[int] = set()
    tp, fp = [], []
    for p in sorted(predicoes, key=lambda x: x["conf"], reverse=True):
        melhor, melhor_iou = None, iou_min
        for i, g in enumerate(gt):
            if i in usados or g["classe_id"] != p["classe_id"]:
                continue
            v = iou(p["bbox_xyxy"], g["bbox_xyxy"])
            if v >= melhor_iou:
                melhor, melhor_iou = i, v
        if melhor is not None:
            usados.add(melhor)
            tp.append(p)
            continue
        ious = [(g["classe_id"], iou(p["bbox_xyxy"], g["bbox_xyxy"])) for g in gt]
        if any(c != p["classe_id"] and v >= iou_min for c, v in ious):
            tipo = "classe_errada"
        elif any(c == p["classe_id"] and v >= iou_min for c, v in ious):
            tipo = "duplicata"
        else:
            tipo = "inexistente"
        fp.append((p, tipo))
    fn = [g for i, g in enumerate(gt) if i not in usados]
    return {"tp": tp, "fp": fp, "fn": fn}


def ap_101(confs_tp: list[tuple[float, bool]], n_gt: int) -> float:
    """AP como no ultralytics: envelope de precisao + integral trapezoidal em 101 pontos."""
    import numpy as np

    if n_gt == 0:
        return float("nan")
    if not confs_tp:
        return 0.0  # sem predicoes da classe (o ultralytics tambem deixa AP = 0)
    ordenado = sorted(confs_tp, key=lambda x: x[0], reverse=True)
    acc_tp = np.cumsum([1.0 if t else 0.0 for _, t in ordenado])
    k = np.arange(1, len(ordenado) + 1)
    mrec = np.concatenate(([0.0], acc_tp / n_gt, [1.0]))
    mpre = np.concatenate(([1.0], acc_tp / k if len(k) else [], [0.0]))
    mpre = np.flip(np.maximum.accumulate(np.flip(mpre)))
    x = np.linspace(0, 1, 101)
    return float(np.trapezoid(np.interp(x, mrec, mpre), x))


# --------------------------------------------------------------------------
# Grupos de vazamento
# --------------------------------------------------------------------------

_RE_FRAME = re.compile(r"frame_(\d{8})_(\d{6})")
_RE_WHATS = re.compile(r"WhatsApp-Image-(\d{4})-(\d{2})-(\d{2})-at-(\d{2})-(\d{2})-(\d{2})")


def horario_do_nome(nome: str) -> datetime | None:
    """Extrai o horario da captura a partir do nome do arquivo (None se nao reconhecer)."""
    m = _RE_FRAME.search(nome)
    if m:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    m = _RE_WHATS.search(nome)
    if m:
        return datetime(*map(int, m.groups()))
    return None


def dhash256(caminho: Path) -> int:
    """dHash de 256 bits (16x16 diferencas horizontais em tons de cinza)."""
    import cv2

    img = cv2.imread(str(caminho), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(caminho)
    peq = cv2.resize(img, (17, 16), interpolation=cv2.INTER_AREA)
    bits = (peq[:, 1:] > peq[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def classificar_grupos(nomes_teste: list[str], pasta_teste: Path = DATASET_DIR / "images" / "test",
                       pastas_treino: list[Path] | None = None) -> dict[str, str]:
    """Grupo de risco de vazamento de cada imagem de teste (ver docstring do modulo).

    `pastas_treino` default: `dataset/images/train` e `dataset/images/val` (dataset atual).
    """
    if pastas_treino is None:
        pastas_treino = [DATASET_DIR / "images" / s for s in ("train", "val")]
    treino = [p for pasta in pastas_treino for p in Path(pasta).glob("*")
              if p.suffix.lower() in EXTENSOES]
    horarios_treino = [(p, horario_do_nome(p.name)) for p in treino]
    cache: dict[Path, int] = {}

    def h(p: Path) -> int:
        if p not in cache:
            cache[p] = dhash256(p)
        return cache[p]

    grupos = {}
    for nome in nomes_teste:
        t = horario_do_nome(nome)
        vizinhos = [p for p, tt in horarios_treino
                    if t is not None and tt is not None
                    and abs((tt - t).total_seconds()) <= JANELA_RAJADA_S]
        if not vizinhos:
            grupos[nome] = "independente"
            continue
        ht = h(pasta_teste / nome)
        dist = min(bin(ht ^ h(v)).count("1") for v in vizinhos)
        grupos[nome] = "risco_forte" if dist <= HAMMING_QUASE_IDENTICA else "risco_moderado"
    return grupos


# --------------------------------------------------------------------------
# Metricas
# --------------------------------------------------------------------------

def _div(a: float, b: float) -> float | None:
    return round(a / b, 4) if b else None


def metricas(imagens: list[dict], classes: list[int], conf: float, iou_min: float) -> dict:
    """Metricas agregadas de um conjunto de imagens para um limiar de confianca."""
    por_classe = {c: {"tp": 0, "fp": 0, "fn": 0, "n_gt": 0,
                      "fp_tipos": {"classe_errada": 0, "duplicata": 0, "inexistente": 0},
                      "erros_contagem": [], "ap": {}} for c in classes}
    por_imagem = []
    # para AP: (conf, eh_tp) por classe e limiar de IoU, sobre as predicoes brutas
    limiares_iou = [0.5 + 0.05 * i for i in range(10)]
    ap_dados = {c: {t: [] for t in limiares_iou} for c in classes}

    for img in imagens:
        aceitas = [p for p in img["predicoes"] if p["conf"] >= conf]
        r = casar(aceitas, img["gt"], iou_min)
        linha = {"imagem": img["imagem"], "fp": len(r["fp"]), "fn": len(r["fn"])}
        for c in classes:
            pc = por_classe[c]
            pc["tp"] += sum(1 for p in r["tp"] if p["classe_id"] == c)
            pc["fn"] += sum(1 for g in r["fn"] if g["classe_id"] == c)
            for p, tipo in r["fp"]:
                if p["classe_id"] == c:
                    pc["fp"] += 1
                    pc["fp_tipos"][tipo] += 1
            n_gt = sum(1 for g in img["gt"] if g["classe_id"] == c)
            n_pred = sum(1 for p in aceitas if p["classe_id"] == c)
            pc["n_gt"] += n_gt
            pc["erros_contagem"].append((n_pred - n_gt, img["imagem"]))
            linha[f"gt_{c}"], linha[f"pred_{c}"] = n_gt, n_pred
        por_imagem.append(linha)
        for t in limiares_iou:
            rb = casar(img["predicoes"], img["gt"], t)
            ids_tp = {id(p) for p in rb["tp"]}
            for p in img["predicoes"]:
                if p["classe_id"] in ap_dados:
                    ap_dados[p["classe_id"]][t].append((p["conf"], id(p) in ids_tp))

    saida = {"n_imagens": len(imagens), "classes": {}}
    tot = {"tp": 0, "fp": 0, "fn": 0}
    for c in classes:
        pc = por_classe[c]
        for k in tot:
            tot[k] += pc[k]
        erros = pc["erros_contagem"]
        abs_erros = [abs(e) for e, _ in erros]
        maior = max(erros, key=lambda x: abs(x[0])) if erros else (0, None)
        aps = [ap_101(ap_dados[c][t], pc["n_gt"]) for t in limiares_iou]
        saida["classes"][str(c)] = {
            "n_gt": pc["n_gt"], "tp": pc["tp"], "fp": pc["fp"], "fn": pc["fn"],
            "fp_tipos": pc["fp_tipos"],
            "precisao": _div(pc["tp"], pc["tp"] + pc["fp"]),
            "recall": _div(pc["tp"], pc["tp"] + pc["fn"]),
            "mae_contagem": _div(sum(abs_erros), len(abs_erros)),
            "pct_contagem_exata": _div(100 * sum(1 for e in abs_erros if e == 0), len(abs_erros)),
            "erro_medio_com_sinal": _div(sum(e for e, _ in erros), len(erros)),
            "maior_erro": {"erro": maior[0], "imagem": maior[1]},
            "ap50": round(aps[0], 4) if pc["n_gt"] else None,
            "ap50_95": round(sum(aps) / len(aps), 4) if pc["n_gt"] else None,
        }
    cl = saida["classes"].values()
    validos = [x for x in cl if x["ap50"] is not None]
    saida["geral"] = {
        **tot,
        "precisao": _div(tot["tp"], tot["tp"] + tot["fp"]),
        "recall": _div(tot["tp"], tot["tp"] + tot["fn"]),
        "map50": _div(sum(x["ap50"] for x in validos), len(validos)),
        "map50_95": _div(sum(x["ap50_95"] for x in validos), len(validos)),
    }
    saida["top_fp"] = sorted(([l["imagem"], l["fp"]] for l in por_imagem if l["fp"]),
                             key=lambda x: -x[1])[:5]
    saida["top_fn"] = sorted(([l["imagem"], l["fn"]] for l in por_imagem if l["fn"]),
                             key=lambda x: -x[1])[:5]
    saida["por_imagem"] = por_imagem
    return saida


def varredura(imagens: list[dict], classes: list[int], limiares, iou_min: float) -> dict:
    """% contagem exata e MAE por classe para varios limiares de confianca."""
    res = {}
    for t in limiares:
        m = metricas(imagens, classes, t, iou_min)
        res[str(t)] = {c: {"pct_contagem_exata": v["pct_contagem_exata"],
                           "mae_contagem": v["mae_contagem"],
                           "precisao": v["precisao"], "recall": v["recall"]}
                       for c, v in m["classes"].items()}
    return res


def map_ultralytics(modelo: str, projeto: Path, nome: str) -> dict:
    """mAP oficial do ultralytics no split test (referencia; roda a partir da raiz do repo)."""
    from ultralytics import YOLO

    r = YOLO(modelo).val(data=str(DATASET_YAML.relative_to(PACOTE_DIR.parent)), split="test",
                         device="cpu", workers=0, batch=4, plots=False,
                         project=str(projeto.resolve()), name=nome, exist_ok=True, verbose=False)
    return {"map50": round(float(r.box.map50), 4), "map50_95": round(float(r.box.map), 4),
            "precisao": round(float(r.box.mp), 4), "recall": round(float(r.box.mr), 4),
            "por_classe": {str(c): {"ap50": round(float(r.box.ap50[i]), 4),
                                    "ap50_95": round(float(r.box.ap[i]), 4)}
                           for i, c in enumerate(r.box.ap_class_index)}}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _fmt(v, casas=3) -> str:
    return "-" if v is None else f"{v:.{casas}f}"


def imprimir(rotulo: str, m: dict, nomes: dict[str, str]) -> None:
    g = m["geral"]
    print(f"\n== {rotulo} ({m['n_imagens']} imagens) ==")
    print("classe    | n_gt |  TP |  FP (cls/dup/inex) |  FN |   P   |   R   | MAE cont | %exata | maior erro | AP50  | AP50-95")
    for c, v in m["classes"].items():
        t = v["fp_tipos"]
        print(f"{nomes[c]:<9} | {v['n_gt']:4} | {v['tp']:3} | {v['fp']:3} ({t['classe_errada']}/{t['duplicata']}/"
              f"{t['inexistente']}){'':<6} | {v['fn']:3} | {_fmt(v['precisao'])} | {_fmt(v['recall'])} | "
              f"{_fmt(v['mae_contagem'], 2):>8} | {_fmt(v['pct_contagem_exata'], 1):>6} | "
              f"{v['maior_erro']['erro']:+d}{'':<8} | {_fmt(v['ap50'])} | {_fmt(v['ap50_95'])}")
    print(f"{'geral':<9} |      | {g['tp']:3} | {g['fp']:3}{'':<16} | {g['fn']:3} | {_fmt(g['precisao'])} | "
          f"{_fmt(g['recall'])} |          |        |            | {_fmt(g['map50'])} | {_fmt(g['map50_95'])}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Metricas de IA no split test a partir do predicoes.json.")
    parser.add_argument("predicoes", type=Path, help="predicoes.json gerado por avaliar_teste.py")
    parser.add_argument("--conf", type=float, default=config.CONFIDENCE_THRESHOLD,
                        help=f"limiar de confianca (default: config.CONFIDENCE_THRESHOLD = {config.CONFIDENCE_THRESHOLD})")
    parser.add_argument("--iou", type=float, default=0.5, help="IoU minimo para casar (default: 0.5)")
    parser.add_argument("--varrer", type=float, nargs="*", default=list(LIMIARES_VARREDURA),
                        help="limiares para a tabela de contagem (default: 0.25 0.35 0.5 0.6 0.7)")
    parser.add_argument("--excluir", nargs="*", default=[],
                        help="trechos de nome de imagem a excluir (ex.: 19-40-31)")
    parser.add_argument("--sem-grupos", action="store_true",
                        help="nao calcula grupos de vazamento (dispensa imagens de train/val)")
    parser.add_argument("--treino", type=Path, nargs="+", default=None,
                        help="pastas de imagens de treino/val usadas para os grupos de vazamento "
                        "(default: dataset/images/train e val; use as do dataset ANTIGO para um "
                        "modelo treinado nele)")
    parser.add_argument("--com-map", action="store_true",
                        help="roda tambem YOLO.val(split='test') para o mAP oficial do ultralytics")
    parser.add_argument("--saida", type=Path, default=None,
                        help="arquivo JSON de saida (default: metricas.json ao lado do predicoes.json)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dados = json.loads(args.predicoes.read_text(encoding="utf-8"))
    nomes = dados["classes"]
    classes = sorted(int(c) for c in nomes)
    imagens = [i for i in dados["imagens"] if not any(x in i["imagem"] for x in args.excluir)]

    grupos = {} if args.sem_grupos else classificar_grupos(
        [i["imagem"] for i in imagens], pastas_treino=args.treino)
    conjuntos = {"total": imagens}
    for gname in GRUPOS:
        sub = [i for i in imagens if grupos.get(i["imagem"]) == gname]
        if sub:
            conjuntos[gname] = sub

    resultado = {"predicoes": str(args.predicoes), "modelo": dados.get("modelo"),
                 "conf": args.conf, "iou": args.iou, "excluidas": args.excluir,
                 "pastas_treino_grupos": [str(p) for p in args.treino] if args.treino else "dataset atual (train+val)",
                 "grupos": grupos, "metricas": {}, "varredura": {}}
    for rotulo, sub in conjuntos.items():
        m = metricas(sub, classes, args.conf, args.iou)
        resultado["metricas"][rotulo] = m
        imprimir(f"{rotulo} conf={args.conf}", m, nomes)
        if rotulo == "total":
            print("top FP:", m["top_fp"])
            print("top FN:", m["top_fn"])
        if args.varrer:
            resultado["varredura"][rotulo] = varredura(sub, classes, args.varrer, args.iou)

    if args.varrer:
        print("\n== varredura de limiar: %exata / MAE por classe ==")
        for rotulo, v in resultado["varredura"].items():
            for t, porc in v.items():
                txt = "  ".join(f"{nomes[c]} {_fmt(x['pct_contagem_exata'], 1)}% / {_fmt(x['mae_contagem'], 2)}"
                                for c, x in porc.items())
                print(f"{rotulo:<15} conf={t:<5} {txt}")

    if args.com_map:
        nome = f"val_test_{args.predicoes.parent.name}"
        resultado["map_ultralytics"] = map_ultralytics(dados["modelo"], args.predicoes.parent.parent, nome)
        print("\nmAP ultralytics (test):", resultado["map_ultralytics"])

    saida = args.saida or args.predicoes.parent / "metricas.json"
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSalvo em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
