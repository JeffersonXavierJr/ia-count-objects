# Validacao no split test (Sprint 5)

Registro simples (sem banco de dados) da validacao em fotos nunca vistas no
treino (PRD secao 21, Etapa 5; metricas da secao 24). Os numeros detalhados
ficam nos JSON dentro de `runs/sprint5/<modelo>/` (fora do Git, como todo
`runs/`).

Modelos comparados:

- **A** — baseline, `models/best.pt` (run `yolo26n_baseline`, dataset antigo:
  train 199 / val 57, so sessoes `frame_20260923_*` e `frame_20260930_*`).
- **B** — `runs/yolo26n_porcas_v2/weights/best.pt`, dataset ampliado com mais
  porcas (train 339 / val 96). Treino **interrompido na epoca 58/100** — nao e
  o modelo final.

Split test atual: 47 imagens 640x640 (as 28 do test antigo + 12
`frame_20261021_*` + 7 fotos WhatsApp). 2 imagens sao fundo sem objeto
(`frame_20260930_210535`, `frame_20261021_202710_002`).

## 5.1 Isolamento do test e inspecao visual

Inferencia: `training/avaliar_teste.py` (conf bruta 0.01, imgsz 640) ->
`runs/sprint5/<modelo>/predicoes.json` + `visual/`.

Isolamento:
- Nenhum arquivo do test esta em train/val (dataset atual). As 28 imagens do
  test antigo continuam no test; nenhuma imagem do test atual estava no
  train/valid antigo (`treinamento_yolo/`), entao o modelo A tambem nunca as viu.
- **Vazamento por rajada**: quase todas as imagens do test tem foto da mesma
  rajada (<= 2 s) em train/val. Grupos usados nas metricas (recalculados de
  forma deterministica pelo `metricas_teste.py`: vizinho temporal <= 2 s pelo
  nome do arquivo + dHash 256 bits, Hamming <= 30 = quase identica), em
  relacao ao train/val ATUAL (o do modelo B):
  - **independente (10)**: 9 `frame_20260930_*` sem vizinho <= 2 s +
    `frame_20261021_202334`;
  - **risco forte (18)**: 15 `frame_20260923_*` (todas menos `_205137_004` e
    `_205623_004`), `frame_20261021_202445_001`, `_202710_002`, `_202827`;
  - **risco moderado (19)**: `frame_20260923_205137_004`, `_205623_004`,
    `frame_20260930_205846`, `_210535`, 8 `frame_20261021_*`, as 7 WhatsApp.
  - Diferenca para a contagem da 5.1 (10/19/18): no recalculo
    `frame_20260930_210535` deu Hamming 56 (moderado, e e imagem de fundo) e
    `frame_20261021_202827` deu Hamming 10 (forte). A descricao da 5.1 tambem
    citava "16" `frame_20260923_*`, mas a regra "todas exceto duas" da 15.
    Valem os grupos recalculados (gravados em `metricas.json`, chave `grupos`).
  - **Atencao para A**: em relacao ao dataset ANTIGO, todas as 19 imagens
    novas (`frame_20261021_*` e WhatsApp) sao sessoes que A nunca viu. So o
    grupo "independente" e justo para os dois modelos ao mesmo tempo; nos
    grupos de risco o modelo B fica favorecido.

Erros visuais (conf 0.5):
- A falha nas fotos WhatsApp (camera/enquadramento diferentes) — quase nenhuma
  porca detectada — e conta pontas de chave/bits como parafuso
  (`frame_20261021_*`).
- Os dois modelos erram objetos encostados/empilhados; B e pior em
  `frame_20260930_205846`, `_204816` e `_210437`.
- A gera caixas duplicadas em parafusos sobrepostos.
- Label suspeito de incompleto: `WhatsApp-Image-2026-10-22-at-19-40-31`
  (3 porcas e 1 parafuso preto sem anotacao). NAO corrigido; tratado como
  ressalva abaixo.

## 5.2 Metricas de IA (A x B)

