# TASKS.md — Contador Inteligente de Componentes

Lista de tarefas do projeto, organizada em **sprints**, seguindo a ordem de desenvolvimento
recomendada no `PRD.md` (seções 21 e 31): Câmera → Dataset → YOLO → Contagem → Estabilização →
MQTT → Home Assistant → Streaming → Integração física completa.

Convenções:

- `[ ]` não iniciado / `[x]` concluído. Marque a subtarefa quando concluída e só marque a
  tarefa-pai quando **todas** as suas subtarefas estiverem concluídas.
- Itens marcados com **⚠️ Ponto em aberto** referenciam a seção 29 do `PRD.md` — não devem ser
  decididos unilateralmente por uma IA; exigem decisão do time antes de prosseguir.
- A Sprint 12 e a Sprint 13 (estrutura física e iluminação) podem ser executadas **em paralelo**
  às Sprints 1–11 (o time mecânico não depende do time de software para avançar), mas a Sprint 14
  (integração física completa) depende de ambas as frentes estarem prontas.
- Nenhuma tarefa de banco de dados, histórico, esteira, ESP32/microcontroladores ou automação do
  fundo deslizante deve ser criada — está fora do escopo da v1 (`CLAUDE.md` / PRD seção 5.2).

---

## Sprint 0 — Preparação do ambiente e planejamento

### [x] 0.1 Configurar ambiente de desenvolvimento Python
Preparar a base do projeto antes de escrever qualquer lógica de captura ou IA.
- [x] 0.1.1 Definir e instalar a versão do Python a ser usada por todo o time (registrar a versão escolhida no README)
- [x] 0.1.2 Criar ambiente virtual (`venv`) do projeto
- [x] 0.1.3 Criar `requirements.txt` inicial com as dependências já certas pelo PRD (`opencv-python`, `ultralytics`, cliente MQTT em Python, ex. `paho-mqtt`)
- [x] 0.1.4 Criar a estrutura de pastas `contador_componentes/` exatamente como descrito na seção 20 do PRD (`app/`, `training/`, `models/`, `dataset/`, `tests/`)
- [x] 0.1.5 Criar arquivos `__init__.py` vazios em `app/` para tratá-lo como pacote Python

### [x] 0.2 Configurar controle de versão e convenções do repositório
- [x] 0.2.1 Revisar/criar `.gitignore` cobrindo ambiente virtual, `__pycache__`, imagens de dataset e pesos de modelo (`*.pt`, `*.onnx`) — decidir se pesos/dataset ficam versionados ou fora do Git
- [x] 0.2.2 Definir e documentar convenção de mensagens de commit do time, se ainda não houver uma

---

## Sprint 1 — Captura de vídeo via webcam (PRD Etapa 1 / seção 32)

### [x] 1.1 Programa mínimo de captura de webcam
Reproduzir localmente o primeiro passo prático de código do PRD (seção 32), sem nenhuma IA envolvida.
- [x] 1.1.1 Abrir a webcam padrão (`cv2.VideoCapture`) em um script isolado
- [x] 1.1.2 Exibir o stream ao vivo em uma janela OpenCV
- [x] 1.1.3 Permitir encerrar o programa pressionando uma tecla (ex.: `q`)
- [x] 1.1.4 Tratar o caso de falha ao abrir a câmera (log claro de erro; é a base do futuro estado `ERRO DE CÂMERA` da RB-03)

### [ ] 1.2 Validar captura com o hardware físico real
- [x] 1.2.1 ~~⚠️ Ponto em aberto~~: modelo da webcam confirmado pelo time — **GoodVision** (registrado no PRD seção 28)
- [x] 1.2.2 ~~⚠️ Ponto em aberto~~: resolução final de captura confirmada pelo time — **1080p / 30 fps** (registrado no PRD seção 28)
- [x] 1.2.3 Posicionar fisicamente a câmera de forma que toda a área da bandeja fique visível (mesmo que a bandeja definitiva ainda não exista, usar um mock/referência de área) — **ação física, requer execução manual pelo time; não pode ser feita por uma IA**
- [x] 1.2.4 Registrar em foto/anotação a posição de referência da câmera para reprodutibilidade futura — **idem, depende de 1.2.3 já ter sido feito fisicamente**

