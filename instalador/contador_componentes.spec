# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller — ContadorComponentes (Sprint 11, tarefa 11.1.3).

Modo ONE-FOLDER (nao onefile): com o torch, o onefile extrairia ~1 GB no
diretorio temporario a cada execucao e demoraria muito para abrir.

Gerar (normalmente via instalador/build.ps1, a partir da raiz do repositorio):

    instalador\\venv_build\\Scripts\\pyinstaller.exe --noconfirm instalador\\contador_componentes.spec

Variavel de ambiente opcional:
    CONTADOR_CONSOLE=1  -> gera o exe COM console (diagnostico de erros de import).

O que NAO entra no pacote: dataset, training/, treinamento_yolo/, runs/,
yolo26n.pt, tests/, docs/ e os scripts de captura/dataset — o Analysis so
segue imports a partir de `ponto_entrada.py`, e o unico script incluido e
`scripts/calibrar_roi.py` (usado por `--calibrar-roi`).
O modelo (`models/best.pt`) tambem NAO entra no executavel: o build.ps1 o copia
para `dist/ContadorComponentes/models/`, para poder ser trocado sem rebuild.
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

RAIZ = Path(SPECPATH).resolve().parent  # raiz do repositorio
CONSOLE = os.environ.get("CONTADOR_CONSOLE", "0") == "1"

# Arquivos de dados do ultralytics (cfg/*.yaml de modelos/trackers/datasets,
# assets); sao pequenos (~1 MB) e o ultralytics le cfg/default.yaml ao importar.
datas = collect_data_files("ultralytics")

# Metadados de distribuicao: o ultralytics consulta versoes instaladas via
# importlib.metadata (check_requirements/check_version). Sem eles acharia que
# o pacote falta e tentaria instalar (desligado no ponto_entrada.py).
for pacote in (
    "ultralytics", "torch", "torchvision", "numpy", "opencv-python", "pillow",
    "pyyaml", "matplotlib", "psutil", "requests",
):
    try:
        datas += copy_metadata(pacote)
    except Exception:  # noqa: BLE001 - pacote ausente no venv de build
        pass

# torchvision >= 0.29 traz o operador NMS em `_C_stable.pyd`, carregado via
# torch.ops.load_library (nao por import), que o hook padrao nao encontra
# ("Hidden import torchvision._C not found"). Sem ele o predict falha com
# "operator torchvision::nms does not exist". Coleta explicita das .pyd/.dll.
binaries = collect_dynamic_libs("torchvision", search_patterns=["*.pyd", "*.dll"])

hiddenimports = [
    # `scripts/` e um namespace package (sem __init__.py) importado sob demanda.
    "contador_componentes.scripts.calibrar_roi",
]

# Suporte a .onnx so e incluido se o onnxruntime estiver no venv de build
# (o build.ps1 o instala apenas quando existe models/best.onnx). Formato final
# .pt x .onnx: ponto em aberto (PRD 29.14 / TASKS 11.2.3).
try:
    import onnxruntime  # noqa: F401

    hiddenimports += ["onnxruntime", "onnx"]
except ImportError:
    pass

# Modulos pesados que a inferencia nao usa. Lista conservadora: so o que
# comprovadamente nao e importado no caminho da v1 (sem MQTT ainda).
excludes = [
    "tensorboard",
    "torch.utils.tensorboard",
    "IPython",
    "ipykernel",
    "jupyter",
    "jupyter_client",
    "jupyter_core",
    "notebook",
    "pytest",
    "_pytest",
    "pandas",
    # polars (~160 MB): o ultralytics so o importa dentro de funcoes de
    # exportacao para DataFrame e graficos de treino, nunca no predict.
    "polars",
    "tensorflow",
    "keras",
    "triton",
    "paho",
]

a = Analysis(
    [str(RAIZ / "instalador" / "ponto_entrada.py")],
    pathex=[str(RAIZ)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ContadorComponentes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX em DLLs do torch costuma quebrar/atrasar; nao usar
    console=CONSOLE,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ContadorComponentes",
)