Como foi calculado (`training/metricas_teste.py`):
- conf >= 0.5 (`config.CONFIDENCE_THRESHOLD`, valor inicial **nao decidido**),
  IoU >= 0.5, mesma classe, matching guloso por confianca (NMS ja feito pelo
  ultralytics).
- FP separados em: classe errada (casa com GT de outra classe, IoU >= 0.5),
  duplicata (casa com GT da mesma classe ja usado) e inexistente (nao casa
  com nada: objeto que nao existe ou caixa mal localizada).
- Erro de contagem = |n previsto - n real| por imagem e por classe, so pela
  contagem de caixas (e o que a aplicacao usa, RB-01).
- AP50/AP50-95 proprios (estilo ultralytics, sobre as predicoes brutas,
  para poder separar por grupo) — aproximam o oficial (tabela no fim).
- Comandos (raiz do repo):
  `venv\Scripts\python.exe contador_componentes/training/metricas_teste.py contador_componentes/training/runs/sprint5/<modelo>/predicoes.json --com-map`

### Resumo (conf 0.5)

| Conjunto | Classe | P A | P B | R A | R B | MAE cont. A | MAE cont. B | % exata A | % exata B |
|---|---|---|---|---|---|---|---|---|---|
| total (47) | parafuso | 0,907 | 0,991 | 0,941 | 0,920 | 0,49 | 0,40 | 72,3 | 83,0 |
| total (47) | porca | 0,904 | 0,933 | 0,356 | 0,955 | 1,83 | 0,19 | 68,1 | 85,1 |
| total (47) | geral | 0,906 | 0,969 | 0,732 | 0,932 | | | | |
| independente (10) | parafuso | 0,926 | 0,986 | 0,893 | 0,821 | 0,70 | 1,40 | 50,0 | 40,0 |
| independente (10) | porca | 0,880 | 0,920 | 0,815 | 0,852 | 0,40 | 0,20 | 70,0 | 80,0 |
| independente (10) | geral | 0,915 | 0,968 | 0,874 | 0,829 | | | | |

### 5.2.1 / 5.2.2 Precisao e recall (e AP) por grupo

| Grupo | Classe | Modelo | GT | TP | FP | FN | Precisao | Recall | AP50 | AP50-95 |
|---|---|---|---|---|---|---|---|---|---|---|
| total (47) | parafuso | A | 238 | 224 | 23 | 14 | 0,907 | 0,941 | 0,968 | 0,832 |
| total (47) | parafuso | B | 238 | 219 | 2 | 19 | 0,991 | 0,920 | 0,981 | 0,826 |
| total (47) | porca | A | 132 | 47 | 5 | 85 | 0,904 | 0,356 | 0,710 | 0,588 |
| total (47) | porca | B | 132 | 126 | 9 | 6 | 0,933 | 0,955 | 0,984 | 0,879 |
| total (47) | geral | A | 370 | 271 | 28 | 99 | 0,906 | 0,732 | 0,839 | 0,710 |
| total (47) | geral | B | 370 | 345 | 11 | 25 | 0,969 | 0,932 | 0,983 | 0,853 |
| independente (10) | parafuso | A | 84 | 75 | 6 | 9 | 0,926 | 0,893 | 0,962 | 0,722 |
| independente (10) | parafuso | B | 84 | 69 | 1 | 15 | 0,986 | 0,821 | 0,947 | 0,681 |
| independente (10) | porca | A | 27 | 22 | 3 | 5 | 0,880 | 0,815 | 0,959 | 0,792 |
| independente (10) | porca | B | 27 | 23 | 2 | 4 | 0,920 | 0,852 | 0,951 | 0,776 |
| independente (10) | geral | A | 111 | 97 | 9 | 14 | 0,915 | 0,874 | 0,960 | 0,757 |
| independente (10) | geral | B | 111 | 92 | 3 | 19 | 0,968 | 0,829 | 0,949 | 0,729 |
| risco forte (18) | parafuso | A | 119 | 119 | 3 | 0 | 0,975 | 1,000 | 0,995 | 0,921 |
| risco forte (18) | parafuso | B | 119 | 119 | 1 | 0 | 0,992 | 1,000 | 0,988 | 0,895 |
| risco forte (18) | porca | A | 4 | 4 | 1 | 0 | 0,800 | 1,000 | 0,895 | 0,846 |
| risco forte (18) | porca | B | 4 | 4 | 0 | 0 | 1,000 | 1,000 | 0,995 | 0,947 |
| risco forte (18) | geral | A | 123 | 123 | 4 | 0 | 0,969 | 1,000 | 0,945 | 0,884 |
| risco forte (18) | geral | B | 123 | 123 | 1 | 0 | 0,992 | 1,000 | 0,991 | 0,921 |
| risco moderado (19) | parafuso | A | 35 | 30 | 14 | 5 | 0,682 | 0,857 | 0,821 | 0,704 |
| risco moderado (19) | parafuso | B | 35 | 31 | 0 | 4 | 1,000 | 0,886 | 0,982 | 0,841 |
| risco moderado (19) | porca | A | 101 | 21 | 1 | 80 | 0,955 | 0,208 | 0,680 | 0,560 |
| risco moderado (19) | porca | B | 101 | 99 | 7 | 2 | 0,934 | 0,980 | 0,991 | 0,902 |
| risco moderado (19) | geral | A | 136 | 51 | 15 | 85 | 0,773 | 0,375 | 0,751 | 0,632 |
| risco moderado (19) | geral | B | 136 | 130 | 7 | 6 | 0,949 | 0,956 | 0,986 | 0,872 |

