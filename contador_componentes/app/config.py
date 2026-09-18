"""Configuracao central da aplicacao (contador_componentes/app).

Modulo citado no PRD/CLAUDE.md como local unico para valores de configuracao
que hoje estariam espalhados pelo codigo (indices de dispositivo, caminhos,
coordenadas de ROI, etc.). Cada sprint deve acrescentar aqui apenas o que a
etapa atual efetivamente precisa — nao adiantar configuracao de etapas
futuras (ROI, modelo YOLO, MQTT) antes delas existirem.

Webcam definida pelo time (PRD secao 28): modelo GoodVision, capturando em
1080p/30fps. `CAMERA_INDEX` continua generico (indice do dispositivo no
sistema operacional) pois esse valor depende de qual porta/driver o SO
atribui a webcam no computador em uso, nao do modelo escolhido.
"""

from __future__ import annotations

# Indice do dispositivo de camera usado por `cv2.VideoCapture`.
# Padrao: 0 e o indice da primeira webcam disponivel no sistema (a webcam
# GoodVision, unico dispositivo previsto). Ajustar aqui (e somente aqui) se
# o sistema atribuir um indice diferente.
CAMERA_INDEX: int = 1
