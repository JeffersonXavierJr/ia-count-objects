# PRD — Sistema Inteligente de Identificação e Contagem de Componentes

**Versão:** 1.0  
**Data de referência:** 15/09/2026  
**Status:** Planejamento concluído / início do desenvolvimento prático  
**Idioma:** Português (Brasil)  
**Tipo:** Product Requirements Document (PRD) / documento de contexto para continuidade por outras IAs

---

## 0. Instruções para qualquer IA que receber este documento

Este arquivo deve ser tratado como a **fonte de verdade atual do projeto**.

Ao sugerir arquitetura, código, materiais ou próximos passos:

1. Não presumir o uso de esteira transportadora.
2. Não presumir ESP32, microcontrolador, motor, servo, relé ou atuadores.
3. Não presumir banco de dados ou histórico de contagens na primeira versão.
4. Não automatizar a abertura do fundo da bandeja na primeira versão.
5. A descarga dos componentes é **manual**.
6. O Home Assistant deve ser, preferencialmente, a **única interface do usuário**.
7. A comunicação lógica entre o processamento e o Home Assistant será baseada em **MQTT**.
8. A transmissão de vídeo para o Home Assistant deverá usar **HTTP/MJPEG ou RTSP**, a definir durante os testes.
9. O modelo de IA inicial deve reconhecer apenas:
   - parafuso;
   - porca.
10. Outros componentes, como arruelas, são expansão futura.
11. O computador usado para **treinar a IA pode ser diferente** do computador que executará o aplicativo final.
12. O protótipo deve ser desenvolvido de maneira incremental, validando cada etapa antes da próxima.
13. A estrutura física será projetada prioritariamente para **impressão 3D**.
14. Não adicionar complexidade sem necessidade funcional.
15. Em caso de conflito com sugestões anteriores, **este documento prevalece**.

---

## 1. Resumo executivo

O projeto consiste em uma **estação inteligente para identificação e contagem automática de pequenos componentes**, inicialmente parafusos e porcas.

Os componentes são colocados manualmente por um usuário em uma **bandeja fixa**, posicionada abaixo de uma câmera.

A câmera observa toda a área útil da bandeja. Um computador executa um software em Python utilizando OpenCV e um modelo YOLO previamente treinado para:

1. capturar a imagem;
2. identificar os componentes;
3. classificar cada item;
4. contar os objetos da classe selecionada;
5. comparar a quantidade detectada com a quantidade requisitada.

O usuário configura pelo Home Assistant:

- qual componente deseja contar;
- qual quantidade deseja atingir.

Quando a quantidade desejada é alcançada, o Home Assistant informa que a contagem foi concluída.

A bandeja possui um **fundo deslizante manual**. Após a confirmação da quantidade, o usuário puxa esse fundo e os componentes caem por gravidade em uma **rampa afunilada**, que os direciona para um recipiente.

A primeira versão não possui automação mecânica da descarga.

---

## 2. Problema

A contagem manual de pequenos componentes como parafusos e porcas é uma atividade repetitiva, demorada e sujeita a erros humanos.

Em processos de montagem, separação de kits ou preparação de materiais, uma contagem incorreta pode causar:

- kits incompletos;
- retrabalho;
- necessidade de nova conferência;
- desperdício de tempo;
- erros de abastecimento;
- redução da confiabilidade do processo.

O projeto propõe automatizar a identificação e a contagem usando visão computacional, mantendo a operação física simples e de baixo custo.

---

## 3. Objetivo geral

Desenvolver um sistema inteligente capaz de identificar e contar automaticamente componentes por visão computacional, permitindo ao usuário selecionar o tipo de componente e a quantidade desejada através do Home Assistant.

---

## 4. Objetivos específicos

- Capturar imagens de uma bandeja de inspeção através de uma webcam.
- Manter câmera, iluminação e bandeja em posições padronizadas.
- Utilizar Python como linguagem principal.
- Utilizar OpenCV para aquisição e manipulação das imagens.
- Treinar um modelo YOLO para identificar parafusos e porcas.
- Realizar automaticamente a contagem dos componentes detectados.
- Permitir ao usuário selecionar o tipo de componente.
- Permitir ao usuário definir a quantidade desejada.
- Comparar a quantidade identificada com a quantidade solicitada.
- Informar em tempo real o progresso da contagem.
- Informar quando a quantidade desejada for atingida.
- Exibir o vídeo da bandeja no Home Assistant.
- Exibir as marcações dos objetos identificados sobre o vídeo ou imagem.
- Utilizar MQTT para troca de informações entre os serviços.
- Utilizar HTTP/MJPEG ou RTSP para disponibilização do vídeo.
- Criar uma bandeja com fundo deslizante para descarga manual.
- Criar uma rampa afunilada para direcionar os componentes ao recipiente.
- Construir a maior parte da estrutura por impressão 3D.
- Permitir expansão futura para outros componentes.