### [x] 1.3 Estruturar `app/camera.py` inicial
Migrar o script solto da tarefa 1.1 para o módulo definitivo do projeto (RNF-05/RNF-06 — não concentrar tudo em um único arquivo).
- [x] 1.3.1 Implementar `open_camera(indice_ou_config)` retornando o objeto de captura
- [x] 1.3.2 Implementar `read_frame(camera)` retornando o frame atual (ou erro tratado)
- [x] 1.3.3 Implementar `release_camera(camera)` para liberar o dispositivo corretamente
- [x] 1.3.4 Externalizar o índice/identificador do dispositivo de câmera para `app/config.py` (nada de valores fixos espalhados pelo código)

---

## Sprint 2 — Ferramenta de captura do dataset (PRD Etapa 2)

> ⚠️ Ponto em aberto que bloqueia a captura em massa: confirmar com o time os modelos exatos de
> parafuso e porca a usar (PRD 29.7) antes de capturar o dataset — capturar com peças diferentes
> das definitivas pode invalidar o treinamento.

### [ ] 2.1 Script de captura de frames para dataset
- [ ] 2.1.1 Reaproveitar `app/camera.py` (sprint 1) para abrir o stream ao vivo
- [ ] 2.1.2 Implementar salvamento de frame ao pressionar uma tecla (ex.: `s`)
- [ ] 2.1.3 Nomear os arquivos salvos com timestamp/contador incremental, evitando sobrescrita
- [ ] 2.1.4 Salvar os frames capturados em `dataset/images/raw/` (pasta de captura bruta, antes do split em train/val/test)

### [ ] 2.2 Protocolo de captura variada (PRD seção 14)
Garantir diversidade de cenários no dataset antes de anotar.
- [ ] 2.2.1 Capturar cenas com diferentes quantidades de parafusos (poucos, muitos, próximo do limite da bandeja)
- [ ] 2.2.2 Capturar cenas com diferentes quantidades de porcas
- [ ] 2.2.3 Capturar cenas misturando parafusos e porcas na mesma imagem
- [ ] 2.2.4 Capturar objetos em posições e rotações variadas
- [ ] 2.2.5 Capturar objetos próximos entre si e parcialmente encostados
- [ ] 2.2.6 Capturar objetos próximos às bordas da bandeja
- [ ] 2.2.7 Capturar a bandeja vazia (imagem de referência sem objetos)

### [ ] 2.3 Meta quantitativa inicial do dataset
- [ ] 2.3.1 Acompanhar a contagem de imagens capturadas até atingir a faixa de referência de 200 a 500 imagens (PRD seção 14 — apenas referência inicial, não é limite rígido)
- [ ] 2.3.2 Revisar visualmente a diversidade/qualidade das capturas antes de prosseguir para a anotação (priorizar diversidade sobre quantidade)

---

## Sprint 3 — Organização e anotação do dataset (PRD Etapa 3 / seção 14)

### [ ] 3.1 Escolher ferramenta de anotação
- [ ] 3.1.1 ⚠️ Ponto em aberto: decidir com o time a ferramenta de anotação a ser usada (PRD 29.9 — ex.: LabelImg, CVAT, Roboflow ou similar) antes de iniciar a anotação em massa
- [ ] 3.1.2 Validar que a ferramenta escolhida exporta rótulos no formato YOLO (`classe x_center y_center width height` normalizado)

### [ ] 3.2 Anotar as imagens capturadas
- [ ] 3.2.1 Anotar bounding box de cada parafuso presente nas imagens (classe `0 = parafuso`)
- [ ] 3.2.2 Anotar bounding box de cada porca presente nas imagens (classe `1 = porca`)
- [ ] 3.2.3 Revisar por amostragem um subconjunto das anotações para checar consistência de critério entre anotadores (relevante pois há mais de uma pessoa na equipe de visão computacional)

