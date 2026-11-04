"""Ponto de entrada do executavel `ContadorComponentes.exe` (PyInstaller).

Cola de empacotamento apenas (Sprint 11, tarefa 11.1.3): NAO contem logica de
contagem nem de interface. Em modo de desenvolvimento continue usando
`python -m contador_componentes.app.main`.

    ContadorComponentes.exe                 -> aplicacao (app/main.py)
    ContadorComponentes.exe --calibrar-roi  -> scripts/calibrar_roi.py, gravando
                                               a ROI confirmada em config_local.json

Cuidados especificos do modo congelado:
- `sys.executable` e o proprio `.exe`. O ultralytics pode tentar rodar
  `sys.executable -m pip ...` (auto-instalacao de dependencias); isso
  reabriria a aplicacao. Por isso a auto-instalacao e desligada e qualquer
  chamada `-m ...` encerra imediatamente.
- Com `console=False`, `sys.stdout`/`sys.stderr` sao `None`; o log vai para
  `ContadorComponentes.log` ao lado do `.exe` (sobrescrito a cada execucao —
  apenas diagnostico, nao e historico de contagens).
"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path


def _pasta_exe() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _redirecionar_saida_sem_console() -> None:
    """Sem console (exe janela), manda stdout/stderr para um arquivo de log."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        arquivo = open(_pasta_exe() / "ContadorComponentes.log", "w", encoding="utf-8", buffering=1)
    except OSError:
        arquivo = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = arquivo
    if sys.stderr is None:
        sys.stderr = arquivo


def _calibrar_roi() -> int:
    from contador_componentes.app import config
    from contador_componentes.scripts import calibrar_roi

    salvas: list[tuple[int, int, int, int]] = []

    def salvar(roi: tuple[int, int, int, int]) -> None:
        caminho = config.salvar_roi_local(roi)
        salvas.append(tuple(roi))  # type: ignore[arg-type]
        calibrar_roi.logger.info("ROI %r gravada em %s.", tuple(roi), caminho)

    codigo = calibrar_roi.main(ao_confirmar=salvar)

    # Sem console, o operador nao ve o terminal: confirma numa caixa de dialogo.
    import tkinter as tk
    from tkinter import messagebox

    raiz = tk.Tk()
    raiz.withdraw()
    if salvas:
        messagebox.showinfo(
            "Calibracao da ROI",
            f"ROI gravada em:\n{config.CONFIG_LOCAL_PATH}\n\nROI = {salvas[-1]}\n\n"
            "Ela sera usada na proxima vez que o Contador de Componentes for aberto.",
        )
    elif codigo != 0:
        messagebox.showerror(
            "Calibracao da ROI",
            "Nao foi possivel abrir/ler a webcam. Verifique a conexao e o "
            f"camera_index em:\n{config.CONFIG_LOCAL_PATH}",
        )
    else:
        messagebox.showinfo(
            "Calibracao da ROI",
            "Nenhuma ROI foi gravada (pressione P ou Enter para gravar antes de sair).",
        )
    raiz.destroy()
    return codigo


def main() -> int:
    # Chamada do tipo `ContadorComponentes.exe -m pip ...` (ver docstring).
    if len(sys.argv) > 1 and sys.argv[1] in ("-m", "-c"):
        return 1

    multiprocessing.freeze_support()
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")  # nunca rodar pip no PC final
    os.environ.setdefault("YOLO_OFFLINE", "true")  # sem verificacoes de rede
    _redirecionar_saida_sem_console()

    parser = argparse.ArgumentParser(prog="ContadorComponentes")
    parser.add_argument(
        "--calibrar-roi",
        action="store_true",
        help="abre a calibracao da ROI e grava a ROI confirmada em config_local.json",
    )
    args = parser.parse_args()

    if args.calibrar_roi:
        return _calibrar_roi()

    from contador_componentes.app.main import main as main_app

    return main_app()


if __name__ == "__main__":
    sys.exit(main())