mAP oficial do ultralytics (`YOLO.val(split='test')`, conf 0.001, so total):

| Modelo | P | R | mAP50 | mAP50-95 | AP50 parafuso | AP50 porca |
|---|---|---|---|---|---|---|
| A | 0,791 | 0,761 | 0,827 | 0,683 | 0,967 | 0,687 |
| B | 0,957 | 0,948 | 0,981 | 0,837 | 0,979 | 0,983 |

(P/R do ultralytics usam o ponto de F1 maximo, nao conf 0.5 — por isso
diferem da tabela acima.)

### 5.2.3 Falsos positivos

| Grupo | Classe | Modelo | FP | classe errada | duplicata | inexistente |
|---|---|---|---|---|---|---|
| total | parafuso | A | 23 | 0 | 1 | 22 |
| total | parafuso | B | 2 | 0 | 0 | 2 |
| total | porca | A | 5 | 1 | 0 | 4 |
| total | porca | B | 9 | 0 | 0 | 9 |
| independente | parafuso | A | 6 | 0 | 1 | 5 |
| independente | parafuso | B | 1 | 0 | 0 | 1 |
| independente | porca | A | 3 | 1 | 0 | 2 |
| independente | porca | B | 2 | 0 | 0 | 2 |
| risco forte | parafuso | A | 3 | 0 | 0 | 3 |
| risco forte | parafuso | B | 1 | 0 | 0 | 1 |
| risco forte | porca | A | 1 | 0 | 0 | 1 |
| risco forte | porca | B | 0 | 0 | 0 | 0 |
| risco moderado | parafuso | A | 14 | 0 | 0 | 14 |
| risco moderado | parafuso | B | 0 | 0 | 0 | 0 |
| risco moderado | porca | A | 1 | 0 | 0 | 1 |
| risco moderado | porca | B | 7 | 0 | 0 | 7 |

Imagens com mais FP:
- A: `frame_20261021_202334` (4), `_202525` (4), `_202445_001` (3),
  `_202458_001` (3), `_202749` (3) — pontas de chave/bits contadas como parafuso.
- B: `WhatsApp-...-19-40-31` (3, provavelmente as porcas sem label), `-19-40-32` (2),
  `frame_20260930_204816`, `_205043`, `_205151` (1 cada).

Confusao de classe e quase inexistente (1 caso em A). Os FP "inexistente"
incluem caixas mal localizadas em objetos encostados (IoU < 0.5).

