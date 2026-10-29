"""Teste manual da lógica de contagem: detector -> counter (Sprint 7, tarefa 7.4).

Roda `detector.run_inference` sobre imagem(ns) ou sobre a webcam e passa as
detecções pelo `counter` (filtro pela classe selecionada -> contagem ->
estado), imprimindo:

- contagem bruta por classe (tudo o que o modelo viu);
- contagem da classe selecionada (o que a interface exibiria, RB-01);
- o `Estado` resultante (RB-02/RB-03).

SEM estabilização temporal (Sprint 8): no modo webcam, o estado é o do frame
atual e pode oscilar entre frames.

Uso (a partir da raiz do repositório, com o venv do projeto ativo):

    # imagens (uma ou várias, na ordem dada — útil para simular peças sendo
    # colocadas na bandeja)
    python -m contador_componentes.scripts.testar_contagem IMG1 [IMG2 ...] \
        --classe parafuso --alvo 12

    # webcam ao vivo (aplica a ROI de config.py); q/Esc encerra
    python -m contador_componentes.scripts.testar_contagem --webcam \
        --classe porca --alvo 4

    # sem --classe/--alvo -> estado AGUARDANDO CONFIGURAÇÃO
    # --modelo CAMINHO  usa outro modelo (padrão: config.MODEL_PATH)
    # --conf 0.5        limiar de confiança (padrão: config.CONFIDENCE_THRESHOLD)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from contador_componentes.app import counter, detector
from contador_componentes.app.counter import ConfiguracaoContagem, Estado


def _processar(modelo, frame, cfg: ConfiguracaoContagem, conf: float | None):
    """detector -> counter para um frame. Retorna (por_classe, detectado, estado, deteccoes)."""
    deteccoes = detector.run_inference(modelo, frame, conf=conf)
    por_classe = {
        nome: counter.count_objects(counter.filter_by_class(deteccoes, cid))
        for cid, nome in counter.CLASSES.items()
    }
    if cfg.classe is None:
        detectado = 0
    else:
        detectado = counter.count_objects(counter.filter_by_class(deteccoes, cfg.classe))
    estado = counter.determinar_estado(cfg, detectado)
    return por_classe, detectado, estado, deteccoes


def _linha(rotulo: str, por_classe: dict, detectado: int, estado: Estado, cfg) -> str:
    brutas = ", ".join(f"{n}={c}" for n, c in por_classe.items())
    sel = cfg.classe if cfg.classe is not None else "-"
    alvo = cfg.quantidade if cfg.quantidade is not None else "-"
    return (f"{rotulo} | bruto: {brutas} | classe={sel} alvo={alvo} "
            f"detectado={detectado} | estado={estado.value}")


def _modo_imagens(modelo, caminhos: list[Path], cfg, conf) -> int:
    codigo = 0
    for caminho in caminhos:
        frame = cv2.imread(str(caminho))
        if frame is None:
            print(f"{caminho.name} | ERRO: nao foi possivel ler a imagem", file=sys.stderr)
            codigo = 1
            continue
        por_classe, detectado, estado, _ = _processar(modelo, frame, cfg, conf)
        print(_linha(caminho.name, por_classe, detectado, estado, cfg))
    return codigo


def _modo_webcam(modelo, cfg, conf) -> int:
    from contador_componentes.app import camera
    from contador_componentes.app.overlay import draw_detections

    cam = None
    try:
        cam = camera.open_camera()
        ultimo = None
        while True:
            roi = camera.apply_roi(camera.read_frame(cam))
            por_classe, detectado, estado, deteccoes = _processar(modelo, roi, cfg, conf)
            linha = _linha("webcam", por_classe, detectado, estado, cfg)
            if linha != ultimo:  # imprime só quando algo muda
                print(linha)
                ultimo = linha
            anotado = draw_detections(roi.copy(), deteccoes)
            cv2.putText(anotado, f"{detectado} {estado.value}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            cv2.imshow("Teste de contagem", anotado)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    except Exception as erro:  # noqa: BLE001 - mapeia para estado de erro
        estado = counter.estado_de_erro(erro)
        if estado is None:
            raise
        print(f"estado={estado.value} ({erro})", file=sys.stderr)
        return 1
    finally:
        camera.release_camera(cam)
        cv2.destroyAllWindows()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("imagens", nargs="*", type=Path, help="imagem(ns) a analisar")
    parser.add_argument("--webcam", action="store_true", help="usar a webcam (com ROI)")
    parser.add_argument("--classe", help="classe selecionada: parafuso ou porca")
    parser.add_argument("--alvo", type=int, help="quantidade alvo (inteiro > 0)")
    parser.add_argument("--modelo", type=Path, help="caminho do modelo (.pt/.onnx)")
    parser.add_argument("--conf", type=float, help="limiar de confianca (0 a 1)")
    args = parser.parse_args(argv)

    if args.webcam == bool(args.imagens):
        parser.error("informe imagem(ns) OU --webcam")

    try:
        cfg = ConfiguracaoContagem(args.classe, args.alvo)
    except ValueError as erro:
        parser.error(str(erro))

    try:
        modelo = detector.load_model(args.modelo)
    except detector.ModelError as erro:
        print(f"estado={counter.estado_de_erro(erro).value} ({erro})", file=sys.stderr)
        return 1

    if args.webcam:
        return _modo_webcam(modelo, cfg, args.conf)
    return _modo_imagens(modelo, args.imagens, cfg, args.conf)


if __name__ == "__main__":
    sys.exit(main())
