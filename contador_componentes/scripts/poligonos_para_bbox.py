"""Converte labels YOLO de poligono (segmentacao) para bounding box (deteccao).

O export do Roboflow veio com a maioria dos objetos anotados como poligono
(`classe x1 y1 x2 y2 ...`), e alguns arquivos misturam poligonos com linhas
bbox (`classe xc yc w h`). O ultralytics rejeita arquivos com essa mistura
("labels mix segment and detection rows") e descarta a imagem no treino.
Como o projeto usa Object Detection (PRD), este script deixa todos os labels
no formato bbox.

Conversao: a caixa e o menor retangulo que contem todos os pontos do
poligono (mesma conta do `segments2boxes` do ultralytics). Coordenadas
continuam normalizadas (0-1). Linhas que ja sao bbox sao mantidas. A classe
nao e alterada.

ATENCAO: sobrescreve os .txt no lugar. Os labels estao versionados no git;
para desfazer: `git checkout -- contador_componentes/dataset/labels`.

Uso (a partir da raiz do repositorio, com o venv do projeto ativo):
    python -m contador_componentes.scripts.poligonos_para_bbox
"""

from __future__ import annotations

import sys
from pathlib import Path

LABELS_DIR = Path(__file__).resolve().parents[1] / "dataset" / "labels"


def linha_para_bbox(linha: str) -> str:
    """Converte uma linha de label para bbox; linhas bbox sao mantidas."""
    v = linha.split()
    if len(v) <= 5:
        return " ".join(v)
    coords = [float(x) for x in v[1:]]
    if len(coords) % 2 != 0:
        raise ValueError(f"poligono com numero impar de coordenadas: {linha!r}")
    xs, ys = coords[0::2], coords[1::2]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return f"{v[0]} {(x0 + x1) / 2:.6f} {(y0 + y1) / 2:.6f} {x1 - x0:.6f} {y1 - y0:.6f}"


def converter_arquivo(arquivo: Path) -> int:
    """Converte um arquivo de label; devolve quantas linhas eram poligono."""
    linhas = [ln for ln in arquivo.read_text().splitlines() if ln.strip()]
    convertidas = sum(1 for ln in linhas if len(ln.split()) > 5)
    novas = [linha_para_bbox(ln) for ln in linhas]
    arquivo.write_text("\n".join(novas) + ("\n" if novas else ""))
    return convertidas


def main() -> int:
    arquivos = sorted(LABELS_DIR.glob("*/*.txt"))
    if not arquivos:
        print(f"Nenhum label encontrado em {LABELS_DIR}")
        return 1
    total = sum(converter_arquivo(a) for a in arquivos)
    print(f"{len(arquivos)} arquivos processados, {total} poligonos convertidos para bbox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