### [ ] 3.3 Dividir o dataset em train/val/test
- [ ] 3.3.1 Definir a proporção do split (ex.: 70/20/10 — a validar com o time; registrar a decisão)
- [ ] 3.3.2 Organizar imagens em `dataset/images/train/`, `dataset/images/val/`, `dataset/images/test/`
- [ ] 3.3.3 Organizar rótulos correspondentes em `dataset/labels/train/`, `dataset/labels/val/`, `dataset/labels/test/`
- [ ] 3.3.4 Conferir que cada imagem tem exatamente um arquivo de rótulo correspondente (mesmo nome, extensão `.txt`)

### [ ] 3.4 Criar `training/dataset.yaml`
- [ ] 3.4.1 Definir o campo `path` apontando para a raiz do dataset
- [ ] 3.4.2 Mapear `train`, `val`, `test` para as respectivas subpastas
- [ ] 3.4.3 Mapear as classes `0: parafuso` e `1: porca` (exatamente como na seção 13.2 do PRD, sem adicionar classes extras)
- [ ] 3.4.4 Validar que o `dataset.yaml` carrega sem erros com a biblioteca YOLO escolhida

---

## Sprint 4 — Primeiro treinamento YOLO (PRD Etapa 4 / seção 13.3–13.4)

### [ ] 4.1 Preparar ambiente de treinamento
Lembrete: a máquina de treino pode ser diferente da máquina de inferência (PRD 13.4) — não acoplar o código de treino a suposições sobre o hardware final.
- [ ] 4.1.1 Instalar as dependências de treinamento (ex.: `ultralytics`) na máquina escolhida para treinar
- [ ] 4.1.2 Criar `training/train.py` com os parâmetros de treinamento (modelo base, dataset.yaml, imgsz, épocas)

### [ ] 4.2 Treinar o modelo baseline YOLO26n
- [ ] 4.2.1 Configurar `imgsz = 640` conforme baseline definido no PRD (seção 21, Etapa 4)
- [ ] 4.2.2 Definir número inicial de épocas (valor a ajustar experimentalmente; registrar o valor usado)
- [ ] 4.2.3 Executar o treinamento e acompanhar as curvas de loss e métricas (mAP) durante o processo
- [ ] 4.2.4 Não escalar para YOLO26s nesta etapa — isso só é permitido após analisar dataset/erros (regra explícita do PRD seção 13.3)

### [ ] 4.3 Coletar e registrar o artefato treinado
- [ ] 4.3.1 Copiar o `best.pt` gerado para `models/`
- [ ] 4.3.2 Registrar as métricas de treino obtidas (precisão/recall preliminares) em um log ou anotação para comparação em treinamentos futuros

---

## Sprint 5 — Validação do modelo treinado (PRD Etapa 5 / seção 24)

### [ ] 5.1 Testar em imagens nunca vistas pelo modelo
- [ ] 5.1.1 Garantir que o conjunto de teste (`dataset/images/test/`) não foi usado em nenhum momento do treino
- [ ] 5.1.2 Rodar inferência do `best.pt` sobre o conjunto de teste
- [ ] 5.1.3 Inspecionar visualmente as detecções (bounding boxes sobrepostas às imagens) em busca de erros óbvios

### [ ] 5.2 Avaliar métricas de IA (PRD seção 24)
- [ ] 5.2.1 Calcular precisão do modelo
- [ ] 5.2.2 Calcular recall do modelo
- [ ] 5.2.3 Levantar falsos positivos (objetos detectados que não existem ou classe errada)
- [ ] 5.2.4 Levantar falsos negativos (objetos reais não detectados)
- [ ] 5.2.5 Calcular erro de contagem (quantidade detectada vs. quantidade real conhecida em cada imagem de teste)

### [ ] 5.3 Decidir próximos passos com base nos erros
- [ ] 5.3.1 Categorizar os erros encontrados por causa provável (oclusão, proximidade da borda, iluminação, objetos encostados)
- [ ] 5.3.2 Decidir se é necessário capturar/anotar mais dados de dataset para as categorias com mais erro (retornar à Sprint 2/3 se necessário)
- [ ] 5.3.3 Só considerar migrar para YOLO26s depois de esgotar melhorias de dataset, conforme regra do PRD (seção 13.3)

