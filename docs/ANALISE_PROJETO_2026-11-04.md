# Análise do projeto e inventário de execução

Data: 04/11/2026. Base: arquivos desta cópia do repositório, código, TASKS.md, TASKS_OLD.md, PRD, documentação, relatórios e scripts de instalação. Este relatório é uma fotografia da análise; não substitui o PRD nem altera decisões de escopo ou marcações de tarefas.

## 1. Objetivo e estágio real

O objetivo é reduzir o trabalho e os erros da contagem manual de pequenos componentes: uma webcam observa uma área de inspeção; OpenCV captura a imagem; YOLO detecta parafusos (0) e porcas (1); o sistema conta somente a classe selecionada, compara com uma quantidade alvo e informa o resultado ao operador.

O software atual implementa captura → ROI → inferência → filtro por classe → contagem → estabilização → janela Tkinter. A aplicação mostra vídeo anotado, quantidade detectada, alvo e estados; permite trocar configurações e reiniciar a estabilização. Treinamento e inferência estão separados. Há ferramentas de captura, importação, conversão de labels, calibração e avaliação, além de infraestrutura para empacotamento Windows.

Diagnóstico: o núcleo do protótipo está implementado, mas o MVP ainda não está homologado. As pendências principais são confiabilidade do modelo, reprodutibilidade dos artefatos, calibração física, desempenho e aceite no computador final.

## 2. Divergência de escopo que precisa ser resolvida

O PRD declara ser a fonte de verdade e exige Home Assistant, MQTT, vídeo HTTP/MJPEG ou RTSP e estação mecânica com fundo deslizante manual e rampa. TASKS.md e o código passaram a usar Tkinter local; a Sprint 9 explicitamente exclui MQTT e streaming na v1. PENDENCIAS_HUMANAS.md reconhece essa mudança e pede atualização do PRD.

Consequência: pela implementação/plano atual, Home Assistant, MQTT e streaming foram retirados do MVP; pelo PRD ainda vigente, permanecem requisitos não atendidos. Não há evidência suficiente para considerar formalmente aprovada a alteração apenas porque ela aparece no código. É preciso registrar a decisão do time e alinhar PRD, README, docs, diagrama, agentes e critérios de aceite. A mecânica também deve ter seu escopo confirmado. TASKS_OLD.md guarda o plano anterior e não deve ser somado ao backlog atual, pois duplicaria tarefas.

CLAUDE.md, docs/README.md e docs/03-arquitetura.md ainda afirmam que não existe código, dataset ou build; isso está desatualizado. Há referências incorretas à numeração dos pontos em aberto do PRD. docs/02-escopo.md aponta para um arquivo inexistente chamado 14-pontos-em-aberto-e-expansoes.md; o arquivo existente começa com 12.

## 3. Como interpretar os números

A contagem abaixo inclui somente subtarefas finais de TASKS.md. O item 11.1.3 é um agrupador e suas três subtarefas são contadas individualmente. Tarefas-pai não são somadas novamente. Os números refletem checkboxes, não porcentagem de esforço, qualidade, aceite nem capacidade de execução nesta máquina.

Total: **141 subtarefas**, **102 marcadas como feitas** e **39 abertas** (72.3% marcadas).

| Sprint | Feitas | Abertas | Leitura técnica |
|---|---:|---:|---|
| 0 | 7 | 0 | Preparação registrada; venv não está presente nesta cópia. |
| 1 | 12 | 0 | Código presente; 1.2 está aberta apesar de todas as filhas marcadas. |
| 2 | 13 | 0 | Ferramenta presente e captura histórica documentada. |
| 3 | 13 | 0 | Organização/anotação históricas; faltam base atual e correções de labels. |
| 4 | 8 | 0 | Treino baseline documentado; pesos não estão nesta cópia. |
| 5 | 11 | 0 | Avaliação documentada; modelo final e melhorias continuam pendentes. |
| 6 | 8 | 4 | Faltam ROI definitiva e baseline de desempenho. |
| 7 | 9 | 0 | Lógica presente; validação ao vivo continua pendente nos relatórios. |
| 8 | 5 | 2 | Estabilização presente; N definitivo depende de teste ao vivo. |
| 9 | 14 | 1 | Interface e orquestração presentes; layout e teste físico pendentes. |
| 10 | 0 | 4 | Iluminação e posicionamento definitivos abertos. |
| 11 | 2 | 13 | Scripts de empacotamento presentes; implantação real aberta. |
| 12 | 0 | 11 | Aceite e regressão no protótipo final abertos. |
| 13 | 0 | 4 | Documentação final e encerramento abertos. |

## 4. O que está implementado