---

## 5. Escopo da primeira versão

### 5.1 Dentro do escopo

A primeira versão deverá possuir:

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

### 5.2 Fora do escopo da primeira versão

Não fazem parte da primeira versão:

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

---

## 6. Funcionamento físico

### 6.1 Estrutura

A estação será composta por:

1. suporte estrutural;
2. câmera posicionada acima;
3. bandeja fixa;
4. iluminação uniforme;
5. fundo deslizante;
6. rampa afunilada;
7. recipiente de coleta.

Representação conceitual:

```text
                  CÂMERA
                     ↓
             ┌───────────────┐
             │    BANDEJA    │
             │  🔩  🔩  ⬡    │
             │               │
             ├───────────────┤ ← fundo deslizante
             └───────┬───────┘
                     ↓
                componentes
                   caem
                     ↓
                ┌────────┐
                │ RAMPA  │
                │ \    / │
                │  \  /  │
                │   \/   │
                └────┬───┘
                     ↓
                RECIPIENTE
```

### 6.2 Bandeja

A bandeja permanecerá fixa durante toda a contagem.

Requisitos:

- área interna totalmente visível pela câmera;
- bordas suficientes para impedir que os componentes escapem;
- superfície com bom contraste em relação aos objetos;
- geometria adequada para impressão 3D;
- fundo independente da estrutura lateral.

### 6.3 Fundo deslizante

O fundo será uma placa que desliza horizontalmente.

**Fechado:** sustenta os componentes durante a inspeção.  
**Aberto:** ao ser puxado manualmente, libera os componentes para a rampa.

Requisitos:

- movimentação suave;
- pequena folga mecânica;
- puxador acessível;
- trilhos/guias;
- abertura suficiente para descarregar todos os componentes.

### 6.4 Rampa

A rampa ficará imediatamente abaixo da bandeja.

Funções:

- receber os componentes;
- impedir espalhamento;
- conduzir os objetos por gravidade;
- afunilar a saída;
- direcionar os componentes ao recipiente.

---

## 7. Fluxo operacional

```text
INÍCIO
  ↓
Usuário acessa Home Assistant
  ↓
Seleciona o tipo de componente
  ↓
Define a quantidade desejada
  ↓
Usuário adiciona componentes à bandeja
  ↓
Câmera captura continuamente
  ↓
IA identifica os objetos
  ↓
Sistema conta a classe selecionada
  ↓
Quantidade detectada < quantidade desejada?
  ├── SIM → continua contando
  └── NÃO
        ↓
Home Assistant informa
"QUANTIDADE ATINGIDA"
        ↓
Usuário puxa o fundo deslizante
        ↓
Componentes caem na rampa
        ↓
Rampa direciona ao recipiente
        ↓
Usuário fecha novamente o fundo
        ↓
Nova contagem pode ser iniciada
```

---

## 8. Cenário de uso de referência

```text
Componente selecionado: Parafuso
Quantidade desejada: 20

Detectado: 14
Status: CONTANDO

Detectado: 17
Status: CONTANDO

Detectado: 19
Status: CONTANDO

Detectado: 20
Status: QUANTIDADE ATINGIDA
```

Após isso, o usuário descarrega manualmente os componentes.

---

## 9. Arquitetura lógica

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

---

## 10. Arquitetura física + software

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

---

## 11. Comunicação

### 11.1 Dados

Protocolo:

```text
MQTT
```

**Home Assistant → Python**

- componente selecionado;
- quantidade desejada;
- comando de iniciar/resetar contagem, se necessário.

**Python → Home Assistant**

- componente detectado;
- quantidade detectada;
- quantidade esperada;
- status.

Exemplo conceitual de tópicos:

```text
contador/config/componente
contador/config/quantidade

contador/status/detectado
contador/status/esperado
contador/status/estado
```

Os nomes definitivos podem ser ajustados durante o desenvolvimento.

### 11.2 Vídeo

A transmissão de vídeo será separada dos dados MQTT.

Candidatos:

```text
HTTP/MJPEG
```

ou

```text
RTSP
```

A escolha final será feita após testes de compatibilidade, estabilidade, latência e consumo de CPU.

---

## 12. Interface do usuário

O Home Assistant será preferencialmente a única interface do operador.

O dashboard deverá permitir:

### Configuração

- selecionar `Parafuso` ou `Porca`;
- informar quantidade desejada;
- reiniciar a contagem.

### Monitoramento

- visualizar câmera;
- visualizar bounding boxes;
- visualizar quantidade atual;
- visualizar quantidade desejada;
- visualizar status.

Exemplo:

```text
┌──────────────────────────────────┐
│      CONTAGEM DE COMPONENTES     │
├──────────────────────────────────┤
│                                  │
│        [ CÂMERA AO VIVO ]        │
│                                  │
│    □parafuso     □parafuso       │
│         □parafuso                │
│                                  │
├──────────────────────────────────┤
│ Componente:        Parafuso      │
│ Quantidade alvo:   20            │
│ Detectado:         17            │
│ Status: CONTANDO                 │
└──────────────────────────────────┘
```

Quando atingir o valor:

```text
Detectado: 20
Status: QUANTIDADE ATINGIDA
```

---

## 13. Inteligência Artificial

### 13.1 Tipo de problema

A primeira versão deve utilizar **Object Detection**.

Não iniciar com segmentação, salvo se os testes mostrarem que bounding boxes são insuficientes.

### 13.2 Classes iniciais

```text
0 = parafuso
1 = porca
```

### 13.3 Modelo inicial recomendado

Baseline atual:

```text
YOLO26n
```

Motivos:

- leve;
- adequado para inferência em computadores modestos;
- apenas duas classes;
- ambiente controlado;
- câmera fixa;
- iluminação padronizada.

Se a precisão for insuficiente:

```text
YOLO26n
   ↓
analisar dataset e erros
   ↓
YOLO26s
```

Não aumentar o modelo antes de verificar a qualidade do dataset.

### 13.4 Treinamento e inferência são separados

O computador de treinamento **não precisa ser o mesmo computador do aplicativo**.

```text
PC DE TREINAMENTO
      ↓
dataset
      ↓
treinamento YOLO
      ↓
best.pt
      ↓
opcionalmente exportar
      ↓
best.onnx
      ↓
copiar modelo
      ↓
PC DO PROTÓTIPO
      ↓
carrega modelo treinado
      ↓
somente inferência
```

---

## 14. Dataset

O dataset deverá ser criado preferencialmente usando a própria configuração física do protótipo.

### Variações recomendadas

Capturar:

- diferentes quantidades de parafusos;
- diferentes quantidades de porcas;
- parafusos + porcas;
- posições diferentes;
- rotações diferentes;
- objetos próximos;
- objetos parcialmente encostados;
- objetos próximos às bordas;
- bandeja vazia.

### Quantidade inicial sugerida

```text
200 a 500 imagens variadas
```

Isso é apenas uma referência inicial.

Priorizar diversidade e qualidade de anotação.

### Anotação

Cada item deve possuir:

- bounding box;
- classe correta.

### Estrutura sugerida

```text
dataset/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
│
└── labels/
    ├── train/
    ├── val/
    └── test/
```

### Exemplo de `dataset.yaml`

```yaml
path: C:/Projetos/contador_componentes/dataset

train: images/train
val: images/val
test: images/test

names:
  0: parafuso
  1: porca
```

---

## 15. Região de interesse — ROI

Como a câmera e a bandeja permanecerão fixas, o sistema deverá considerar o uso de ROI.

```text
Imagem completa
      ↓
recorte da bandeja
      ↓
imagem da área útil
      ↓
YOLO
```

Vantagens:

- reduz processamento;
- elimina elementos externos;
- aumenta consistência;
- pode melhorar desempenho.

---

## 16. Estabilização da contagem

A contagem pode oscilar entre frames:

```text
Frame 1 → 19
Frame 2 → 20
Frame 3 → 19
Frame 4 → 20
Frame 5 → 20
```

O sistema deve evitar alternância constante de status.

Baseline sugerido:

```text
Quantidade alvo detectada
por N frames consecutivos
        ↓
QUANTIDADE ATINGIDA
```

Valor inicial sugerido:

```text
N = 5
```

Essa estratégia deverá ser validada experimentalmente.

---

## 17. Regras de negócio

