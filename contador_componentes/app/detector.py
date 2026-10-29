"""Inferência YOLO (Sprint 6, tarefa 6.2 do TASKS.md).

Responsabilidade única deste módulo (RNF-05/RNF-06): carregar um modelo YOLO
JÁ TREINADO e executar a inferência sobre um frame, devolvendo classe,
confiança e bounding box de cada detecção. O único filtro aplicado aqui é o
limiar de confiança.

NÃO pertencem a este módulo:
- treinamento (fica em `training/train.py`, possivelmente em outro PC);
- filtragem pela classe selecionada, contagem e estabilização temporal
  (`counter.py`, Sprint 7);
- desenho das bounding boxes no frame (pipeline ao vivo, tarefa 6.3).

Caminho do modelo, limiar de confiança e `imgsz` ficam em `app/config.py`.

Uso típico (o modelo é carregado UMA vez e reutilizado a cada frame):

    modelo = detector.load_model()
    deteccoes = detector.run_inference(modelo, frame)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from contador_componentes.app import config

logger = logging.getLogger(__name__)

# Classes da v1 (CLAUDE.md / PRD): exatamente parafuso (0) e porca (1).
# O `counter.py` dependerá desse mapeamento id -> nome, por isso ele é
# verificado ao carregar o modelo.
CLASSES_ESPERADAS: dict[int, str] = {0: "parafuso", 1: "porca"}

# Extensões aceitas: `.pt` (PyTorch, padrão atual) e `.onnx` (exportação
# opcional). A escolha final é ponto em aberto do PRD (seção 29, item 14).
_EXTENSOES_SUPORTADAS = (".pt", ".onnx")


class ModelError(RuntimeError):
    """Erro ao carregar o modelo YOLO ou modelo incompatível com o projeto.

    Serve de base para o futuro estado `MODELO NÃO CARREGADO` da máquina de
    estados do projeto (RB-03), que será implementado em sprint posterior
    (Sprint 7). Este módulo apenas detecta e sinaliza a falha de forma
    clara — não implementa a máquina de estados em si.
    """


@dataclass(frozen=True)
class Deteccao:
    """Uma detecção retornada por `run_inference`.

    Attributes:
        classe_id: id da classe no modelo (0 = parafuso, 1 = porca).
        classe_nome: nome da classe conforme gravado no próprio modelo.
        confianca: confiança da detecção, entre 0.0 e 1.0.
        bbox: retângulo `(x1, y1, x2, y2)` em pixels, nas coordenadas do
            frame passado para `run_inference` (canto superior esquerdo e
            canto inferior direito). Se o frame for um recorte de ROI, as
            coordenadas são relativas ao recorte, não ao frame da câmera.
    """

    classe_id: int
    classe_nome: str
    confianca: float
    bbox: tuple[int, int, int, int]


def load_model(caminho_modelo: str | Path | None = None) -> YOLO:
    """Carrega o modelo YOLO treinado (`.pt` ou `.onnx`).

    Args:
        caminho_modelo: caminho do arquivo do modelo. Quando omitido, usa
            `config.MODEL_PATH`.

    Returns:
        Instância de `ultralytics.YOLO` pronta para `run_inference`.

    Raises:
        ModelError: se o arquivo não existir, tiver extensão não suportada,
            falhar ao carregar, ou se as classes do modelo não forem as da
            v1 (0 = parafuso, 1 = porca).
    """
    caminho = Path(config.MODEL_PATH if caminho_modelo is None else caminho_modelo)

    if not caminho.is_file():
        raise ModelError(
            f"Arquivo do modelo nao encontrado: {caminho}. O modelo treinado "
            "(best.pt) nao e versionado no Git: copie-o do PC de treino para "
            "contador_componentes/models/ ou ajuste config.MODEL_PATH."
        )

    extensao = caminho.suffix.lower()
    if extensao not in _EXTENSOES_SUPORTADAS:
        raise ModelError(
            f"Extensao de modelo nao suportada: {caminho.name!r} "
            f"(esperado: {', '.join(_EXTENSOES_SUPORTADAS)})."
        )

    try:
        # Modelos exportados (.onnx) nao carregam a tarefa de forma confiavel
        # sem dica explicita; o projeto usa apenas deteccao (bounding boxes).
        modelo = YOLO(str(caminho), task="detect" if extensao == ".onnx" else None)
        # Para .onnx, acessar `names` inicializa o backend de inferencia;
        # fica dentro do try para que falhas de carga virem ModelError.
        nomes = dict(modelo.names)
    except Exception as erro:  # noqa: BLE001 - qualquer falha = modelo nao carregado
        raise ModelError(f"Falha ao carregar o modelo {caminho}: {erro}") from erro

    _validar_classes(nomes, caminho)

    logger.info("Modelo carregado: %s (classes=%r).", caminho, nomes)
    return modelo


def _validar_classes(nomes: dict[int, str], caminho: Path) -> None:
    """Garante que o modelo usa o mapeamento de classes da v1.

    Mapeamento diferente é erro (não apenas aviso): o `counter.py` conta pela
    classe selecionada, então um modelo com ids trocados ou de outro projeto
    produziria contagens erradas silenciosamente. Classes extras além de
    0/1 geram apenas aviso, pois não quebram a contagem das classes da v1.
    """
    for classe_id, nome_esperado in CLASSES_ESPERADAS.items():
        if nomes.get(classe_id) != nome_esperado:
            raise ModelError(
                f"Modelo {caminho} incompativel: esperado classe {classe_id} = "
                f"{nome_esperado!r}, encontrado {nomes.get(classe_id)!r} "
                f"(classes do modelo: {nomes!r})."
            )

    extras = {i: n for i, n in nomes.items() if i not in CLASSES_ESPERADAS}
    if extras:
        logger.warning(
            "Modelo %s possui classes alem das previstas na v1: %r. Elas serao "
            "retornadas pela inferencia, mas nao fazem parte do escopo atual.",
            caminho, extras,
        )


def run_inference(
    modelo: YOLO, frame: np.ndarray, conf: float | None = None
) -> list[Deteccao]:
    """Executa a inferência YOLO sobre um frame e retorna as detecções.

    O modelo é recebido explicitamente (em vez de `run_inference(frame)` com
    estado global) para manter o estilo funcional de `camera.py`: quem
    orquestra (`main.py`/pipeline) carrega o modelo uma vez com `load_model`
    e o reutiliza a cada frame.

    Nenhuma filtragem por classe selecionada é feita aqui — isso é papel do
    `counter.py`. O único filtro é o limiar de confiança.

    Args:
        modelo: modelo retornado por `load_model`.
        frame: imagem BGR (formato do OpenCV), tipicamente o recorte da ROI.
        conf: confiança mínima (0.0 a 1.0). Quando omitido, usa
            `config.CONFIDENCE_THRESHOLD`.

    Returns:
        Lista de `Deteccao` (vazia se nada for detectado), em ordem
        decrescente de confiança.

    Raises:
        ValueError: se o frame for `None`/vazio ou `conf` estiver fora de
            [0, 1].
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        raise ValueError("Frame vazio ou None recebido para inferencia.")

    limiar = config.CONFIDENCE_THRESHOLD if conf is None else float(conf)
    if not 0.0 <= limiar <= 1.0:
        raise ValueError(f"Confianca minima invalida: {limiar!r} (esperado 0.0 a 1.0).")

    resultados = modelo.predict(frame, conf=limiar, imgsz=config.IMGSZ, verbose=False)
    if not resultados:
        return []

    resultado = resultados[0]
    caixas = resultado.boxes
    if caixas is None or len(caixas) == 0:
        return []

    nomes = resultado.names
    xyxy = caixas.xyxy.cpu().numpy()
    confiancas = caixas.conf.cpu().numpy()
    classes = caixas.cls.cpu().numpy().astype(int)

    deteccoes = [
        Deteccao(
            classe_id=int(classe_id),
            classe_nome=str(nomes.get(int(classe_id), str(classe_id))),
            confianca=float(confianca),
            bbox=tuple(int(round(v)) for v in caixa),  # type: ignore[arg-type]
        )
        for caixa, confianca, classe_id in zip(xyxy, confiancas, classes)
    ]
    deteccoes.sort(key=lambda d: d.confianca, reverse=True)
    return deteccoes