| Frente | Entregas existentes | Limite da evidência |
|---|---|---|
| Captura | camera.py; webcam_preview.py; dataset_capture.py; tratamento de abertura/leitura e liberação | Não configura explicitamente 1080p/30 fps |
| Dataset | importar_roboflow.py; poligonos_para_bbox.py; training/dataset.yaml | Dataset de destino ausente nesta cópia |
| Treino | train.py com modelo, dataset, resolução, épocas, dispositivo e pasta de saída configuráveis | Não oferece resume/batch/workers pela CLI atual |
| Avaliação | avaliar_teste.py e metricas_teste.py; métricas e análise de erros registradas | Pesos, predições JSON e runs não disponíveis localmente |
| Detecção | detector.py carrega .pt/.onnx, valida IDs/nomes e retorna caixas/confiança/classe | Precisa de peso externo compatível; suporte ONNX do pacote depende do build |
| Contagem | filtro por classe, comparação e estados aguardando/contando/atingida/excedida/erros | Acerto da lógica não garante acerto das detecções |
| Estabilização | N frames; N inicial 5; reinício por reset e mudança de configuração | Não corrige erro sistemático do modelo; sem histerese de saída |
| Interface | vídeo anotado, seletor, alvo positivo, reset, painel e layout adaptável | Aprovação de layout, limite máximo e reset definitivo em aberto |
| Orquestração | worker separado, caixa com último resultado, atualização Tk por after, reconexão e encerramento | Webcam/driver e latência reais ainda exigem ensaio |
| Distribuição | spec PyInstaller, build.ps1, Inno Setup, instruções, modelo externo, config_local.json, calibração no executável | Scripts presentes não comprovam pacote gerado ou validado no PC final |
| Testes | 12 arquivos, 183 funções test_ no código | Contagem de funções não é contagem de casos executados; há parametrização, skips e xfails |

## 5. Artefatos presentes e ausentes nesta cópia

- Existem 284 imagens e 284 labels em treinamento_yolo/: train 199, valid 57, test 28. A checagem por nome encontrou correspondência imagem/label em todos os splits. IDs observados: somente 0 e 1; coordenadas numéricas verificadas dentro de [0,1]. Isso não comprova completude visual das anotações.
- A maioria dos labels desse export contém polígonos, com algumas linhas bbox. O pipeline previsto é importar e converter para bounding boxes antes do treino de detecção.
- O arquivo training/dataset.yaml aponta para contador_componentes/dataset/, que não existe nesta cópia. O export presente não está diretamente no layout esperado pelo treino.
- O importador usa shutil.copy2 para diretórios de destino e não os cria. Portanto, a preparação de uma cópia nova precisa criar a estrutura de dataset antes de importar, ou o importador precisa ser ajustado.
- models/ contém somente .gitkeep. Não há best.pt nem best.onnx ali. Também faltam o run porcas_v2, seus checkpoints e o dataset ampliado de 482 imagens descrito nos relatórios (339/96/47).
- Não há venv do projeto nem dist/ no repositório examinado. Isso impede comprovar a disponibilidade do ambiente e dos pacotes de distribuição mencionados historicamente.
- README diz que dataset não é versionado, mas treinamento_yolo/ tem imagens e labels rastreados pelo Git. O .gitignore exclui o dataset organizado em contador_componentes/, não esse export. É necessário definir uma política coerente de compartilhamento e recuperação dos dados/pesos.

## 6. Qualidade do modelo: trabalho realizado e pendências

Os relatórios registram um baseline YOLO26n com 100 épocas, melhor época 98, e um candidato porcas_v2 interrompido por falta de memória na época 58 de 100. O registro informa que o modelo oficial não havia sido substituído; nesta cópia, nenhum dos dois pesos está disponível para confirmação.

Métricas históricas da validação da Sprint 5, confiança 0,5:

| Indicador | Baseline A | Candidato B |
|---|---:|---:|
| Recall de porca, teste total | 35,6% | 95,5% |
| Contagem exata de parafuso, teste total | 72,3% | 83,0% |
| Contagem exata de porca, teste total | 68,1% | 85,1% |
| Recall de parafuso, grupo independente | 89,3% | 82,1% |
| Contagem exata de parafuso, grupo independente | 50,0% | 40,0% |

Esses números não são uma reavaliação feita nesta análise. O grupo independente tem somente 10 imagens; boa parte do teste contém cenas próximas às do treino e há labels incompletos. O ganho do candidato no conjunto total não basta para homologação.

Pendências descritas nos relatórios, mesmo com a Sprint 5 marcada como concluída:

1. Corrigir os sete arquivos de teste identificados com labels incompletos e auditar fotos vizinhas no treino/validação.
2. Definir critério de anotação para peças parcialmente visíveis, encostadas, rosqueadas e na borda.
3. Separar os dados por sessão/rajada e reservar teste independente. Preservar nomes diferentes não elimina vazamento por imagens quase idênticas.
4. Capturar mais exemplos de sobreposição, peças encostadas, poses difíceis e negativos com ferramentas/distratores.
5. Concluir ou refazer o treinamento após a auditoria dos labels, controlando consumo de memória.
6. Reavaliar precisão, recall e contagem exata por classe em teste independente; calibrar o limiar de confiança, atualmente 0,5.
7. Escolher e disponibilizar o modelo final com identificação de versão e métricas. Continuar YOLO26n até esgotar melhorias de dados; YOLO26s não é uma pendência obrigatória.