### 5.2.4 Falsos negativos

| Grupo | Classe | FN A | FN B |
|---|---|---|---|
| total | parafuso | 14 | 19 |
| total | porca | 85 | 6 |
| independente | parafuso | 9 | 15 |
| independente | porca | 5 | 4 |
| risco forte | parafuso | 0 | 0 |
| risco forte | porca | 0 | 0 |
| risco moderado | parafuso | 5 | 4 |
| risco moderado | porca | 80 | 2 |

Imagens com mais FN:
- A: WhatsApp `21-59-24-4-` (18), `19-40-22` (14), `19-40-32` (13),
  `19-40-31` (11), `21-59-23-2-` (11) — porcas das fotos WhatsApp.
- B: `frame_20260930_204816` (5), `_205043` (5), `_205846` (5), `_210437` (3),
  `_205151` (2) — parafusos encostados/empilhados.

### 5.2.5 Erro de contagem (so contagem, RB-01)

| Grupo | Classe | Modelo | MAE | % exata | erro medio c/ sinal | maior erro (imagem) |
|---|---|---|---|---|---|---|
| total | parafuso | A | 0,49 | 72,3 | +0,19 | +3 (frame_20261021_202445_001) |
| total | parafuso | B | 0,40 | 83,0 | -0,36 | -4 (frame_20260930_204816) |
| total | porca | A | 1,83 | 68,1 | -1,70 | -18 (WhatsApp-...-21-59-24-4-) |
| total | porca | B | 0,19 | 85,1 | +0,06 | +3 (WhatsApp-...-19-40-31) |
| independente | parafuso | A | 0,70 | 50,0 | -0,30 | -2 (frame_20260930_204816) |
| independente | parafuso | B | 1,40 | 40,0 | -1,40 | -4 (frame_20260930_204816) |
| independente | porca | A | 0,40 | 70,0 | -0,20 | -2 (frame_20260930_210024) |
| independente | porca | B | 0,20 | 80,0 | -0,20 | -1 (frame_20260930_205151) |
| risco forte | parafuso | A | 0,17 | 94,4 | +0,17 | +3 (frame_20261021_202445_001) |
| risco forte | parafuso | B | 0,06 | 94,4 | +0,06 | +1 (frame_20261021_202445_001) |
| risco forte | porca | A | 0,06 | 94,4 | +0,06 | +1 (frame_20261021_202827) |
| risco forte | porca | B | 0,00 | 100,0 | +0,00 | 0 |
| risco moderado | parafuso | A | 0,68 | 63,2 | +0,47 | +3 (frame_20261021_202525) |
| risco moderado | parafuso | B | 0,21 | 94,7 | -0,21 | -4 (frame_20260930_205846) |
| risco moderado | porca | A | 4,26 | 42,1 | -4,16 | -18 (WhatsApp-...-21-59-24-4-) |
| risco moderado | porca | B | 0,37 | 73,7 | +0,26 | +3 (WhatsApp-...-19-40-31) |

"% exata" conta tambem imagens sem nenhum objeto da classe (0 = 0).
Erro com sinal negativo = conta a menos.

### Extra: limiar de confianca x contagem (% exata / MAE)

Apenas referencia para calibrar o limiar depois — **nada decidido aqui**
(o 0.5 continua sendo valor inicial).

