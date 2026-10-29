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

from pathlib import Path

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
MODEL_PATH: Path = Path(__file__).resolve().parent.parent / "models" / "best.pt"

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