## 7. Pendências de validação e inconsistências nas marcações

- 1.2: todas as filhas estão [x], mas a tarefa-pai continua [ ]. É uma inconsistência do checklist; não implica autorização para afirmar nova validação física.
- 7.4.1–7.4.3: [x] no TASKS, mas relatorio_testes_contagem.md registra testes com fotografias e deixa o checklist ao vivo aberto, inclusive a cena exata 12 parafusos + 4 porcas.
- 9.3.1–9.3.4: [x] no TASKS, mas plano_teste_manual_interface.md informa cobertura automatizada com hardware falso e contém resultados manuais em branco. Classificação adequada: validação automatizada implementada; validação física pendente.
- Sprint 5 concluída significa avaliação realizada e recomendações registradas; não significa modelo aprovado para produção.
- 11.1.3.1 e 11.1.3.2 têm código, mas não foi possível comprovar geração, instalação ou execução do pacote nesta análise. 11.1.3.3 continua aberta.
- O FPS ~8,6 citado no roteiro é um smoke test histórico a 640x480, sem janela; 21–25 FPS são inferência offline. Nenhum deles substitui medição do sistema completo no PC final.
- camera.open_camera não chama set para resolução/FPS. O padrão do driver pode divergir do 1080p/30 fps definido no PRD. Definir a captura real e verificá-la antes de calibrar ROI e medir desempenho.
- config.ROI = None, FRAMES_ESTABILIZACAO = 5, CONFIDENCE_THRESHOLD = 0.5 e QUANTIDADE_MAXIMA = None continuam valores de trabalho, não decisões finais de homologação.
- paho-mqtt está no requirements.txt, embora não seja usado pelo fluxo atual. O arquivo de desenvolvimento não fixa versões nem declara pytest; o arquivo de build fixa parte das dependências.

Achado adicional por leitura do código: em main.py, exceções genéricas de processamento só geram log e espera; nenhuma atualização de erro é publicada e a sequência de estabilização não é invalidada nesse caminho. Se a inferência falhar repetidamente após um resultado válido, a interface pode manter uma imagem/contagem/status antigo, inclusive ATINGIDA. Convém definir e testar a invalidação de resultado e a sinalização de falha de processamento. Esta observação foi estática, sem reprodução com o modelo real.

## 8. Ordem prática para concluir

1. Formalizar o escopo: Tkinter local ou requisitos originais de integração; esclarecer a mecânica e manter a decisão documentada.
2. Recuperar pesos, dataset atual e resultados; preparar ambiente Python 3.12 com dependências e criar o layout esperado. Corrigir a preparação/importação em uma cópia nova.
3. Auditar labels, reorganizar split, concluir treino e selecionar o modelo com teste independente.
4. Definir iluminação e posições; configurar/verificar resolução e FPS; calibrar ROI definitiva (6.1.1 e Sprint 10).
5. Medir FPS/CPU/RAM (6.4), validar contagem ao vivo (7.4), escolher N (8.2) e aprovar layout/reset/limite (9.1.6 e decisões associadas).
6. Tratar os achados de robustez; executar a suíte e o roteiro físico da interface, incluindo desconexão/reconexão da webcam e ciclos de reset.
7. Preparar o PC final, escolher formato .pt/.onnx com evidência, gerar e instalar o pacote, medir desempenho e latência (Sprint 11).
8. Executar aceite/regressão completos e registrar evidências (Sprint 12); finalizar documentação e relatório de métricas (Sprint 13).

A tarefa 11.3.4 é condicional: otimizar somente se as medições mostrarem desempenho insuficiente. ONNX deve ser avaliado como opção; não é necessário exportar por obrigação se .pt atender.

## 9. Verificações e limites desta análise

- Inspeção de estrutura, requisitos, backlog atual e histórico, código, testes existentes, relatórios e empacotamento.
- Análise sintática por ast.parse: 33 arquivos Python, sem erro de sintaxe. Isso não verifica imports nem comportamento.
- Inventário de funções de teste e checagem estrutural dos labels do export presente.
- Tentativa de executar a suíte com o Python 3.12.14 disponível: interrompida por No module named pytest. Não foram instaladas dependências nem executados treino, build ou testes físicos.
- O relatório histórico da Sprint 7 cita 147 passed e 13 xfailed; não corresponde a uma execução atual, e o código de testes cresceu desde então. Testes reais de modelo/dataset podem ser pulados quando faltam artefatos; testes Tk podem ser pulados sem display.
- Nenhum requisito, checkbox ou código de produção foi alterado. Os artefatos ausentes nesta cópia podem existir em outra máquina; ausência local não invalida o histórico registrado, mas impede sua reprodução aqui.

