"""Importa um export YOLO do Roboflow para o dataset do projeto.

Copia (nao move) imagens e labels de `<export>/{train,valid,test}` para
`contador_componentes/dataset/{images,labels}/{train,val,test}`, mantendo o
split definido no Roboflow (`valid` vira `val`).

Imagens que ja existem no dataset (mesmo nome de arquivo, em qualquer split)
sao PULADAS e continuam no split onde ja estavam. Isso evita duplicatas e,
principalmente, evita que uma imagem ja usada no treino caia no `test`
(vazamento de dados - o test fica reservado para a Sprint 5).

Os labels do Roboflow podem vir como poligono. Depois de importar, rode
`poligonos_para_bbox` para deixar tudo no formato bbox (Object Detection).

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m contador_componentes.scripts.importar_roboflow <pasta_do_export>
    python -m contador_componentes.scripts.importar_roboflow <pasta_do_export> --dry-run
    python -m contador_componentes.scripts.poligonos_para_bbox
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[1] / "dataset"

# split do Roboflow -> split do projeto
SPLITS = {"train": "train", "valid": "val", "test": "test"}
EXTENSOES = {".jpg", ".jpeg", ".png"}


def nomes_existentes() -> set[str]:
    """Nomes de imagem ja presentes em qualquer split do dataset."""
    return {
        f.name
        for split in SPLITS.values()
        for f in (DATASET_DIR / "images" / split).glob("*")
        if f.suffix.lower() in EXTENSOES
    }


def importar(export: Path, dry_run: bool = False) -> Counter:
    existentes = nomes_existentes()
    resumo: Counter = Counter()
    for split_rf, split in SPLITS.items():
        pasta_img = export / split_rf / "images"
        if not pasta_img.is_dir():
            continue
        for img in sorted(pasta_img.iterdir()):
            if img.suffix.lower() not in EXTENSOES:
                continue
            if img.name in existentes:
                resumo["pulada (ja existe)"] += 1
                continue
            label = export / split_rf / "labels" / f"{img.stem}.txt"
            if not label.is_file():
                resumo["pulada (sem label)"] += 1
                print(f"Aviso: sem label, ignorada: {img}")
                continue
            if not dry_run:
                shutil.copy2(img, DATASET_DIR / "images" / split / img.name)
                shutil.copy2(label, DATASET_DIR / "labels" / split / label.name)
            resumo[f"importada -> {split}"] += 1
    return resumo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path, help="pasta raiz do export do Roboflow")
    parser.add_argument("--dry-run", action="store_true", help="so mostra o que seria feito")
    args = parser.parse_args(argv)

    if not args.export.is_dir():
        print(f"Erro: pasta nao encontrada: {args.export}")
        return 1
    resumo = importar(args.export, args.dry_run)
    for chave, n in sorted(resumo.items()):
        print(f"{chave}: {n}")
    if not args.dry_run and any(k.startswith("importada") for k in resumo):
        # caches antigos do ultralytics; ele recria no proximo treino
        for cache in (DATASET_DIR / "labels").glob("*.cache"):
            cache.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
