"""Roda um modelo treinado sobre o split `test` e salva predicoes brutas (Sprint 5, tarefa 5.1).

Objetivo: validar o modelo em fotos NUNCA vistas no treino (PRD secao 21,
Etapa 5). Este script so faz INFERENCIA e grava os resultados; o calculo de
precision/recall/erro de contagem fica para a tarefa 5.2, a partir do JSON.

Saidas em `<saida>/<nome>/` (default `contador_componentes/training/runs/sprint5/`,
fora do Git):
- `predicoes.json`: predicoes brutas por imagem com confianca baixa
  (`--conf-bruta`, default 0.01) para permitir varrer limiares depois, junto
  com o ground truth do label YOLO convertido para pixels;
- `visual/<imagem>.jpg`: imagem com as predicoes acima de `--conf-visual`
  (default `config.CONFIDENCE_THRESHOLD`) desenhadas pelo `app/overlay.py`,
  o ground truth em contorno fino verde e um cabecalho com as contagens
  GT x predicao por classe.

Formato do `predicoes.json`:
    {
      "modelo": "<caminho do .pt>", "imgsz": 640, "conf_bruta": 0.01,
      "classes": {"0": "parafuso", "1": "porca"},
      "imagens": [
        {"imagem": "<nome do arquivo>", "largura": 640, "altura": 640,
         "predicoes": [{"classe_id": 0, "conf": 0.93,
                        "bbox_xyxy": [x1, y1, x2, y2]}, ...],
         "gt": [{"classe_id": 1, "bbox_xyxy": [x1, y1, x2, y2]}, ...]}
      ]
    }
Coordenadas em pixels da imagem original (float, 2 casas).

Treino e inferencia sao separados (PRD 13.4): o modelo e apenas carregado
(via `app/detector.load_model`, que valida as classes 0=parafuso/1=porca).

Uso (a partir da RAIZ do repositorio, com o venv do projeto ativo):
    python contador_componentes/training/avaliar_teste.py --nome baseline
    python contador_componentes/training/avaliar_teste.py \\
        --modelo contador_componentes/training/runs/<run>/weights/best.pt --nome <run>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent
PACOTE_DIR = TRAINING_DIR.parent
DEFAULT_TEST_DIR = PACOTE_DIR / "dataset" / "images" / "test"
DEFAULT_SAIDA = TRAINING_DIR / "runs" / "sprint5"
DEFAULT_CONF_BRUTA = 0.01

# Permite rodar como script (`python .../avaliar_teste.py`) a partir da raiz
# do repo, alem de `python -m contador_componentes.training.avaliar_teste`.
if str(PACOTE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PACOTE_DIR.parent))

from contador_componentes.app import config  # noqa: E402

COR_GT = (0, 200, 0)  # verde (BGR), contorno fino do ground truth
EXTENSOES = (".jpg", ".jpeg", ".png", ".bmp")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Le os parametros da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Inferencia de um modelo sobre o split test (predicoes brutas + imagens anotadas).",
    )
    parser.add_argument("--modelo", type=Path, default=config.MODEL_PATH,
                        help="pesos do modelo (default: config.MODEL_PATH = models/best.pt)")
    parser.add_argument("--nome", required=True,
                        help="nome da pasta de saida dentro de --saida (ex.: baseline)")
    parser.add_argument("--imagens", type=Path, default=DEFAULT_TEST_DIR,
                        help="pasta de imagens (default: dataset/images/test); "
                        "labels sao procurados trocando 'images' por 'labels'")
    parser.add_argument("--saida", type=Path, default=DEFAULT_SAIDA,
                        help="pasta base das saidas (default: training/runs/sprint5)")
    parser.add_argument("--conf-bruta", type=float, default=DEFAULT_CONF_BRUTA,
                        help=f"confianca minima gravada no JSON (default: {DEFAULT_CONF_BRUTA})")
    parser.add_argument("--conf-visual", type=float, default=config.CONFIDENCE_THRESHOLD,
                        help="confianca minima desenhada nas imagens "
                        f"(default: config.CONFIDENCE_THRESHOLD = {config.CONFIDENCE_THRESHOLD})")
    parser.add_argument("--imgsz", type=int, default=config.IMGSZ,
                        help=f"tamanho de inferencia (default: config.IMGSZ = {config.IMGSZ})")
    parser.add_argument("--device", default="cpu", help="dispositivo (default: cpu)")
    return parser.parse_args(argv)


def ler_gt(caminho_label: Path, largura: int, altura: int) -> list[dict]:
    """Converte um label YOLO (classe xc yc w h normalizados) para xyxy em pixels."""
    if not caminho_label.is_file():
        return []
    gt = []
    for linha in caminho_label.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if len(partes) != 5:
            continue  # linha vazia ou fora do formato bbox
        classe, xc, yc, w, h = int(partes[0]), *map(float, partes[1:])
        gt.append({
            "classe_id": classe,
            "bbox_xyxy": [round((xc - w / 2) * largura, 2), round((yc - h / 2) * altura, 2),
                          round((xc + w / 2) * largura, 2), round((yc + h / 2) * altura, 2)],
        })
    return gt


def desenhar(imagem, predicoes: list[dict], gt: list[dict], nomes: dict[int, str], conf_visual: float):
    """Imagem anotada: GT em verde fino, predicoes >= conf_visual via overlay, cabecalho com contagens."""
    import cv2

    from contador_componentes.app.detector import Deteccao
    from contador_componentes.app.overlay import draw_detections

    base = imagem.copy()
    for g in gt:
        x1, y1, x2, y2 = (int(round(v)) for v in g["bbox_xyxy"])
        cv2.rectangle(base, (x1, y1), (x2, y2), COR_GT, 1)

    aceitas = [p for p in predicoes if p["conf"] >= conf_visual]
    anotada = draw_detections(base, [
        Deteccao(p["classe_id"], nomes.get(p["classe_id"], str(p["classe_id"])), p["conf"],
                 tuple(int(round(v)) for v in p["bbox_xyxy"]))
        for p in aceitas
    ])

    def contar(itens):
        return [sum(1 for i in itens if i["classe_id"] == c) for c in (0, 1)]

    g0, g1 = contar(gt)
    p0, p1 = contar(aceitas)
    texto = f"GT par={g0} por={g1} | pred par={p0} por={p1} (conf>={conf_visual:g})"
    cv2.rectangle(anotada, (0, 0), (anotada.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(anotada, texto, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return anotada


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    imagens = sorted(p for p in args.imagens.glob("*") if p.suffix.lower() in EXTENSOES)
    if not imagens:
        print(f"Erro: nenhuma imagem encontrada em {args.imagens}")
        return 1
    pasta_labels = Path(str(args.imagens).replace("images", "labels"))

    # Import tardio: `--help` nao depende do torch.
    import cv2

    from contador_componentes.app.detector import ModelError, load_model

    try:
        modelo = load_model(args.modelo)
    except ModelError as erro:
        print(f"Erro: {erro}")
        return 1
    nomes = {int(k): str(v) for k, v in modelo.names.items()}

    saida = args.saida / args.nome
    pasta_visual = saida / "visual"
    pasta_visual.mkdir(parents=True, exist_ok=True)

    registros = []
    for caminho in imagens:
        imagem = cv2.imread(str(caminho))
        if imagem is None:
            print(f"Aviso: nao foi possivel ler {caminho.name}, ignorada.")
            continue
        altura, largura = imagem.shape[:2]

        resultado = modelo.predict(imagem, conf=args.conf_bruta, imgsz=args.imgsz,
                                   device=args.device, verbose=False)[0]
        caixas = resultado.boxes
        predicoes = [
            {"classe_id": int(c), "conf": round(float(s), 4),
             "bbox_xyxy": [round(float(v), 2) for v in xyxy]}
            for xyxy, s, c in zip(caixas.xyxy.tolist(), caixas.conf.tolist(), caixas.cls.tolist())
        ] if caixas is not None else []
        predicoes.sort(key=lambda p: p["conf"], reverse=True)

        gt = ler_gt(pasta_labels / f"{caminho.stem}.txt", largura, altura)
        registros.append({"imagem": caminho.name, "largura": largura, "altura": altura,
                          "predicoes": predicoes, "gt": gt})

        cv2.imwrite(str(pasta_visual / caminho.name),
                    desenhar(imagem, predicoes, gt, nomes, args.conf_visual))

    dados = {
        "modelo": str(args.modelo),
        "imgsz": args.imgsz,
        "conf_bruta": args.conf_bruta,
        "conf_visual": args.conf_visual,
        "classes": {str(k): v for k, v in nomes.items()},
        "imagens": registros,
    }
    (saida / "predicoes.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(f"{len(registros)} imagens processadas. Saida: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