| Grupo | conf | A parafuso | A porca | B parafuso | B porca |
|---|---|---|---|---|---|
| total | 0,25 | 61,7 / 0,89 | 63,8 / 1,68 | 85,1 / 0,28 | 83,0 / 0,26 |
| total | 0,35 | 72,3 / 0,68 | 68,1 / 1,77 | 87,2 / 0,15 | 87,2 / 0,19 |
| total | 0,5 | 72,3 / 0,49 | 68,1 / 1,83 | 83,0 / 0,40 | 85,1 / 0,19 |
| total | 0,6 | 70,2 / 0,57 | 68,1 / 1,85 | 78,7 / 0,53 | 87,2 / 0,19 |
| total | 0,7 | 78,7 / 0,62 | 70,2 / 1,87 | 78,7 / 0,77 | 89,4 / 0,23 |
| independente | 0,25 | 50,0 / 0,80 | 60,0 / 0,50 | 40,0 / 1,20 | 80,0 / 0,30 |
| independente | 0,35 | 70,0 / 0,40 | 80,0 / 0,30 | 50,0 / 0,60 | 90,0 / 0,10 |
| independente | 0,5 | 50,0 / 0,70 | 70,0 / 0,40 | 40,0 / 1,40 | 80,0 / 0,20 |
| independente | 0,6 | 40,0 / 1,10 | 70,0 / 0,40 | 30,0 / 1,90 | 80,0 / 0,30 |
| independente | 0,7 | 50,0 / 1,70 | 80,0 / 0,30 | 30,0 / 2,90 | 80,0 / 0,60 |
| risco forte | 0,25 | 88,9 / 0,44 | 94,4 / 0,33 | 94,4 / 0,06 | 94,4 / 0,06 |
| risco forte | 0,35 | 88,9 / 0,39 | 94,4 / 0,28 | 94,4 / 0,06 | 100,0 / 0,00 |
| risco forte | 0,5 | 94,4 / 0,17 | 94,4 / 0,06 | 94,4 / 0,06 | 100,0 / 0,00 |
| risco forte | 0,6 | 94,4 / 0,17 | 94,4 / 0,06 | 94,4 / 0,06 | 100,0 / 0,00 |
| risco forte | 0,7 | 94,4 / 0,11 | 94,4 / 0,06 | 94,4 / 0,06 | 100,0 / 0,00 |
| risco moderado | 0,25 | 42,1 / 1,37 | 36,8 / 3,58 | 100,0 / 0,00 | 73,7 / 0,42 |
| risco moderado | 0,35 | 57,9 / 1,11 | 36,8 / 3,95 | 100,0 / 0,00 | 73,7 / 0,42 |
| risco moderado | 0,5 | 63,2 / 0,68 | 42,1 / 4,26 | 94,7 / 0,21 | 73,7 / 0,37 |
| risco moderado | 0,6 | 63,2 / 0,68 | 42,1 / 4,32 | 89,5 / 0,26 | 78,9 / 0,32 |
| risco moderado | 0,7 | 78,9 / 0,53 | 42,1 / 4,42 | 89,5 / 0,32 | 84,2 / 0,26 |

O grupo independente tem so 10 imagens: 1 imagem = 10 pontos percentuais.

### Ressalva: label incompleto `WhatsApp-...-19-40-31`

Sem essa imagem (46 imagens, `--excluir 19-40-31`), conf 0.5:
- B porca: P 0,933 -> 0,950; MAE 0,19 -> 0,13; % exata 85,1 -> 87,0; maior
  erro +3 -> -1. Os 3 FP de porca de B nessa imagem sao provavelmente as
  porcas sem anotacao (acertos, nao erros).
- A porca: R 0,356 -> 0,388; MAE 1,83 -> 1,63 (A nao detecta nada nessa foto).
- Parafuso: praticamente igual nos dois.
Saida: `runs/sprint5/<modelo>/metricas_sem_19-40-31.json`.

### Achados principais (5.2)

1. **Porca**: B resolve o problema principal de A (recall 0,356 -> 0,955; MAE
   de contagem 1,83 -> 0,19). Mas 101 das 132 porcas estao no grupo de risco
   moderado (WhatsApp/`frame_20261021`), onde B tem fotos da mesma rajada no
   treino e A nunca viu a sessao. No grupo independente o ganho e pequeno
   (recall 0,815 -> 0,852; 27 porcas). O ganho real de B em porca esta
   provavelmente superestimado.