## 10. Inventário completo das tarefas-pai

Estado abaixo copiado de TASKS.md; ressalvas das seções anteriores prevalecem para interpretar validação real.

| Tarefa | Marcação | Descrição |
|---|---|---|
| 0.1 | Feita | Configurar ambiente de desenvolvimento Python |
| 0.2 | Feita | Configurar controle de versão e convenções do repositório |
| 1.1 | Feita | Programa mínimo de captura de webcam |
| 1.2 | Aberta | Validar captura com o hardware físico real |
| 1.3 | Feita | Estruturar `app/camera.py` inicial |
| 2.1 | Feita | Script de captura de frames para dataset |
| 2.2 | Feita | Protocolo de captura variada (PRD seção 14) |
| 2.3 | Feita | Meta quantitativa inicial do dataset |
| 3.1 | Feita | Escolher ferramenta de anotação |
| 3.2 | Feita | Anotar as imagens capturadas |
| 3.3 | Feita | Dividir o dataset em train/val/test |
| 3.4 | Feita | Criar `training/dataset.yaml` |
| 4.1 | Feita | Preparar ambiente de treinamento |
| 4.2 | Feita | Treinar o modelo baseline YOLO26n |
| 4.3 | Feita | Coletar e registrar o artefato treinado |
| 5.1 | Feita | Testar em imagens nunca vistas pelo modelo |
| 5.2 | Feita | Avaliar métricas de IA (PRD seção 24) |
| 5.3 | Feita | Decidir próximos passos com base nos erros |
| 6.1 | Aberta | Implementar recorte de ROI em `app/camera.py` |
| 6.2 | Feita | Criar `app/detector.py` |
| 6.3 | Feita | Montar o pipeline ao vivo webcam → ROI → YOLO → bounding boxes |
| 6.4 | Aberta | Validar desempenho básico do pipeline |
| 7.1 | Feita | Criar `app/counter.py` — filtragem por classe |
| 7.2 | Feita | Contagem dos objetos detectados |
| 7.3 | Feita | Comparação com a quantidade alvo e máquina de estados (RB-02 / RB-03) |
| 7.4 | Feita | Testes manuais da lógica de contagem |
| 8.1 | Feita | Implementar estabilização por N frames consecutivos |
| 8.2 | Aberta | Validar experimentalmente o valor de N |
| 8.3 | Feita | Tratar reinício da estabilização |
| 9.1 | Aberta | Criar `app/interface.py` (janela Tkinter) |
| 9.2 | Feita | Orquestrar tudo em `app/main.py` |
| 9.3 | Feita | Testes manuais da interface |
| 10.1 | Aberta | Definir e instalar iluminação padronizada |
| 10.2 | Aberta | Padronizar e documentar o posicionamento físico |
| 11.1 | Aberta | Especificar e preparar o computador final |
| 11.2 | Aberta | Transferir o modelo treinado |
| 11.3 | Aberta | Testar desempenho no hardware real |
| 11.4 | Aberta | Montagem completa do protótipo |
| 12.1 | Aberta | Validar cada critério de aceitação do protótipo |
| 12.2 | Aberta | Testes de regressão end-to-end |
| 13.1 | Aberta | Atualizar a documentação técnica |
| 13.2 | Aberta | Registrar aprendizados e próximos passos |

## 11. Inventário completo das subtarefas finais

Marcação documental, sem inferir homologação. Cada item aparece uma única vez.

### Sprint 0 — Preparação do ambiente e planejamento

- [x] 0.1.1 Definir e instalar a versão do Python a ser usada por todo o time (registrar a versão escolhida no README)
- [x] 0.1.2 Criar ambiente virtual (`venv`) do projeto
- [x] 0.1.3 Criar `requirements.txt` inicial com as dependências já certas pelo PRD (`opencv-python`, `ultralytics`, cliente MQTT em Python, ex. `paho-mqtt`)
- [x] 0.1.4 Criar a estrutura de pastas `contador_componentes/` exatamente como descrito na seção 20 do PRD (`app/`, `training/`, `models/`, `dataset/`, `tests/`)
- [x] 0.1.5 Criar arquivos `__init__.py` vazios em `app/` para tratá-lo como pacote Python
- [x] 0.2.1 Revisar/criar `.gitignore` cobrindo ambiente virtual, `__pycache__`, imagens de dataset e pesos de modelo (`*.pt`, `*.onnx`) — decidir se pesos/dataset ficam versionados ou fora do Git
- [x] 0.2.2 Definir e documentar convenção de mensagens de commit do time, se ainda não houver uma