### RB-01
Contar somente a classe selecionada.

Exemplo:

```text
Selecionado: Parafuso

Imagem:
12 parafusos
4 porcas

Quantidade exibida: 12
```

### RB-02
Comparar continuamente quantidade detectada e quantidade requisitada.

### RB-03
Estados mínimos:

```text
AGUARDANDO CONFIGURAÇÃO
CONTANDO
QUANTIDADE ATINGIDA
```

Estados de erro opcionais:

```text
ERRO DE CÂMERA
MODELO NÃO CARREGADO
```

### RB-04
A descarga física ocorre manualmente após a indicação de quantidade atingida.

### RB-05
Após a descarga, deve existir forma de reiniciar a contagem.

Baseline recomendado:

```text
Botão RESET no Home Assistant
```

---

## 18. Requisitos funcionais

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

---

## 19. Requisitos não funcionais

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

---

## 20. Estrutura inicial de código

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

### Responsabilidades dos módulos

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

---

## 21. Sequência recomendada de desenvolvimento

### Etapa 1 — Webcam
Meta:

```text
Webcam → Python → imagem na tela
```

### Etapa 2 — Captura do dataset
Criar uma ferramenta simples para salvar frames.

### Etapa 3 — Dataset e anotação
Capturar, anotar e dividir `train/val/test`.

### Etapa 4 — Primeiro treinamento
Baseline:

```text
YOLO26n
imgsz = 640
```

### Etapa 5 — Validação em fotografias
Testar imagens nunca vistas pelo modelo.

### Etapa 6 — Webcam + IA

```text
Webcam → ROI → YOLO → bounding boxes
```

### Etapa 7 — Contagem

```text
detections → filtrar classe → contar
```

### Etapa 8 — Estabilização
Reduzir oscilações entre frames.

### Etapa 9 — MQTT + Home Assistant
Integrar somente após a IA funcionar localmente.

### Etapa 10 — Stream de vídeo
Integrar HTTP/MJPEG ou RTSP.

### Etapa 11 — Computador final
Testar desempenho no equipamento real.

Se necessário:
- reduzir resolução;
- exportar para ONNX;
- ajustar FPS;
- otimizar inferência.

---

## 22. Deployment do modelo

Durante o desenvolvimento:

```text
best.pt
```

Para computador final, avaliar:

```text
best.onnx
```

A escolha deve ser baseada em testes reais de desempenho.

---

## 23. Critérios de aceitação do protótipo

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

---

## 24. Métricas de validação

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

---

## 25. Materiais previstos

| Item | Quantidade | Especificação inicial | Função |
|---|---:|---|---|
| Webcam USB | 1 | Preferencialmente 1080p / UVC | Captura de imagem |
| Computador de execução | 1 | CPU compatível; 8 GB RAM ou mais recomendado | Aplicação + IA + Home Assistant |
| Iluminação LED | 1 conjunto | Iluminação uniforme | Padronizar a imagem |
| Bandeja | 1 | Impressão 3D | Área de inspeção |
| Fundo deslizante | 1 | Impressão 3D | Descarga manual |
| Guias/trilhos | 2 | Impressão 3D | Movimento do fundo |
| Puxador | 1 | Impressão 3D | Acionamento manual |
| Rampa afunilada | 1 | Impressão 3D | Direcionamento dos itens |
| Recipiente | 1 | Impresso ou comercial | Coleta |
| Suporte da câmera | 1 | Impressão 3D | Posicionamento fixo |
| Estrutura/base | 1 conjunto | PLA ou PETG | Sustentação |
| Filamento | Conforme necessidade | PLA/PETG 1,75 mm | Fabricação |
| Fixadores | Conforme necessidade | M3/M4 ou similares | Montagem |
| Parafusos de teste | Variável | Modelo a definir | Classe 1 |
| Porcas de teste | Variável | Modelo a definir | Classe 2 |

---

## 26. Impressão 3D

### Peças previstas
- base;
- colunas;
- suporte da câmera;
- bandeja;
- fundo deslizante;
- trilhos;
- puxador;
- rampa;
- recipiente ou suporte;
- reforços estruturais.

### Material
Primeira opção:

```text
PLA
```

Alternativa:

```text
PETG
```

### Cuidados
- permitir impressão modular;
- prever desmontagem;
- usar fixadores metálicos;
- garantir rigidez do suporte da câmera;
- evitar vibração;
- usar superfície que favoreça contraste visual;
- garantir inclinação suficiente na rampa;
- fazer o fundo deslizar sem folga excessiva.

