# Comunicação

## Dados — MQTT

Protocolo: **MQTT**.

**Home Assistant → Python**

- componente selecionado;
- quantidade desejada;
- comando de iniciar/resetar contagem, se necessário.

**Python → Home Assistant**

- componente detectado;
- quantidade detectada;
- quantidade esperada;
- status.

### Exemplo conceitual de tópicos

```text
contador/config/componente
contador/config/quantidade

contador/status/detectado
contador/status/esperado
contador/status/estado
```

Os nomes definitivos podem ser ajustados durante o desenvolvimento — os tópicos acima são
apenas um exemplo conceitual do PRD, não uma especificação final.

## Vídeo

A transmissão de vídeo é **separada** dos dados MQTT.

Candidatos:

- HTTP/MJPEG
- RTSP

A escolha final será feita após testes de compatibilidade, estabilidade, latência e consumo
de CPU (ver [Pontos em aberto](14-pontos-em-aberto-e-expansoes.md)).
