"""Treina o modelo YOLO de deteccao (parafuso/porca) a partir do dataset.yaml.

Treino e inferencia sao separados (PRD 13.4): este script roda na MAQUINA DE
TREINO, que pode ser diferente do PC do prototipo. Ele so produz os pesos
(`best.pt` / `last.pt`) dentro da pasta do run; copiar o `best.pt` para
`contador_componentes/models/` e um passo manual posterior (TASKS 4.3).

Baseline (PRD 13.3 e secao 21, Etapa 4): YOLO26n com imgsz = 640, Object
Detection (bounding boxes). Nao trocar para YOLO26s antes de analisar o
dataset e os erros do YOLO26n.

Saida: `contador_componentes/training/runs/<name>/` (pesos em `weights/`,
curvas de loss/mAP e `results.csv` gerados pelo proprio ultralytics). Se o
nome ja existir, o ultralytics cria `<name>2`, `<name>3`, ... sem sobrescrever.

Uso (a partir da RAIZ do repositorio, com o venv do projeto ativo):
    python contador_componentes/training/train.py
    python contador_componentes/training/train.py --epochs 50 --device cpu
    python contador_componentes/training/train.py --help

Na primeira execucao o ultralytics baixa os pesos pre-treinados `yolo26n.pt`
para o diretorio atual (ignorados pelo git via `*.pt`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

TRAINING_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = TRAINING_DIR / "dataset.yaml"
DEFAULT_PROJECT = TRAINING_DIR / "runs"

# Modelo base: baseline do PRD. Escalar para yolo26s.pt so apos analise de
# dataset/erros (PRD 13.3) - nunca como primeira reacao a baixa precisao.
DEFAULT_MODEL = "yolo26n.pt"

# Baseline de treino definido no PRD (secao 21, Etapa 4).
DEFAULT_IMGSZ = 640

# Default INICIAL de epocas, apenas ponto de partida configuravel. O valor
# definitivo e decidido e registrado na tarefa 4.2.2, de forma experimental
# (observando as curvas de loss/mAP). 100 e o default do proprio ultralytics
# e e razoavel para um dataset pequeno (~200 imagens de treino) partindo de
# pesos pre-treinados; o early stopping do ultralytics (patience) interrompe
# antes se o mAP de validacao parar de melhorar.
DEFAULT_EPOCHS = 100


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Le os parametros de treino da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Treina o YOLO (deteccao parafuso/porca). Executar a partir da raiz do repositorio.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"pesos/modelo base (default: {DEFAULT_MODEL}, baseline do PRD)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="caminho do dataset.yaml (default: contador_componentes/training/dataset.yaml)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=DEFAULT_IMGSZ,
        help=f"tamanho de imagem de treino (default: {DEFAULT_IMGSZ}, baseline do PRD)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=DEFAULT_EPOCHS,
        help=f"numero de epocas (default inicial: {DEFAULT_EPOCHS}; valor final definido na tarefa 4.2.2)",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="dispositivo: '0' (GPU CUDA), 'cpu', 'mps'... "
        "(default: automatico - GPU se disponivel, senao CPU)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=DEFAULT_PROJECT,
        help="pasta onde os runs sao salvos (default: contador_componentes/training/runs)",
    )
    parser.add_argument(
        "--name",
        default="yolo26n_baseline",
        help="nome do run dentro de --project (default: yolo26n_baseline)",
    )
    return parser.parse_args(argv)


def checar_dataset(data: Path) -> str | None:
    """Confere se o dataset.yaml existe e se seu `path` resolve a partir do cwd.

    O ultralytics resolve o `path` relativo contra o diretorio atual, nao
    contra a pasta do yaml (ver comentario no dataset.yaml). Melhor falhar
    aqui com mensagem clara do que no meio do setup do treino.
    """
    if not data.is_file():
        return f"dataset.yaml nao encontrado: {data}"
    cfg = yaml.safe_load(data.read_text(encoding="utf-8")) or {}
    raiz = Path(cfg.get("path", ""))
    if not raiz.is_absolute() and not raiz.exists():
        return (
            f"o `path` do dataset ({raiz}) nao existe a partir do diretorio atual "
            f"({Path.cwd()}). Execute o treino a partir da raiz do repositorio."
        )
    return None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    erro = checar_dataset(args.data)
    if erro:
        print(f"Erro: {erro}")
        return 1

    # Import tardio: `--help` e a checagem do dataset nao dependem do torch.
    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(args.data),
        imgsz=args.imgsz,
        epochs=args.epochs,
        device=args.device,  # None -> ultralytics escolhe GPU se houver, senao CPU
        # Caminho ABSOLUTO de proposito: com `project` relativo o ultralytics
        # salva em <runs_dir das settings>/detect/<project>, fora do repo.
        project=str(args.project.resolve()),
        name=args.name,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