2. **Parafuso**: no grupo independente **B piora** (recall 0,893 -> 0,821; MAE
   0,70 -> 1,40; % exata 50 -> 40), concentrado em objetos
   encostados/empilhados (`frame_20260930_204816`, `_205043`, `_205846`,
   `_210437`). B conta a menos; A conta a mais (FP em pontas de chave/bits).
   B parou na epoca 58/100 — pode nao ter convergido.
3. **Risco forte** (fotos quase identicas a train/val): os dois ficam perto de
   100% — esse grupo mede memorizacao, nao generalizacao.
4. Confusao parafuso <-> porca praticamente nao ocorre; os erros sao de
   deteccao (perder/inventar objeto) e de localizacao em objetos encostados.
5. Pela varredura, o limiar ideal parece diferente por classe/modelo (B
   parafuso prefere conf mais baixa; B porca, mais alta), mas com 10 imagens
   independentes nao da para decidir — fica para a 5.3 / testes ao vivo.

## 5.3 Proximos passos com base nos erros

### 5.3.1 Categorizacao dos erros (conf 0.5, IoU 0.5)

Metodo: cada FP/FN do matching da 5.2 (mesmo `casar()` do
`metricas_teste.py`) foi listado com IoU contra o GT, distancia da borda e
interseccao com outras caixas, e classificado olhando a imagem. Imagens com
os erros marcados (FP vermelho, FN amarelo, TP cinza; 1,5x) e zooms:
`runs/sprint5/erros/{A,B}_<imagem>.jpg` e `zoom_*.jpg` (fora do Git).
Cada erro recebe UMA categoria (a principal).

| Categoria | FP A | FN A | FP B | FN B | Imagens exemplo |
|---|---|---|---|---|---|
| Oclusao/sobreposicao (pilha, parafuso cruzado, porca rosqueada no parafuso, mao) | 3 | 9 | 2 | 16 | `frame_20260930_205043` (pilha em estrela: B 5 FN), `_204816`, `_205846` (parafuso apoiado sobre porca; porca na mao), `_205151` (porca no parafuso) |
| Proximidade da borda | 0 | 2 | 0 | 1 | `frame_20260930_204816` (parafuso cortado na esquerda, A), `_205151` (porca na borda inferior) |
| Iluminacao/reflexo | 0 | 2 | 0 | 0 | `frame_20261021_202458_001`, `_202525` (porca pequena saturada/branca, A) |
| Objetos encostados (lado a lado, sem sobrepor) | 0 | 7 | 0 | 6 | `frame_20260930_210437` (parafusos paralelos), `_210643`, `_210024` (porca+parafuso), `frame_20261021_202525` (parafuso encostado no bit, A) |
| Objeto estranho nao anotado (bits, chave, abridor) | 19 | 0 | 0 | 0 | `frame_20261021_202525` (4), `_202334`, `_202445_001`, `_202458_001` (3 cada), `_202905`, `_202922` (2), `_202903`, `_202749` (abridor "sodexo") |
| Outra camera/dominio (WhatsApp) | 0 | 77 | 0 | 0 | as 7 WhatsApp (A detecta quase nenhuma porca; ex. `21-59-24-4-` 18 FN) |
| Erro/omissao de label (predicao correta, GT faltando) | 5 | 0 | 9 | 0 | `WhatsApp-...-19-40-31` (B 3), `-19-40-32` (B 2), `-19-40-22`, `frame_20260930_205151`, `frame_20261021_202749`, `_202827`, `_202445_001` |
| Outro (pose incomum / tipo pouco visto) | 1 | 2 | 0 | 2 | `frame_20261021_202334` (parafuso preto visto de topo -> A diz porca), `_202458_001` (parafuso de cabeca redonda, A), `frame_20260930_210437` (parafuso pequeno, baixo contraste, B), `WhatsApp-...-19-40-32` (porca "em pe", B) |
| **Total** | **28** | **99** | **11** | **25** | |

Leitura:
- **A**: 96 de 127 erros (76%) sao dominio WhatsApp (77 FN de porca) ou
  objetos estranhos (19 FP). Sao falta de cobertura do dataset antigo, que o
  dataset de B ja corrigiu (B: 0 nas duas categorias).