---

## Sprint 6 — Integração webcam + ROI + YOLO ao vivo (PRD Etapa 6 / seção 15)

### [ ] 6.1 Implementar recorte de ROI em `app/camera.py`
- [ ] 6.1.1 Definir as coordenadas fixas da área útil da bandeja (depende da posição física definitiva da câmera — sincronizar com Sprint 12/13 se a estrutura final já estiver montada; caso contrário, usar a posição de referência da Sprint 1)
- [ ] 6.1.2 Implementar `apply_roi(frame)` retornando apenas a região da bandeja
- [ ] 6.1.3 Criar uma ferramenta simples de calibração visual do ROI (ex.: overlay do retângulo de corte sobre o frame ao vivo, ajustável antes de travar os valores)
- [ ] 6.1.4 Externalizar as coordenadas do ROI para `app/config.py`

### [ ] 6.2 Criar `app/detector.py`
- [ ] 6.2.1 Implementar `load_model(caminho_modelo)` carregando o `best.pt` treinado (ou `.onnx`, quando essa decisão for tomada — ver Sprint 14)
- [ ] 6.2.2 Implementar `run_inference(frame)` retornando lista de detecções (classe, confiança, bounding box)
- [ ] 6.2.3 Externalizar o caminho do modelo para `app/config.py`

### [ ] 6.3 Montar o pipeline ao vivo webcam → ROI → YOLO → bounding boxes
- [ ] 6.3.1 Implementar o loop principal: captura de frame → aplicação de ROI → inferência → desenho das bounding boxes com classe/confiança
- [ ] 6.3.2 Exibir o resultado em uma janela local para validação manual (etapa ainda sem MQTT/Home Assistant)

### [ ] 6.4 Validar desempenho básico do pipeline
- [ ] 6.4.1 Medir o FPS obtido nesta etapa do pipeline
- [ ] 6.4.2 Medir uso de CPU e RAM durante a execução
- [ ] 6.4.3 Registrar os números como baseline para comparação após otimizações futuras (Sprint 14)

---

## Sprint 7 — Lógica de contagem (PRD Etapa 7 / RB-01 / RB-02)

### [ ] 7.1 Criar `app/counter.py` — filtragem por classe
- [ ] 7.1.1 Implementar `filter_by_class(detections, classe_selecionada)`
- [ ] 7.1.2 Garantir que a classe não selecionada seja completamente ignorada na contagem (RB-01 — ex.: se "parafuso" está selecionado, porcas no frame não entram na contagem exibida)

### [ ] 7.2 Contagem dos objetos detectados
- [ ] 7.2.1 Implementar `count_objects(detections_filtradas)` retornando a quantidade inteira detectada

### [ ] 7.3 Comparação com a quantidade alvo e máquina de estados (RB-02 / RB-03)
- [ ] 7.3.1 Implementar `compare_counts(detectado, esperado)` retornando o estado correspondente
- [ ] 7.3.2 Implementar os estados mínimos da máquina de estados: `AGUARDANDO CONFIGURAÇÃO`, `CONTANDO`, `QUANTIDADE ATINGIDA`, `QUANTIDADE EXCEDIDA`
- [ ] 7.3.3 Implementar os estados de erro opcionais: `ERRO DE CÂMERA`, `MODELO NÃO CARREGADO` (conectar ao tratamento de erro já iniciado na Sprint 1.1.4)

### [ ] 7.4 Testes manuais da lógica de contagem
- [ ] 7.4.1 Testar cenário com a quantidade exata de parafusos configurada como alvo
- [ ] 7.4.2 Testar cenário misto (parafusos + porcas) validando que a contagem exibida reflete apenas a classe selecionada (reproduzir o exemplo da seção 17 do PRD: 12 parafusos + 4 porcas → exibir 12)
- [ ] 7.4.3 Testar transição de estado `AGUARDANDO CONFIGURAÇÃO` → `CONTANDO` → `QUANTIDADE ATINGIDA` OU → `QUANTIDADE EXCEDIDA`

