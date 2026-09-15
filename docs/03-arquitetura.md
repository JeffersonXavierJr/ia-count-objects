# Arquitetura

## Arquitetura lógica

```text
                   USUÁRIO
                      │
                      ▼
              ┌───────────────┐
              │ HOME ASSISTANT│
              │ componente    │
              │ quantidade    │
              │ vídeo         │
              │ contagem      │
              │ status        │
              └───────┬───────┘
                      │
                     MQTT
                      │
                      ▼
              ┌───────────────┐
              │   APLICAÇÃO   │
              │    PYTHON     │
              └───────┬───────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
      OpenCV                     YOLO
   captura/tratamento      identificação/classificação
          │                        │
          └───────────┬────────────┘
                      ▼
                   CONTAGEM
                      │
                      ▼
                  COMPARAÇÃO
                      │
             detectado x esperado
                      │
                      ▼
                     MQTT
                      │
                      ▼
               HOME ASSISTANT
```

## Arquitetura física + software

```text
Bandeja física
     ↓
Webcam USB
     ↓
Computador do protótipo
     │
     ├── Python
     ├── OpenCV
     ├── Modelo YOLO treinado
     ├── lógica de contagem
     ├── MQTT
     └── stream de vídeo
             │
             ├── MQTT ──────────────→ Home Assistant
             │
             └── HTTP/MJPEG ou RTSP → Home Assistant
```

O Home Assistant poderá rodar no mesmo computador da aplicação.

Ver também o [diagrama Mermaid detalhado](diagrama_arquitetura_contagem_componentes.md).

## Estrutura inicial de código

```text
contador_componentes/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── camera.py
│   ├── detector.py
│   ├── counter.py
│   ├── config.py
│   ├── mqtt_client.py
│   └── video_stream.py
│
├── training/
│   ├── train.py
│   └── dataset.yaml
│
├── models/
│   └── best.pt
│
├── dataset/
│   ├── images/
│   └── labels/
│
├── tests/
├── requirements.txt
└── README.md
```

Esta estrutura ainda não existe no repositório — é o layout planejado quando o
desenvolvimento de código começar (ver [Diretrizes de desenvolvimento](11-diretrizes-de-desenvolvimento.md)).

## Responsabilidades dos módulos

**`camera.py`**
- abrir webcam;
- capturar frames;
- aplicar ROI.

**`detector.py`**
- carregar modelo;
- executar inferência;
- retornar classes, confidence e bounding boxes.

**`counter.py`**
- filtrar classe;
- contar objetos;
- aplicar estabilização;
- comparar com quantidade alvo.

**`mqtt_client.py`**
- receber configurações;
- publicar contagem e status.

**`video_stream.py`**
- fornecer imagem processada ao Home Assistant.

**`main.py`**
- coordenar os módulos.

**`config.py`**
- configuração da aplicação.

`training/` (treino do modelo) e `models/` (modelo treinado) ficam separados de `app/`
porque treinamento e inferência podem rodar em computadores diferentes.
