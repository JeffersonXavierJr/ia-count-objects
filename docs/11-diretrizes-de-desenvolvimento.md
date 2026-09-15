# Diretrizes de Desenvolvimento

Padrões que qualquer pessoa (ou IA) trabalhando neste repositório deve seguir. Baseado nas
instruções vinculantes da seção 0 do [`PRD.md`](../PRD.md).

## Princípio geral

> Primeiro fazer funcionar corretamente em uma etapa simples; depois integrar.

Não adicionar complexidade sem necessidade funcional.

## O que não presumir na v1

- esteira transportadora;
- ESP32, microcontrolador, motor, servo ou relé/atuador;
- banco de dados ou histórico de contagens;
- abertura automática do fundo da bandeja — a descarga é **manual**;
- interface própria além do Home Assistant;
- outros componentes além de `parafuso` e `porca`.

Ver detalhes em [Escopo](02-escopo.md).

## Modularidade (RNF-05, RNF-06)

Captura, detecção, contagem, comunicação e interface devem permanecer em módulos separados —
evitar concentrar tudo em um único arquivo Python. Ver [Arquitetura](03-arquitetura.md) para o
layout de módulos planejado.

## Treinamento vs. inferência

O computador usado para treinar o modelo pode ser diferente do computador de produção. Código
de treinamento (`training/`) e código de inferência (`app/`, `models/`) são responsabilidades
separadas.

## Construção incremental

O protótipo deve ser desenvolvido de maneira incremental, validando cada etapa antes da
próxima. Ordem recomendada:

```text
Câmera
  ↓
Dataset
  ↓
YOLO
  ↓
Contagem
  ↓
Estabilização
  ↓
MQTT
  ↓
Home Assistant
  ↓
Streaming
  ↓
Integração física completa
```

### Etapas detalhadas

1. **Webcam** — `Webcam → Python → imagem na tela`.
2. **Captura do dataset** — ferramenta simples para salvar frames.
3. **Dataset e anotação** — capturar, anotar e dividir `train/val/test`.
4. **Primeiro treinamento** — baseline `YOLO26n`, `imgsz = 640`.
5. **Validação em fotografias** — testar imagens nunca vistas pelo modelo.
6. **Webcam + IA** — `Webcam → ROI → YOLO → bounding boxes`.
7. **Contagem** — `detections → filtrar classe → contar`.
8. **Estabilização** — reduzir oscilações entre frames.
9. **MQTT + Home Assistant** — integrar somente após a IA funcionar localmente.
10. **Stream de vídeo** — integrar HTTP/MJPEG ou RTSP.
11. **Computador final** — testar desempenho no equipamento real; se necessário, reduzir
    resolução, exportar para ONNX, ajustar FPS, otimizar inferência.

MQTT/Home Assistant só entram **depois** que o pipeline de detecção já funciona sozinho.

## Primeiro passo prático de código

O primeiro programa deve apenas abrir a webcam, mostrar a imagem e permitir encerrar com uma
tecla. Nenhuma IA é necessária nessa etapa.

```python
import cv2

camera = cv2.VideoCapture(0)

while True:
    ok, frame = camera.read()

    if not ok:
        break

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
```

## Ao ficar em dúvida

Pontos ainda não decididos no PRD (ex.: modelo da webcam, dimensões da bandeja, MJPEG vs
RTSP) devem ser perguntados ou sinalizados — nunca inventados. Ver
[Pontos em aberto](14-pontos-em-aberto-e-expansoes.md).