### Sprint 1 — Captura de vídeo via webcam (PRD Etapa 1 / seção 32)

- [x] 1.1.1 Abrir a webcam padrão (`cv2.VideoCapture`) em um script isolado
- [x] 1.1.2 Exibir o stream ao vivo em uma janela OpenCV
- [x] 1.1.3 Permitir encerrar o programa pressionando uma tecla (ex.: `q`)
- [x] 1.1.4 Tratar o caso de falha ao abrir a câmera (log claro de erro; é a base do futuro estado `ERRO DE CÂMERA` da RB-03)
- [x] 1.2.1 ~~⚠️ Ponto em aberto~~: modelo da webcam confirmado pelo time — **GoodVision** (registrado no PRD seção 28)
- [x] 1.2.2 ~~⚠️ Ponto em aberto~~: resolução final de captura confirmada pelo time — **1080p / 30 fps** (registrado no PRD seção 28)
- [x] 1.2.3 Posicionar fisicamente a câmera de forma que toda a área da bandeja fique visível (mesmo que a bandeja definitiva ainda não exista, usar um mock/referência de área) — **ação física, requer execução manual pelo time; não pode ser feita por uma IA**
- [x] 1.2.4 Registrar em foto/anotação a posição de referência da câmera para reprodutibilidade futura — **idem, depende de 1.2.3 já ter sido feito fisicamente**
- [x] 1.3.1 Implementar `open_camera(indice_ou_config)` retornando o objeto de captura
- [x] 1.3.2 Implementar `read_frame(camera)` retornando o frame atual (ou erro tratado)
- [x] 1.3.3 Implementar `release_camera(camera)` para liberar o dispositivo corretamente
- [x] 1.3.4 Externalizar o índice/identificador do dispositivo de câmera para `app/config.py` (nada de valores fixos espalhados pelo código)

### Sprint 2 — Ferramenta de captura do dataset (PRD Etapa 2)

- [x] 2.1.1 Reaproveitar `app/camera.py` (sprint 1) para abrir o stream ao vivo
- [x] 2.1.2 Implementar salvamento de frame ao pressionar uma tecla (ex.: `s`)
- [x] 2.1.3 Nomear os arquivos salvos com timestamp/contador incremental, evitando sobrescrita
- [x] 2.1.4 Salvar os frames capturados em `dataset/images/raw/` (pasta de captura bruta, antes do split em train/val/test)
- [x] 2.2.1 Capturar cenas com diferentes quantidades de parafusos (poucos, muitos, próximo do limite da bandeja)
- [x] 2.2.2 Capturar cenas com diferentes quantidades de porcas
- [x] 2.2.3 Capturar cenas misturando parafusos e porcas na mesma imagem
- [x] 2.2.4 Capturar objetos em posições e rotações variadas
- [x] 2.2.5 Capturar objetos próximos entre si e parcialmente encostados
- [x] 2.2.6 Capturar objetos próximos às bordas da bandeja
- [x] 2.2.7 Capturar a bandeja vazia (imagem de referência sem objetos)
- [x] 2.3.1 Acompanhar a contagem de imagens capturadas até atingir a faixa de referência de 200 a 500 imagens (PRD seção 14 — apenas referência inicial, não é limite rígido)
- [x] 2.3.2 Revisar visualmente a diversidade/qualidade das capturas antes de prosseguir para a anotação (priorizar diversidade sobre quantidade)

### Sprint 3 — Organização e anotação do dataset (PRD Etapa 3 / seção 14)

- [x] 3.1.1 ⚠️ Ponto em aberto: decidir com o time a ferramenta de anotação a ser usada (PRD 29.9 — ex.: LabelImg, CVAT, Roboflow ou similar) antes de iniciar a anotação em massa
- [x] 3.1.2 Validar que a ferramenta escolhida exporta rótulos no formato YOLO (`classe x_center y_center width height` normalizado)
- [x] 3.2.1 Anotar bounding box de cada parafuso presente nas imagens (classe `0 = parafuso`)
- [x] 3.2.2 Anotar bounding box de cada porca presente nas imagens (classe `1 = porca`)
- [x] 3.2.3 Revisar por amostragem um subconjunto das anotações para checar consistência de critério entre anotadores (relevante pois há mais de uma pessoa na equipe de visão computacional)
- [x] 3.3.1 Definir a proporção do split (ex.: 70/20/10 — a validar com o time; registrar a decisão)
- [x] 3.3.2 Organizar imagens em `dataset/images/train/`, `dataset/images/val/`, `dataset/images/test/`
- [x] 3.3.3 Organizar rótulos correspondentes em `dataset/labels/train/`, `dataset/labels/val/`, `dataset/labels/test/`
- [x] 3.3.4 Conferir que cada imagem tem exatamente um arquivo de rótulo correspondente (mesmo nome, extensão `.txt`)
- [x] 3.4.1 Definir o campo `path` apontando para a raiz do dataset
- [x] 3.4.2 Mapear `train`, `val`, `test` para as respectivas subpastas
- [x] 3.4.3 Mapear as classes `0: parafuso` e `1: porca` (exatamente como na seção 13.2 do PRD, sem adicionar classes extras)
- [x] 3.4.4 Validar que o `dataset.yaml` carrega sem erros com a biblioteca YOLO escolhida