- **B**: 22 dos 25 FN sao objetos sobrepostos/encostados (todos os 19 FN de
  parafuso estao em `frame_20260930_*`, cenas com pilhas). 9 dos 11 FP **nao sao
  erros do modelo**: sao objetos reais sem label (8 porcas + 1 parafuso).
- Em 18 dos 25 FN de B existe predicao da classe certa com IoU >= 0,5 e conf
  entre 0,10 e 0,49 (12 com conf >= 0,25): o modelo acha o objeto, mas sem
  confianca suficiente. Em A isso vale para 37 de 99.
- Estimativa com os labels corrigidos (sem re-rodar): B porca P 0,933 ->
  ~0,99; B parafuso FP 2 -> 1. Precisa ser confirmado depois da correcao.

Labels incompletos encontrados (objeto real sem anotacao; NAO corrigidos):

| Arquivo (test) | Faltando | Posicao aprox. (px, 640x640) |
|---|---|---|
| `WhatsApp-Image-2026-10-22-at-19-40-31` | 3 porcas (+1 parafuso preto, ja citado na 5.1) | (267,291), (210,299), (306,223) |
| `WhatsApp-Image-2026-10-22-at-19-40-32` | 2 porcas | (393,187) porca preta; (562,256) porca flangeada |
| `WhatsApp-Image-2026-10-22-at-19-40-22` | 1 porca | (264,404) porca preta flangeada |
| `frame_20260930_205151` | 2 porcas rosqueadas | (234,362) no 2o parafuso; (334,205) no topo do 4o parafuso |
| `frame_20261021_202749` | 2 porcas | (230,306) porca quadrada; (350,32) porca cortada na borda superior |
| `frame_20261021_202827` | 1 porca (castelo) + verificar objeto quadrado cinza | (221,89); objeto em ~(220,355) |
| `frame_20261021_202445_001` | 1 parafuso (encostado no bit) | (276,422) — o mesmo parafuso esta anotado em `_202525` |

Os mesmos tipos (porca quadrada, castelo, flangeada preta, porca rosqueada
no parafuso) provavelmente estao sem label tambem nas fotos vizinhas da
mesma rajada em train/val.

### 5.3.2 Recomendacao (decisao final do time)

Ordem sugerida:

1. **Corrigir labels primeiro** (barato, afeta metricas e treino): os 7
   arquivos da tabela acima e uma auditoria das fotos de train/val das
   mesmas rajadas (`WhatsApp-...-19-40-*`, `frame_20261021_2027*`/`_2028*`,
   `frame_20260930_2051*`, `frame_20261021_2024*`). Definir e registrar a
   regra de anotacao: toda porca/parafuso visivel conta (inclusive quadrada,
   castelo, flangeada, rosqueada no parafuso, parcialmente coberta ou
   cortada na borda — a partir de qual % visivel e decisao do time, ligada a
   regra de contagem na borda do ROI).
2. **Terminar o treino B** (retomar de `last.pt` ate 100 epocas) depois da
   correcao de labels **so se** a correcao for pequena; se a auditoria mudar
   muitos labels de train/val, e melhor um treino novo com o dataset
   corrigido (o resume reusa o dataset atual pelo caminho do yaml, mas os
   pesos ja aprenderam os labels errados por 58 epocas). Motivo para nao
   parar em 58: mAP50-95 de val ainda subia devagar (0,815 na ep 25 ->
   0,845 na ep 52), o LR nao decaiu ate o final e as 10 ultimas epocas sem
   mosaic (`close_mosaic: 10`) nao aconteceram. Para caber na memoria:
   `resume=True` aceita sobrescrever `batch`, `workers` e `cache`
   (conferido na doc do ultralytics), ex.:
   `YOLO("contador_componentes/training/runs/yolo26n_porcas_v2/weights/last.pt").train(resume=True, batch=8, workers=2)`.
   Nao executado. O `train.py` atual nao tem opcao de resume.