---

## Sprint 8 — Estabilização da contagem (PRD Etapa 8 / seção 16)

### [ ] 8.1 Implementar estabilização por N frames consecutivos
- [ ] 8.1.1 Manter um histórico das últimas leituras de contagem por frame
- [ ] 8.1.2 Implementar a regra: só transicionar para `QUANTIDADE ATINGIDA` quando a contagem alvo se mantiver por N frames consecutivos
- [ ] 8.1.3 Definir N=5 como valor inicial (baseline sugerido na seção 16 do PRD), configurável em `app/config.py`

### [ ] 8.2 Validar experimentalmente o valor de N
- [ ] 8.2.1 ⚠️ Ponto em aberto: testar com N=5 e observar se ainda há oscilações de status perceptíveis (PRD 29.10/29.11)
- [ ] 8.2.2 Ajustar o valor de N caso necessário e documentar a decisão final adotada

### [ ] 8.3 Tratar reinício da estabilização
- [ ] 8.3.1 Reiniciar o contador de frames consecutivos sempre que a contagem cair abaixo do valor alvo
- [ ] 8.3.2 Reiniciar a estabilização ao trocar a classe selecionada ou a quantidade alvo (evitar herdar histórico de uma configuração anterior)

---

## Sprint 9 — Integração MQTT (PRD Etapa 9 / seção 11.1)

### [ ] 9.1 Configurar broker MQTT
- [ ] 9.1.1 Confirmar com o time se já existe um broker MQTT definido (ex.: Mosquitto) ou se precisa ser instalado
- [ ] 9.1.2 Configurar autenticação básica do broker, se aplicável ao ambiente do time

### [ ] 9.2 Criar `app/mqtt_client.py` — recepção de configuração
- [ ] 9.2.1 Implementar assinatura do tópico `contador/config/componente`
- [ ] 9.2.2 Implementar assinatura do tópico `contador/config/quantidade`
- [ ] 9.2.3 Implementar recepção de comando de iniciar/resetar contagem (tópico a definir junto com a Sprint 10, alinhado à RB-05)
- [ ] 9.2.4 Validar/tratar mensagens malformadas ou fora do domínio esperado (ex.: componente diferente de parafuso/porca)

### [ ] 9.3 Criar `app/mqtt_client.py` — publicação de status
- [ ] 9.3.1 Implementar publicação em `contador/status/detectado`
- [ ] 9.3.2 Implementar publicação em `contador/status/esperado`
- [ ] 9.3.3 Implementar publicação em `contador/status/estado`
- [ ] 9.3.4 Definir a frequência de publicação (a cada frame processado, a cada mudança de valor, ou intervalo fixo) e justificar a escolha

### [ ] 9.4 Orquestrar tudo em `app/main.py`
- [ ] 9.4.1 Conectar `mqtt_client` aos módulos `camera`, `detector` e `counter` já existentes
- [ ] 9.4.2 Implementar o loop principal completo: captura → ROI → inferência → filtragem/contagem → estabilização → publicação MQTT
- [ ] 9.4.3 Garantir que o loop reage a mudanças de configuração recebidas via MQTT em tempo real (sem precisar reiniciar a aplicação)

### [ ] 9.5 Testes de integração MQTT isolados (antes do Home Assistant)
- [ ] 9.5.1 Testar publish/subscribe com um cliente MQTT genérico (ex.: MQTT Explorer, `mosquitto_sub`/`mosquitto_pub`) para validar os tópicos antes de conectar ao Home Assistant
- [ ] 9.5.2 Validar que os nomes de tópico usados batem com os definidos na seção 11.1 do PRD (ou registrar formalmente qualquer ajuste feito nos nomes)

---

## Sprint 10 — Integração Home Assistant (PRD Etapa 9 continuação / seção 12)

### [ ] 10.1 Configurar integração MQTT no Home Assistant
- [ ] 10.1.1 Configurar a conexão do Home Assistant ao mesmo broker MQTT usado pela aplicação Python
- [ ] 10.1.2 Criar entidade MQTT sensor para "detectado"
- [ ] 10.1.3 Criar entidade MQTT sensor para "esperado"
- [ ] 10.1.4 Criar entidade MQTT sensor para "estado"