### Sprint 4 — Primeiro treinamento YOLO (PRD Etapa 4 / seção 13.3–13.4)

- [x] 4.1.1 Instalar as dependências de treinamento (ex.: `ultralytics`) na máquina escolhida para treinar
- [x] 4.1.2 Criar `training/train.py` com os parâmetros de treinamento (modelo base, dataset.yaml, imgsz, épocas)
- [x] 4.2.1 Configurar `imgsz = 640` conforme baseline definido no PRD (seção 21, Etapa 4)
- [x] 4.2.2 Definir número inicial de épocas (valor a ajustar experimentalmente; registrar o valor usado)
- [x] 4.2.3 Executar o treinamento e acompanhar as curvas de loss e métricas (mAP) durante o processo
- [x] 4.2.4 Não escalar para YOLO26s nesta etapa — isso só é permitido após analisar dataset/erros (regra explícita do PRD seção 13.3)
- [x] 4.3.1 Copiar o `best.pt` gerado para `models/`
- [x] 4.3.2 Registrar as métricas de treino obtidas (precisão/recall preliminares) em um log ou anotação para comparação em treinamentos futuros

### Sprint 5 — Validação do modelo treinado (PRD Etapa 5 / seção 24)

- [x] 5.1.1 Garantir que o conjunto de teste (`dataset/images/test/`) não foi usado em nenhum momento do treino
- [x] 5.1.2 Rodar inferência do `best.pt` sobre o conjunto de teste
- [x] 5.1.3 Inspecionar visualmente as detecções (bounding boxes sobrepostas às imagens) em busca de erros óbvios
- [x] 5.2.1 Calcular precisão do modelo
- [x] 5.2.2 Calcular recall do modelo
- [x] 5.2.3 Levantar falsos positivos (objetos detectados que não existem ou classe errada)
- [x] 5.2.4 Levantar falsos negativos (objetos reais não detectados)
- [x] 5.2.5 Calcular erro de contagem (quantidade detectada vs. quantidade real conhecida em cada imagem de teste)
- [x] 5.3.1 Categorizar os erros encontrados por causa provável (oclusão, proximidade da borda, iluminação, objetos encostados)
- [x] 5.3.2 Decidir se é necessário capturar/anotar mais dados de dataset para as categorias com mais erro (retornar à Sprint 2/3 se necessário)
- [x] 5.3.3 Só considerar migrar para YOLO26s depois de esgotar melhorias de dataset, conforme regra do PRD (seção 13.3)

### Sprint 6 — Integração webcam + ROI + YOLO ao vivo (PRD Etapa 6 / seção 15)

- [ ] 6.1.1 Definir as coordenadas fixas da área útil da bandeja (depende da posição física definitiva da câmera — sincronizar com a Sprint 10 se a iluminação/posição definitiva já estiver montada; caso contrário, usar a posição de referência da Sprint 1)
- [x] 6.1.2 Implementar `apply_roi(frame)` retornando apenas a região da bandeja
- [x] 6.1.3 Criar uma ferramenta simples de calibração visual do ROI (ex.: overlay do retângulo de corte sobre o frame ao vivo, ajustável antes de travar os valores)
- [x] 6.1.4 Externalizar as coordenadas do ROI para `app/config.py`
- [x] 6.2.1 Implementar `load_model(caminho_modelo)` carregando o `best.pt` treinado (ou `.onnx`, quando essa decisão for tomada — ver Sprint 11)
- [x] 6.2.2 Implementar `run_inference(frame)` retornando lista de detecções (classe, confiança, bounding box)
- [x] 6.2.3 Externalizar o caminho do modelo para `app/config.py`
- [x] 6.3.1 Implementar o loop principal: captura de frame → aplicação de ROI → inferência → desenho das bounding boxes com classe/confiança
- [x] 6.3.2 Exibir o resultado em uma janela local para validação manual (etapa ainda sem a interface final)
- [ ] 6.4.1 Medir o FPS obtido nesta etapa do pipeline
- [ ] 6.4.2 Medir uso de CPU e RAM durante a execução
- [ ] 6.4.3 Registrar os números como baseline para comparação após otimizações futuras (Sprint 11)

### Sprint 7 — Lógica de contagem (PRD Etapa 7 / RB-01 / RB-02)

