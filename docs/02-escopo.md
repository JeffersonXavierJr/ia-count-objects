# Escopo da Primeira Versão (v1)

## Dentro do escopo

- uma webcam;
- uma bandeja fixa;
- iluminação padronizada;
- fundo deslizante manual;
- rampa afunilada;
- recipiente de coleta;
- aplicação Python;
- OpenCV;
- modelo YOLO treinado;
- classes `parafuso` e `porca`;
- contagem em tempo real;
- Home Assistant como interface;
- seleção do componente;
- configuração da quantidade desejada;
- exibição da quantidade detectada;
- status da operação;
- stream de vídeo;
- comunicação MQTT.

## Fora do escopo da primeira versão

- esteira transportadora;
- ESP32;
- Arduino;
- microcontroladores;
- relés;
- motores;
- servo motores;
- acionamento automático do fundo;
- sensores de presença;
- célula de carga;
- QR Code;
- banco de dados;
- histórico de produção;
- dashboard histórico de KPIs;
- controle de estoque;
- integração com ERP;
- aplicativo mobile nativo;
- processamento em nuvem.

## Decisões já tomadas

| Decisão | Estado |
|---|---|
| Bandeja fixa | Definido |
| Fundo deslizante manual | Definido |
| Rampa abaixo da bandeja | Definido |
| Estrutura principalmente impressa em 3D | Definido |
| Webcam superior | Definido |
| Ambiente de iluminação controlada | Definido |
| Python | Definido |
| OpenCV | Definido |
| YOLO | Definido |
| Classes iniciais: parafuso e porca | Definido |
| Home Assistant como interface principal | Definido |
| MQTT para dados | Definido |
| HTTP/MJPEG ou RTSP para vídeo | Em validação |
| Banco de dados | Não necessário na V1 |
| Automação do fundo | Não necessária na V1 |
| Computador de treino pode ser diferente do final | Definido |
| Modelo inicial | YOLO26n como baseline |
| Exportação ONNX | Possível otimização futura |

Itens ainda não decididos (ex.: MJPEG vs RTSP, `.pt` vs `.onnx`) estão listados em
[Pontos em aberto](14-pontos-em-aberto-e-expansoes.md) — não devem ser presumidos.