### [ ] 10.2 Criar controles de configuração no Home Assistant
- [ ] 10.2.1 Criar seletor de componente (Parafuso/Porca) publicando em `contador/config/componente`
- [ ] 10.2.2 Criar campo numérico de quantidade desejada publicando em `contador/config/quantidade` (⚠️ Ponto em aberto: o limite máximo do campo depende da quantidade máxima de componentes suportada, PRD 29.8)
- [ ] 10.2.3 Criar botão de reset (RB-05) publicando o comando de reset definido na Sprint 9.2.3
- [ ] 10.2.4 ⚠️ Ponto em aberto: confirmar com o time o método definitivo de reset (PRD 29.16) antes de finalizar este item

### [ ] 10.3 Montar o dashboard de monitoramento (PRD seção 12)
- [ ] 10.3.1 Adicionar exibição da quantidade atual detectada
- [ ] 10.3.2 Adicionar exibição da quantidade desejada
- [ ] 10.3.3 Adicionar exibição do status textual (`AGUARDANDO CONFIGURAÇÃO` / `CONTANDO` / `QUANTIDADE ATINGIDA` / `QUANTIDADE EXCEDIDA` / estados de erro)
- [ ] 10.3.4 ⚠️ Ponto em aberto: validar com o time o layout final do dashboard (PRD 29.15) antes de considerar esta tarefa concluída

### [ ] 10.4 Testes end-to-end de configuração via Home Assistant
- [ ] 10.4.1 Alterar o componente selecionado pelo Home Assistant e validar que a aplicação Python reflete a mudança
- [ ] 10.4.2 Alterar a quantidade desejada pelo Home Assistant e validar atualização em tempo real na aplicação
- [ ] 10.4.3 Testar o botão de reset e validar que uma nova contagem pode ser iniciada corretamente (RB-05)

---

## Sprint 11 — Streaming de vídeo (PRD Etapa 10 / seção 11.2)

### [ ] 11.1 Criar `app/video_stream.py` com transmissão HTTP/MJPEG
- [ ] 11.1.1 Implementar função que recebe o frame já anotado (com bounding boxes) vindo do pipeline principal
- [ ] 11.1.2 Implementar um servidor HTTP simples que sirva o stream em formato MJPEG

### [ ] 11.2 Avaliar alternativa RTSP
- [ ] 11.2.1 ⚠️ Ponto em aberto: implementar/testar um protótipo de transmissão via RTSP (PRD 29.12)
- [ ] 11.2.2 Comparar HTTP/MJPEG vs. RTSP em estabilidade, latência e consumo de CPU, conforme critério da seção 11.2 do PRD

### [ ] 11.3 Decidir o protocolo de vídeo final
- [ ] 11.3.1 Registrar a decisão final (MJPEG ou RTSP) com base nos testes da tarefa 11.2, atualizando a tabela de decisões (PRD seção 28) se o time mantiver esse controle

### [ ] 11.4 Integrar o stream ao Home Assistant
- [ ] 11.4.1 Configurar uma entidade de câmera genérica no Home Assistant apontando para o stream escolhido
- [ ] 11.4.2 Validar que o vídeo ao vivo com bounding boxes aparece corretamente no dashboard (PRD seção 12)

---

## Sprint 12 — Estrutura física / mecânica (pode rodar em paralelo às Sprints 1–11)

> Responsabilidade primária: dupla mecânica do time (PRD seção 27). Referências: PRD seções 6, 25 e 26.
>
> ⚠️ Ponto em aberto que bloqueia o dimensionamento da bandeja (tarefa 12.1): confirmar a
> quantidade máxima de componentes que o sistema precisa suportar por sessão (PRD 29.8).