- [x] 7.1.1 Implementar `filter_by_class(detections, classe_selecionada)`
- [x] 7.1.2 Garantir que a classe não selecionada seja completamente ignorada na contagem (RB-01 — ex.: se "parafuso" está selecionado, porcas no frame não entram na contagem exibida)
- [x] 7.2.1 Implementar `count_objects(detections_filtradas)` retornando a quantidade inteira detectada
- [x] 7.3.1 Implementar `compare_counts(detectado, esperado)` retornando o estado correspondente
- [x] 7.3.2 Implementar os estados mínimos da máquina de estados: `AGUARDANDO CONFIGURAÇÃO`, `CONTANDO`, `QUANTIDADE ATINGIDA`, `QUANTIDADE EXCEDIDA`
- [x] 7.3.3 Implementar os estados de erro opcionais: `ERRO DE CÂMERA`, `MODELO NÃO CARREGADO` (conectar ao tratamento de erro já iniciado na Sprint 1.1.4)
- [x] 7.4.1 Testar cenário com a quantidade exata de parafusos configurada como alvo
- [x] 7.4.2 Testar cenário misto (parafusos + porcas) validando que a contagem exibida reflete apenas a classe selecionada (reproduzir o exemplo da seção 17 do PRD: 12 parafusos + 4 porcas → exibir 12)
- [x] 7.4.3 Testar transição de estado `AGUARDANDO CONFIGURAÇÃO` → `CONTANDO` → `QUANTIDADE ATINGIDA` OU → `QUANTIDADE EXCEDIDA`

### Sprint 8 — Estabilização da contagem (PRD Etapa 8 / seção 16)

- [x] 8.1.1 Manter um histórico das últimas leituras de contagem por frame
- [x] 8.1.2 Implementar a regra: só transicionar para `QUANTIDADE ATINGIDA` quando a contagem alvo se mantiver por N frames consecutivos
- [x] 8.1.3 Definir N=5 como valor inicial (baseline sugerido na seção 16 do PRD), configurável em `app/config.py`
- [ ] 8.2.1 ⚠️ Ponto em aberto: testar com N=5 e observar se ainda há oscilações de status perceptíveis (PRD 29.8/29.9)
- [ ] 8.2.2 Ajustar o valor de N caso necessário e documentar a decisão final adotada
- [x] 8.3.1 Reiniciar o contador de frames consecutivos sempre que a contagem cair abaixo do valor alvo
- [x] 8.3.2 Reiniciar a estabilização ao trocar a classe selecionada ou a quantidade alvo (evitar herdar histórico de uma configuração anterior)

### Sprint 9 — Interface local (Tkinter) e orquestração

- [x] 9.1.1 Exibir o vídeo ao vivo com as bounding boxes (frame anotado vindo do pipeline)
- [x] 9.1.2 Criar seletor de componente `Parafuso` / `Porca` (somente as duas classes da v1)
- [x] 9.1.3 Criar campo numérico de quantidade desejada, aceitando só inteiros positivos (⚠️ Ponto em aberto: o limite máximo depende da quantidade máxima de componentes suportada, PRD 29.8)
- [x] 9.1.4 Criar botão de reset (RB-05) (⚠️ Ponto em aberto: confirmar com o time o método definitivo de reset, PRD 29.16)
- [x] 9.1.5 Exibir quantidade detectada, quantidade desejada e status textual (`AGUARDANDO CONFIGURAÇÃO` / `CONTANDO` / `QUANTIDADE ATINGIDA` / `QUANTIDADE EXCEDIDA` / estados de erro)
- [ ] 9.1.6 ⚠️ Ponto em aberto: validar com o time o layout final da janela (PRD 29.15)
- [x] 9.2.1 Conectar os módulos `camera`, `detector`, `counter` e `interface`
- [x] 9.2.2 Implementar o loop principal completo: captura → ROI → inferência → filtragem/contagem → estabilização → atualização da interface
- [x] 9.2.3 Garantir que a janela não trave durante a inferência (ex.: processamento em thread separada e atualização da tela via `after` do Tkinter) — escolher a abordagem com base no FPS medido na tarefa 6.4
- [x] 9.2.4 Aplicar em tempo real as mudanças de componente/quantidade feitas na interface, reiniciando a estabilização (tarefa 8.3.2), sem reiniciar a aplicação
- [x] 9.2.5 Liberar a câmera corretamente ao fechar a janela
- [x] 9.3.1 Trocar o componente selecionado e validar que a contagem exibida reflete a mudança
- [x] 9.3.2 Alterar a quantidade desejada e validar a atualização em tempo real
- [x] 9.3.3 Testar o botão de reset e validar que uma nova contagem pode ser iniciada corretamente (RB-05)
- [x] 9.3.4 Desconectar a câmera / remover o modelo e validar que a interface mostra `ERRO DE CÂMERA` / `MODELO NÃO CARREGADO`

### Sprint 10 — Iluminação e ambiente controlado (RNF-01, pode rodar em paralelo às Sprints 1–9)

