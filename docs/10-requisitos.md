# Requisitos

## Requisitos funcionais

- **RF-01:** capturar vídeo de webcam USB.
- **RF-02:** processar frames com OpenCV.
- **RF-03:** carregar modelo YOLO treinado.
- **RF-04:** detectar parafusos.
- **RF-05:** detectar porcas.
- **RF-06:** contar objetos da classe selecionada.
- **RF-07:** permitir seleção da classe no Home Assistant.
- **RF-08:** permitir informar quantidade desejada.
- **RF-09:** comparar quantidade detectada e desejada.
- **RF-10:** exibir quantidade detectada no Home Assistant.
- **RF-11:** exibir quantidade desejada.
- **RF-12:** exibir status.
- **RF-13:** exibir câmera.
- **RF-14:** exibir bounding boxes quando viável.
- **RF-15:** transmitir dados via MQTT.
- **RF-16:** permitir reiniciar uma contagem.

## Requisitos não funcionais

### RNF-01 — Ambiente controlado
Manter câmera, altura, bandeja e iluminação estáveis.

### RNF-02 — Baixo custo
Priorizar impressão 3D, webcam comum e software local.

### RNF-03 — Operação local
A inferência deve funcionar localmente, sem depender de API de IA na nuvem.

### RNF-04 — Portabilidade
O modelo treinado deve poder ser transferido para outro computador.

### RNF-05 — Modularidade
Captura, detecção, contagem, comunicação e interface devem permanecer separados.

### RNF-06 — Manutenibilidade
Evitar concentrar toda a aplicação em um único arquivo Python.

## Critérios de aceitação do protótipo

A primeira versão será considerada funcional quando:

1. A webcam capturar toda a bandeja de maneira estável.
2. O usuário conseguir selecionar `Parafuso` ou `Porca`.
3. O usuário conseguir definir uma quantidade alvo.
4. O modelo identificar corretamente os componentes em condições normais.
5. A aplicação contar apenas a classe selecionada.
6. A quantidade aparecer no Home Assistant.
7. O status mudar para `QUANTIDADE ATINGIDA` quando o alvo for alcançado.
8. O vídeo da bandeja puder ser visualizado no Home Assistant.
9. A bandeja permitir descarga manual pelo fundo deslizante.
10. A rampa conduzir os componentes ao recipiente sem perdas significativas.

## Métricas de validação

### IA
- precisão;
- recall;
- falsos positivos;
- falsos negativos;
- erro de contagem.

### Aplicação
- FPS;
- latência;
- uso de CPU;
- uso de RAM;
- uso de GPU, quando aplicável.

### Mecânica
- taxa de descarga completa;
- componentes presos na bandeja;
- componentes presos na rampa;
- necessidade de intervenção manual.