---

## 27. Equipe

Integrantes:

1. Augusto
2. Jefferson
3. Gabriel
4. Clara
5. Murilo
6. Romulo

### Augusto + Jefferson — Estrutura mecânica
- CAD;
- impressão 3D;
- bandeja;
- fundo deslizante;
- rampa;
- suporte da câmera;
- montagem;
- testes mecânicos.

### Gabriel + Murilo — Visão computacional e backend
- Python;
- OpenCV;
- webcam;
- dataset;
- anotação;
- treinamento YOLO;
- inferência;
- contagem;
- MQTT;
- stream de vídeo.

### Clara + Romulo — Home Assistant, integração e documentação
- Home Assistant;
- dashboard;
- configuração MQTT;
- interface de seleção;
- quantidade alvo;
- status;
- vídeo;
- documentação;
- testes integrados.

Todos participam da integração e validação final.

---

## 28. Decisões já tomadas

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
| Modelo da webcam | GoodVision |
| Resolução final de captura | 1080p / 30 fps |

---

## 29. Pontos ainda em aberto

Outra IA deve **perguntar ou sinalizar**, e não inventar:

1. dimensões da bandeja;
2. altura exata da câmera;
3. tipo e posição da iluminação;
4. PLA ou PETG definitivo;
5. modelos exatos de parafuso e porca;
6. quantidade máxima de componentes;
7. ferramenta de anotação;
8. método final de estabilização;
9. número de frames para confirmação;
10. HTTP/MJPEG ou RTSP;
11. especificação do computador final;
12. formato final `.pt` ou `.onnx`;
13. layout final do dashboard;
14. método definitivo de reset;
15. dimensões e inclinação da rampa.

> Já decididos e removidos desta lista: modelo exato da webcam (GoodVision) e
> resolução final de captura (1080p/30fps) — ver seção 28.

---

## 30. Possíveis expansões futuras

Fora do MVP, mas possíveis:

- arruelas;
- diferentes modelos de parafusos;
- diferentes tipos de porcas;
- múltiplas classes simultâneas;
- reconhecimento de kits completos;
- histórico de contagens;
- banco de dados;
- relatórios;
- rastreabilidade;
- indicadores;
- integração com sistemas externos;
- acionamento automático do fundo;
- notificações;
- hardware edge dedicado;
- otimizações de inferência.

---

## 31. Princípio de desenvolvimento

> **Primeiro fazer funcionar corretamente em uma etapa simples; depois integrar.**

Ordem:

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

---

## 32. Primeiro passo prático de código

O primeiro programa deve apenas:

1. abrir a webcam;
2. mostrar a imagem;
3. permitir encerrar com uma tecla;
4. futuramente permitir salvar frames para o dataset.

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

Nenhuma IA é necessária nessa primeira etapa.

---

## 33. Resumo de uma frase

> Sistema local de visão computacional que utiliza uma webcam, Python, OpenCV e YOLO para identificar e contar parafusos ou porcas colocados em uma bandeja fixa, recebe a quantidade desejada e apresenta vídeo, contagem e status no Home Assistant, permitindo posteriormente a descarga manual dos componentes por um fundo deslizante para uma rampa afunilada e recipiente.

---

## 34. Contexto rápido para outra IA

```text
PROJETO:
Contador inteligente de parafusos e porcas.

FÍSICO:
Webcam em cima → bandeja fixa → fundo deslizante manual
→ rampa afunilada → recipiente.

IA:
Python + OpenCV + YOLO.
Primeiras classes: parafuso e porca.
Baseline: YOLO26n.
Câmera e iluminação fixas.
ROI da bandeja.

INTERFACE:
Home Assistant.

ENTRADAS:
Tipo de componente + quantidade desejada.

SAÍDAS:
Vídeo, bounding boxes, quantidade detectada e status.

COMUNICAÇÃO:
MQTT para dados.
HTTP/MJPEG ou RTSP para vídeo.

NÃO USAR NA V1:
Esteira, ESP32, motores, servos, relés, banco de dados,
automação do fundo.

TREINAMENTO:
Pode ocorrer em PC mais potente.
Aplicativo final usa somente inferência.

ORDEM DE DESENVOLVIMENTO:
Webcam → dataset → treinamento → detecção → contagem
→ estabilização → MQTT → Home Assistant → vídeo.
```

---

**Fim do PRD — versão 1.0**