### [ ] 12.1 Projetar a bandeja fixa
- [ ] 12.1.1 Modelar em CAD garantindo área interna totalmente visível pela câmera
- [ ] 12.1.2 Modelar bordas suficientes para impedir que componentes escapem
- [ ] 12.1.3 Escolher/definir uma superfície com bom contraste visual em relação aos objetos (parafusos/porcas metálicos)
- [ ] 12.1.4 ⚠️ Ponto em aberto: definir as dimensões finais da bandeja (PRD 29.3)
- [ ] 12.1.5 Garantir que o fundo da bandeja seja uma peça independente da estrutura lateral (necessário para o fundo deslizante)

### [ ] 12.2 Projetar o fundo deslizante manual
- [ ] 12.2.1 Modelar a placa deslizante que sustenta os componentes quando fechada
- [ ] 12.2.2 Modelar trilhos/guias para movimentação suave e com folga mínima
- [ ] 12.2.3 Modelar um puxador acessível para acionamento manual
- [ ] 12.2.4 Garantir abertura suficiente para descarregar todos os componentes ao ser puxado

### [ ] 12.3 Projetar a rampa afunilada
- [ ] 12.3.1 Modelar a rampa posicionada imediatamente abaixo da bandeja
- [ ] 12.3.2 Modelar geometria que impeça espalhamento dos componentes durante a queda
- [ ] 12.3.3 Modelar o afunilamento da saída para direcionar os componentes ao recipiente
- [ ] 12.3.4 ⚠️ Ponto em aberto: definir dimensões e inclinação finais da rampa (PRD 29.17) — validar experimentalmente que a inclinação é suficiente para o material dos componentes escorregar

### [ ] 12.4 Projetar o suporte da câmera
- [ ] 12.4.1 Modelar um suporte rígido que evite vibração
- [ ] 12.4.2 ⚠️ Ponto em aberto: definir a altura exata da câmera (PRD 29.4) — coordenar com a Sprint 1.2 e a calibração de ROI da Sprint 6.1

### [ ] 12.5 Selecionar material de impressão definitivo
- [ ] 12.5.1 ⚠️ Ponto em aberto: decidir entre PLA e PETG como material definitivo (PRD 29.6)

### [ ] 12.6 Imprimir e montar as peças
- [ ] 12.6.1 Imprimir bandeja, fundo deslizante, trilhos, puxador, rampa e suporte de câmera
- [ ] 12.6.2 Montar a estrutura completa, usando fixadores metálicos onde previsto (PRD seção 26)
- [ ] 12.6.3 Prever montagem modular e possibilidade de desmontagem, conforme diretriz da seção 26 do PRD

### [ ] 12.7 Testes mecânicos (métricas da seção 24 do PRD)
- [ ] 12.7.1 Testar deslizamento do fundo sem folga excessiva
- [ ] 12.7.2 Medir a taxa de descarga completa dos componentes pela rampa
- [ ] 12.7.3 Medir a taxa de componentes que ficam presos na bandeja
- [ ] 12.7.4 Medir a taxa de componentes que ficam presos na rampa
- [ ] 12.7.5 Registrar quando há necessidade de intervenção manual para completar a descarga

---

## Sprint 13 — Iluminação e ambiente controlado (RNF-01, pode rodar em paralelo às Sprints 1–11)

### [ ] 13.1 Definir e instalar iluminação padronizada
- [ ] 13.1.1 ⚠️ Ponto em aberto: decidir tipo e posição da iluminação (PRD 29.5)
- [ ] 13.1.2 Fixar a iluminação de forma a minimizar variação de luz ambiente ao longo do dia

### [ ] 13.2 Padronizar e documentar o posicionamento físico
- [ ] 13.2.1 Fixar as posições definitivas de câmera, bandeja e iluminação uma em relação à outra
- [ ] 13.2.2 Documentar (foto e/ou medidas) as posições definitivas para permitir remontagem idêntica no futuro

---

## Sprint 14 — Integração física completa no computador final (PRD Etapa 11 / seção 22)

### [ ] 14.1 Especificar e preparar o computador final
- [ ] 14.1.1 ⚠️ Ponto em aberto: confirmar a especificação do computador final de produção (PRD 29.13)
- [ ] 14.1.2 Instalar no computador final apenas as dependências necessárias para inferência (sem as dependências de treino, que só existem na máquina de treinamento)