3. **Capturar/anotar mais dados** (de preferencia ja com a webcam e a
   bandeja do prototipo, em sessoes novas):

| Categoria | Prioridade | Imagens aprox. | O que capturar |
|---|---|---|---|
| Sobreposicao/oclusao + encostados | alta (22/25 FN de B) | 80-120 | pilhas pequenas, parafusos cruzados/paralelos encostados, porca rosqueada no parafuso, parafuso apoiado na porca, porca encostada em parafuso; 5 a 35 pecas |
| Borda do ROI | media | 20-30 | pecas parcialmente fora do ROI/bandeja (depende da regra de borda) |
| Poses incomuns | media | 20-30 | porca em pe/de lado, parafuso visto de topo, parafusos pequenos e de cabeca redonda |
| Iluminacao/reflexo | baixa (so A) | 20-30 | variacao de luz e pecas pequenas brilhantes, quando a iluminacao final for definida |
| Dominio (outra camera) | baixa | 0 extra | B ja resolveu; o que importa e a camera de producao |

   Total: ~150-200 imagens novas, aumentando a base em ~35-45%.
4. **Bits, chaves, abridor e outros objetos**: manter como **imagens/regioes
   sem anotacao (negativos/fundo)** — sem classe nova (PRD so permite
   parafuso e porca na v1). B ja aprendeu a ignorar bits (0 FP) com as
   fotos `frame_20261021_*` onde eles aparecem sem label; recomendo +20-40
   imagens com objetos que nao sao parafuso/porca (so eles, label vazio, e
   misturados com pecas reais), mantendo fundo puro em ~5-10% do train
   (hoje sao 10 labels vazios em 339).
5. **Reorganizar o split por sessao/rajada** (nao executado): hoje 46/47
   imagens do test tem foto da mesma rajada em train/val; so 10 sao
   independentes. Proposta: agrupar por rajada (timestamp do nome <= 2 s /
   dHash, como em `metricas_teste.py`) e sortear grupos inteiros para
   train/val/test; melhor ainda, reservar **uma sessao de captura inteira e
   nova** (na webcam/bandeja finais) so para test, com ~40-60 imagens. Com
   o split atual, a metrica de test superestima o modelo (grupo "risco
   forte" ~100%). Depois de reorganizar, comparar A e B de novo no test
   independente antes de trocar o `models/best.pt`.

### 5.3.3 YOLO26s: NAO migrar agora

Decisao registrada: **continua YOLO26n** (PRD 13.3: so escalar depois de
esgotar as melhorias de dataset). Os dados **confirmam** que os erros
dominantes sao de dataset/label/dominio, nao de capacidade:

- A: 76% dos erros sao dominio WhatsApp ou objeto estranho, e o **mesmo
  YOLO26n** treinado com mais dados (B) zerou essas duas categorias.
- B: 9 dos 11 FP sao omissao de label (o modelo estava certo).
- B: os FN se concentram em sobreposicao/encostados, que estao
  sub-representados; em 18/25 FN o modelo ja localiza o objeto com conf
  0,10-0,49 (falta de exemplos/treino, nao de capacidade).
- No grupo independente o YOLO26n A teve **menos** FN de parafuso (9) que B
  (15), com a mesma arquitetura: a piora de B vem do treino incompleto
  (58/100) e/ou da mistura do dataset, nao do tamanho do modelo.
- Ressalva (nao refuta, mas fica registrada): pilhas densas sao dificeis
  para qualquer detector de caixas (caixas de GT com IoU ate 0,46 entre si).
  Se apos dataset corrigido/ampliado e treino completo os FN em pilhas
  continuarem, avaliar primeiro a regra operacional (espalhar as pecas na
  bandeja) e so depois YOLO26s; segmentacao nao e indicada por estes dados
  e, se cogitada, deve ser levada ao time antes.

Criterio para reabrir a questao do YOLO26s: dataset com labels corrigidos +
dados novos de sobreposicao + split por sessao + treino completo, e ainda
assim recall de parafuso no test independente abaixo do aceitavel.
