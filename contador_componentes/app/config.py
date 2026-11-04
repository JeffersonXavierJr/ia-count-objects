"""Configuracao central da aplicacao (contador_componentes/app).

Modulo citado no PRD/CLAUDE.md como local unico para valores de configuracao
que hoje estariam espalhados pelo codigo (indices de dispositivo, caminhos,
coordenadas de ROI, etc.). Cada sprint deve acrescentar aqui apenas o que a
etapa atual efetivamente precisa — nao adiantar configuracao de etapas
futuras (ex.: MQTT) antes delas existirem. A ROI foi acrescentada na
Sprint 6 (tarefa 6.1.4 do TASKS.md); caminho do modelo, limiar de confianca e
imgsz da inferencia YOLO, tambem na Sprint 6 (tarefa 6.2.3).

Webcam definida pelo time (PRD secao 28): modelo GoodVision, capturando em
1080p/30fps. `CAMERA_INDEX` continua generico (indice do dispositivo no
sistema operacional) pois esse valor depende de qual porta/driver o SO
atribui a webcam no computador em uso, nao do modelo escolhido.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pasta base da aplicacao (empacotamento, Sprint 11 — tarefa 11.1.3)
# ---------------------------------------------------------------------------

# Em desenvolvimento: a pasta do pacote `contador_componentes/` (resolvida a
# partir deste arquivo, e NAO do diretorio de trabalho atual).
# No executavel gerado pelo PyInstaller (`sys.frozen`): a pasta onde esta o
# `ContadorComponentes.exe`, para que o modelo (`models/`) e o
# `config_local.json` fiquem FORA do executavel e possam ser trocados/editados
# no PC final sem gerar o executavel de novo (ver instalador/LEIAME_INSTALACAO.md).
if getattr(sys, "frozen", False):
    PASTA_APLICACAO: Path = Path(sys.executable).resolve().parent
else:
    PASTA_APLICACAO = Path(__file__).resolve().parent.parent

# Indice do dispositivo de camera usado por `cv2.VideoCapture`.
# Padrao: 0 e o indice da primeira webcam disponivel no sistema (a webcam
# GoodVision, unico dispositivo previsto). Ajustar aqui (e somente aqui) se
# o sistema atribuir um indice diferente.
CAMERA_INDEX: int = 0

# Regiao de interesse (ROI) = area util da bandeja, no formato
# (x, y, largura, altura), em pixels do frame CAPTURADO pela camera (mesma
# resolucao entregue por `camera.read_frame`, nao a da janela de exibicao).
#
# Valor padrao `None` = ROI desativada (o frame inteiro e usado). As
# coordenadas reais da bandeja AINDA NAO FORAM DEFINIDAS: dependem da posicao
# fisica definitiva da camera (ponto em aberto do PRD, secao 29; tarefa 6.1.1
# do TASKS.md). Para preencher, rode a ferramenta de calibracao:
#     python -m contador_componentes.scripts.calibrar_roi
# ajuste o retangulo sobre a bandeja e cole aqui a linha `ROI = (...)` que
# ela imprime. Se a camera, sua altura ou a resolucao de captura mudarem,
# a ROI precisa ser recalibrada.
# No PC final (executavel), CAMERA_INDEX e ROI podem ser sobrescritos sem
# rebuild pelo `config_local.json` (ver final deste arquivo).
ROI: tuple[int, int, int, int] | None = None

# ---------------------------------------------------------------------------
# Modelo YOLO (Sprint 6, tarefa 6.2.3 do TASKS.md)
# ---------------------------------------------------------------------------

# Caminho do modelo treinado usado na inferencia (`detector.load_model`).
# Resolvido a partir da localizacao deste arquivo (pacote
# `contador_componentes`), e NAO do diretorio de trabalho atual — assim o
# caminho funciona independentemente de onde a aplicacao e iniciada.
# O arquivo e gerado por `training/train.py` (possivelmente em outro PC) e
# copiado para `contador_componentes/models/` (fora do Git, ver .gitignore).
#
# PONTO EM ABERTO (PRD secao 29, item 14): formato final de deployment
# `.pt` vs `.onnx` ainda NAO foi decidido. `detector.load_model` aceita os
# dois; exportar para ONNX so deve ser feito se testes no PC final mostrarem
# necessidade real de desempenho (Sprint 14). Ate la, usa-se o `best.pt`.
#
# Empacotamento (11.1.3): a pasta e `PASTA_APLICACAO / "models"` — em dev
# continua sendo `contador_componentes/models/`; no executavel, a pasta
# `models/` ao lado do `.exe`. Se `best.pt` nao existir mas houver
# `best.onnx`, usa-se o `.onnx` (apenas fallback; NAO e a decisao do formato).
_PASTA_MODELOS: Path = PASTA_APLICACAO / "models"
MODEL_PATH: Path = _PASTA_MODELOS / "best.pt"
if not MODEL_PATH.is_file() and (_PASTA_MODELOS / "best.onnx").is_file():
    MODEL_PATH = _PASTA_MODELOS / "best.onnx"

# Confianca minima para uma deteccao ser aceita (0.0 a 1.0).
# VALOR INICIAL, a ser ajustado: 0.5 e apenas um ponto de partida, NAO um
# valor decidido. Deve ser calibrado com base na validacao em fotos nunca
# vistas pelo modelo e nos testes ao vivo (falsos positivos x falsos
# negativos).
CONFIDENCE_THRESHOLD: float = 0.5

# Tamanho de imagem (lado, em pixels) usado na inferencia. Mantido igual ao
# baseline de treino (PRD secao 21, Etapa 4: imgsz=640); se o modelo for
# retreinado com outro valor, atualizar aqui tambem.
IMGSZ: int = 640

# ---------------------------------------------------------------------------
# Estabilizacao da contagem (Sprint 8, tarefa 8.1.3 do TASKS.md)
# ---------------------------------------------------------------------------

# Numero N de frames CONSECUTIVOS com o mesmo resultado (alvo atingido ou
# alvo excedido) exigido antes de `counter.EstabilizadorContagem` reportar
# `QUANTIDADE ATINGIDA` / `QUANTIDADE EXCEDIDA` (PRD secao 16). Deve ser
# inteiro >= 1; N=1 equivale a nao estabilizar.
#
# VALOR INICIAL, a ser validado: 5 e o baseline sugerido pelo PRD (secao 16).
# PONTO EM ABERTO (PRD secao 29, itens 8/9; tarefa 8.2 do TASKS.md): o valor
# definitivo deve ser decidido experimentalmente, observando se ainda ha
# oscilacao perceptivel de status. Note que o tempo efetivo de espera depende
# do FPS real do pipeline (ex.: 5 frames a ~10 FPS = ~0,5 s).
FRAMES_ESTABILIZACAO: int = 5

# ---------------------------------------------------------------------------
# Orquestracao / interface local (Sprint 9, tarefa 9.2 do TASKS.md)
# ---------------------------------------------------------------------------

# Intervalo, em segundos, entre tentativas de reabrir a webcam depois de uma
# falha ao abrir/ler (estado `ERRO DE CAMERA`). Tambem e o intervalo com que
# o estado de erro e republicado para a interface enquanto a falha persiste.
# VALOR INICIAL: 2 s e um compromisso entre reagir rapido a reconexao do cabo
# USB e nao ficar martelando o driver; ajustar nos testes manuais (9.3.4).
INTERVALO_RECONEXAO_CAMERA_S: float = 2.0

# Periodo, em milissegundos, com que a thread do Tkinter consulta o resultado
# mais recente do pipeline (`root.after`). ~30 ms (~33 atualizacoes/s) basta
# para acompanhar a webcam (30 fps) sem ocupar a thread da interface; o FPS
# real e limitado pela inferencia, nao por este valor.
INTERVALO_ATUALIZACAO_INTERFACE_MS: int = 30

# Tempo maximo, em segundos, que o fechamento da janela espera a thread do
# pipeline terminar (join) antes de liberar a camera e destruir a janela.
# Deve cobrir uma inferencia em andamento no PC mais lento previsto
# (FPS da tarefa 6.4 ainda nao medido).
TIMEOUT_ENCERRAMENTO_WORKER_S: float = 3.0

# ---------------------------------------------------------------------------
# Interface local (Sprint 9, tarefa 9.1.3 do TASKS.md)
# ---------------------------------------------------------------------------

# Quantidade desejada maxima aceita pelo campo da interface (`interface.py`).
# `None` = sem limite (aceita qualquer inteiro positivo).
#
# PONTO EM ABERTO (PRD secao 29, item 6): a quantidade maxima de componentes
# suportada pela bandeja/camera AINDA NAO FOI DEFINIDA. Nao inventar um
# valor: preencher aqui somente quando o time decidir.
QUANTIDADE_MAXIMA: int | None = None

# ---------------------------------------------------------------------------
# Configuracao local editavel no PC final (Sprint 11 — tarefa 11.1.3)
# ---------------------------------------------------------------------------

# Arquivo OPCIONAL, ao lado do executavel (em dev: `contador_componentes/`),
# que sobrescreve SOMENTE os valores que dependem do PC/montagem final e
# precisam mudar sem gerar o executavel de novo:
#
#     {"camera_index": 0, "roi": [x, y, largura, altura]}   (roi pode ser null)
#
# Chaves ausentes mantem os padroes definidos acima. Arquivo inexistente =
# padroes. Arquivo/valor invalido = aviso no log e padrao mantido (a
# aplicacao nao deve deixar de abrir por causa dele). A ROI pode ser gravada
# aqui pela calibracao (`ContadorComponentes.exe --calibrar-roi`). Nao e
# historico nem banco de dados: guarda apenas a configuracao corrente.
CONFIG_LOCAL_PATH: Path = PASTA_APLICACAO / "config_local.json"


def _validar_camera_index(valor: Any) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
        raise ValueError(f"camera_index deve ser inteiro >= 0, recebido {valor!r}")
    return valor


def _validar_roi(valor: Any) -> tuple[int, int, int, int] | None:
    if valor is None:
        return None
    if (
        not isinstance(valor, (list, tuple))
        or len(valor) != 4
        or any(isinstance(v, bool) or not isinstance(v, int) for v in valor)
    ):
        raise ValueError(f"roi deve ser null ou [x, y, largura, altura] inteiros, recebido {valor!r}")
    x, y, largura, altura = valor
    if x < 0 or y < 0 or largura <= 0 or altura <= 0:
        raise ValueError(f"roi com valores invalidos {valor!r} (x,y >= 0; largura,altura > 0)")
    return (x, y, largura, altura)


_VALIDADORES_LOCAIS = {"camera_index": _validar_camera_index, "roi": _validar_roi}


def _ler_config_local(caminho: Path) -> dict[str, Any]:
    """Le o JSON local; devolve {} se nao existir ou estiver ilegivel."""
    if not caminho.is_file():
        return {}
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        logger.warning("Ignorando %s (ilegivel: %s). Usando os padroes.", caminho, erro)
        return {}
    if not isinstance(dados, dict):
        logger.warning("Ignorando %s (esperado um objeto JSON). Usando os padroes.", caminho)
        return {}
    return dados


def carregar_config_local(caminho: Path | None = None) -> dict[str, Any]:
    """Devolve os valores VALIDOS do arquivo local (`camera_index`, `roi`)."""
    caminho = CONFIG_LOCAL_PATH if caminho is None else caminho
    valores: dict[str, Any] = {}
    for chave, bruto in _ler_config_local(caminho).items():
        validador = _VALIDADORES_LOCAIS.get(chave)
        if validador is None:
            logger.warning("Chave desconhecida %r em %s ignorada.", chave, caminho)
            continue
        try:
            valores[chave] = validador(bruto)
        except ValueError as erro:
            logger.warning("%s: %s. Usando o padrao.", caminho, erro)
    return valores


def salvar_roi_local(roi: tuple[int, int, int, int] | None, caminho: Path | None = None) -> Path:
    """Grava a ROI no arquivo local, preservando as demais chaves.

    Usado pela calibracao no PC final. Atualiza tambem `ROI` deste modulo.

    Raises:
        ValueError: ROI invalida.
        OSError: falha ao gravar o arquivo.
    """
    global ROI
    caminho = CONFIG_LOCAL_PATH if caminho is None else caminho
    roi = _validar_roi(None if roi is None else [int(v) for v in roi])
    dados = _ler_config_local(caminho)
    dados["roi"] = None if roi is None else list(roi)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, indent=2) + "\n", encoding="utf-8")
    temporario.replace(caminho)
    ROI = roi
    return caminho


_valores_locais = carregar_config_local()
CAMERA_INDEX = _valores_locais.get("camera_index", CAMERA_INDEX)
ROI = _valores_locais.get("roi", ROI)
del _valores_locais