- [ ] 10.1.1 ⚠️ Ponto em aberto: decidir tipo e posição da iluminação (PRD 29.5)
- [ ] 10.1.2 Fixar a iluminação de forma a minimizar variação de luz ambiente ao longo do dia
- [ ] 10.2.1 Fixar as posições definitivas de câmera, bandeja e iluminação uma em relação à outra
- [ ] 10.2.2 Documentar (foto e/ou medidas) as posições definitivas para permitir remontagem idêntica no futuro

### Sprint 11 — Integração completa no computador final (PRD Etapa 11 / seção 22)

- [ ] 11.1.1 ⚠️ Ponto em aberto: confirmar a especificação do computador final de produção (PRD 29.13)
- [ ] 11.1.2 Instalar no computador final apenas as dependências necessárias para inferência (sem as dependências de treino, que só existem na máquina de treinamento)
- [x] 11.1.3.1 Build PyInstaller one-folder (`instalador/contador_componentes.spec` + `instalador/build.ps1`, venv de build só com dependências de inferência; roda os testes antes; gera zip e, com Inno Setup, `Instalar_ContadorComponentes.exe`)
- [x] 11.1.3.2 Modelo (`models/best.pt`) fora do executável, trocável sem rebuild; `camera_index`/`roi` editáveis em `config_local.json`; calibração de ROI no PC final via `ContadorComponentes.exe --calibrar-roi`
- [ ] 11.1.3.3 Instalar e abrir o pacote no PC final real, com a webcam (depende de 11.1.1 e da pendência 1 — modelo final — do `PENDENCIAS_HUMANAS.md`)
- [ ] 11.2.1 Copiar o `best.pt` validado (Sprint 5) para o computador final
- [ ] 11.2.2 Avaliar exportação para `best.onnx` como possível otimização (PRD seção 22)
- [ ] 11.2.3 ⚠️ Ponto em aberto: decidir o formato final entre `.pt` e `.onnx` com base em testes reais de desempenho no hardware final (PRD 29.14)
- [ ] 11.3.1 Medir FPS no computador final
- [ ] 11.3.2 Medir latência ponta a ponta (captura → contagem → atualização na interface)
- [ ] 11.3.3 Medir uso de CPU, RAM e GPU (quando aplicável)
- [ ] 11.3.4 Se o desempenho for insuficiente: reduzir resolução de captura, ajustar FPS-alvo, ou otimizar a inferência (nessa ordem de prioridade, conforme PRD seção 21)
- [ ] 11.4.1 Conectar a webcam ao computador final
- [ ] 11.4.2 Integrar a iluminação definitiva (Sprint 10) à posição da câmera
- [ ] 11.4.3 Validar cabeamento, alimentação elétrica e posicionamento final de todos os componentes físicos

### Sprint 12 — Testes finais e critérios de aceitação (PRD seção 23)

- [ ] 12.1.1 A webcam captura toda a bandeja de maneira estável
- [ ] 12.1.2 O usuário consegue selecionar `Parafuso` ou `Porca` na interface local
- [ ] 12.1.3 O usuário consegue definir uma quantidade alvo na interface local
- [ ] 12.1.4 O modelo identifica corretamente os componentes em condições normais de uso
- [ ] 12.1.5 A aplicação conta apenas a classe selecionada (RB-01)
- [ ] 12.1.6 A quantidade detectada aparece corretamente na interface local
- [ ] 12.1.7 O status muda para `QUANTIDADE ATINGIDA` quando o alvo é alcançado
- [ ] 12.1.8 O vídeo da bandeja pode ser visualizado ao vivo na interface local
- [ ] 12.2.1 Executar o cenário de uso de referência completo (PRD seção 8: selecionar Parafuso, alvo 20, acompanhar contagem até `QUANTIDADE ATINGIDA`)
- [ ] 12.2.2 Repetir o ciclo completo (contagem → retirada manual das peças → reset → nova contagem) múltiplas vezes seguidas para checar estabilidade
- [ ] 12.2.3 Testar o cenário de troca de classe selecionada no meio de uma sessão (ex.: trocar de Parafuso para Porca) e validar que a contagem e a estabilização reiniciam corretamente

### Sprint 13 — Documentação final e encerramento do MVP

- [ ] 13.1.1 Documentar, para cada ponto em aberto da seção 29 do PRD, qual foi a decisão final tomada
- [ ] 13.1.2 Atualizar o `README.md` do projeto com instruções de instalação, configuração e uso do protótipo final
- [ ] 13.2.1 Registrar as métricas finais obtidas (IA: precisão/recall; aplicação: FPS/latência) em um documento de fechamento do MVP
- [ ] 13.2.2 Priorizar, junto ao time, quais expansões futuras da seção 30 do PRD (ex.: arruelas, múltiplas classes, histórico) fazem sentido buscar em uma próxima versão
