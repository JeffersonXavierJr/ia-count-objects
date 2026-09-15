# Agentes do projeto

Índice dos subagentes especializados do Claude Code criados para o
**Sistema Inteligente de Identificação e Contagem de Componentes**
(ver [`PRD.md`](../../PRD.md) e [`CLAUDE.md`](../../CLAUDE.md), na raiz do
repositório, para o contexto completo).

Cada agente cobre uma função específica do time de desenvolvimento,
alinhada à stack real do projeto (Python, OpenCV, YOLO, MQTT, Home
Assistant). Todos os agentes de implementação técnica usam o **MCP server
do context7** para consultar a documentação atualizada das bibliotecas
antes de escrever código, em vez de confiar apenas na memória do modelo.

O Claude Code pode selecionar automaticamente o agente certo com base na
tarefa (a `description` de cada arquivo existe justamente para isso), ou
você pode invocá-lo explicitamente pedindo pelo nome.

## Agentes disponíveis

| Agente | Quando usar |
|---|---|
| [`opencv-camera-specialist`](opencv-camera-specialist.md) | Captura de webcam, recorte de ROI (área da bandeja), desenho de bounding boxes no frame, ferramenta de captura do dataset. Arquivo principal: `contador_componentes/app/camera.py`. |
| [`yolo-detection-specialist`](yolo-detection-specialist.md) | Dataset (`images/`, `labels/`, split train/val/test), `training/train.py` e `dataset.yaml`, treino do YOLO26n, `contador_componentes/app/detector.py` (inferência), avaliação de métricas e exportação para ONNX. |
| [`python-backend-engineer`](python-backend-engineer.md) | Lógica de contagem e estabilização (`counter.py`), orquestração e máquina de estados (`main.py`, `config.py`), integração MQTT (`mqtt_client.py`) e streaming de vídeo HTTP/MJPEG ou RTSP (`video_stream.py`). |
| [`home-assistant-specialist`](home-assistant-specialist.md) | Entidades MQTT no Home Assistant, dashboard/Lovelace (câmera, seleção de componente, quantidade, status, botão de reset), integração da entidade de câmera (MJPEG/RTSP). |
| [`qa-tester`](qa-tester.md) | Testes automatizados de lógica pura (contagem, estabilização, contrato MQTT), planos de teste manual para partes que dependem de hardware, e checagem do progresso contra os critérios de aceitação (PRD seção 23) e métricas de validação (PRD seção 24). |

## Por que apenas estes cinco

O time de código do projeto (PRD seção 27) é pequeno e as responsabilidades
de visão computacional/backend Python (câmera, dataset, treino, inferência,
contagem, MQTT, streaming) se concentram nas mesmas duas pessoas. Os agentes
acima refletem isso: um por área de conhecimento técnico distinta (OpenCV,
YOLO, backend/MQTT/streaming, Home Assistant) mais QA — sem duplicar agentes
para responsabilidades que, na prática, formam um único módulo coeso do PRD
(ex.: MQTT e streaming de vídeo estão dentro do mesmo agente de backend, não
separados, porque ambos moram nos mesmos módulos `mqtt_client.py`/
`video_stream.py` e na mesma "camada" de orquestração).

Estrutura mecânica/impressão 3D (Augusto/Jefferson no PRD) não gera um
agente porque não produz código.

## Regras que todo agente respeita

Cada agente carrega, no próprio prompt, as restrições vinculantes do PRD
que dizem respeito à sua função (ex.: só duas classes YOLO, sem banco de
dados, descarga manual, Home Assistant como única interface). Mesmo assim,
o [`CLAUDE.md`](../../CLAUDE.md) da raiz continua valendo para qualquer
trabalho no repositório — em caso de dúvida, ele (e o PRD) prevalecem sobre
qualquer agente.

Pontos ainda não decididos pelo projeto (PRD seção 29 — ex.: HTTP/MJPEG vs
RTSP, número de frames de estabilização, `.pt` vs `.onnx`) devem ser
perguntados ao usuário por qualquer agente, nunca inventados.