### [ ] 14.2 Transferir o modelo treinado
- [ ] 14.2.1 Copiar o `best.pt` validado (Sprint 5) para o computador final
- [ ] 14.2.2 Avaliar exportação para `best.onnx` como possível otimização (PRD seção 22)
- [ ] 14.2.3 ⚠️ Ponto em aberto: decidir o formato final entre `.pt` e `.onnx` com base em testes reais de desempenho no hardware final (PRD 29.14)

### [ ] 14.3 Testar desempenho no hardware real
- [ ] 14.3.1 Medir FPS no computador final
- [ ] 14.3.2 Medir latência ponta a ponta (captura → contagem → publicação MQTT)
- [ ] 14.3.3 Medir uso de CPU, RAM e GPU (quando aplicável)
- [ ] 14.3.4 Se o desempenho for insuficiente: reduzir resolução de captura, ajustar FPS-alvo, ou otimizar a inferência (nessa ordem de prioridade, conforme PRD seção 21)

### [ ] 14.4 Montagem física completa do protótipo
- [ ] 14.4.1 Conectar a webcam ao computador final
- [ ] 14.4.2 Integrar a estrutura mecânica montada (Sprint 12) e a iluminação definitiva (Sprint 13) à posição da câmera
- [ ] 14.4.3 Validar cabeamento, alimentação elétrica e posicionamento final de todos os componentes físicos

---

## Sprint 15 — Testes finais e critérios de aceitação (PRD seção 23)

### [ ] 15.1 Validar cada critério de aceitação do protótipo
- [ ] 15.1.1 A webcam captura toda a bandeja de maneira estável
- [ ] 15.1.2 O usuário consegue selecionar `Parafuso` ou `Porca` pelo Home Assistant
- [ ] 15.1.3 O usuário consegue definir uma quantidade alvo pelo Home Assistant
- [ ] 15.1.4 O modelo identifica corretamente os componentes em condições normais de uso
- [ ] 15.1.5 A aplicação conta apenas a classe selecionada (RB-01)
- [ ] 15.1.6 A quantidade detectada aparece corretamente no Home Assistant
- [ ] 15.1.7 O status muda para `QUANTIDADE ATINGIDA` quando o alvo é alcançado
- [ ] 15.1.8 O vídeo da bandeja pode ser visualizado ao vivo no Home Assistant
- [ ] 15.1.9 A bandeja permite descarga manual pelo fundo deslizante
- [ ] 15.1.10 A rampa conduz os componentes ao recipiente sem perdas significativas

### [ ] 15.2 Testes de regressão end-to-end
- [ ] 15.2.1 Executar o cenário de uso de referência completo (PRD seção 8: selecionar Parafuso, alvo 20, acompanhar contagem até `QUANTIDADE ATINGIDA`)
- [ ] 15.2.2 Repetir o ciclo completo (contagem → descarga manual → reset → nova contagem) múltiplas vezes seguidas para checar estabilidade
- [ ] 15.2.3 Testar o cenário de troca de classe selecionada no meio de uma sessão (ex.: trocar de Parafuso para Porca) e validar que a contagem e a estabilização reiniciam corretamente

---

## Sprint 16 — Documentação final e encerramento do MVP

### [ ] 16.1 Atualizar a documentação técnica
- [ ] 16.1.1 Documentar, para cada ponto em aberto da seção 29 do PRD, qual foi a decisão final tomada
- [ ] 16.1.2 Atualizar o `README.md` do projeto com instruções de instalação, configuração e uso do protótipo final

### [ ] 16.2 Registrar aprendizados e próximos passos
- [ ] 16.2.1 Registrar as métricas finais obtidas (IA: precisão/recall; aplicação: FPS/latência; mecânica: taxa de descarga) em um documento de fechamento do MVP
- [ ] 16.2.2 Priorizar, junto ao time, quais expansões futuras da seção 30 do PRD (ex.: arruelas, múltiplas classes, histórico) fazem sentido buscar em uma próxima versão
