# Relatório — Validação experimental do N de estabilização (tarefa 8.2)

- Data: 2026-10-28
- Escopo: Sprint 8, tarefa 8.2 do `TASKS.md` / PRD seção 16.
- Script: `contador_componentes/scripts/avaliar_estabilizacao.py`
- Testes automatizados da simulação: `contador_componentes/tests/test_avaliar_estabilizacao.py`
- **Status: evidência OFFLINE preliminar. A tarefa 8.2 NÃO está fechada.** O valor de N
  continua `FRAMES_ESTABILIZACAO = 5` em `app/config.py` (não alterado). A decisão final de
  N e do método de estabilização é do **time**: é ponto em aberto do PRD, seção 29
  (itens "8. método final de estabilização" e "9. número de frames para confirmação").

> Observação: a referência no `TASKS.md` (8.2.1) foi corrigida de "PRD 29.10/29.11" para "PRD 29.8/29.9".

---

## 1. Método

1. A contagem **bruta** por frame (detector → `filter_by_class` → `count_objects`) é obtida
   uma única vez e a MESMA sequência é reprocessada por um `EstabilizadorContagem(N)` para
   cada N ∈ {1, 3, 5, 8, 10}. N=1 equivale a não estabilizar.
2. Fonte offline: frames em rajada do dataset (nomes `frame_AAAAMMDD_HHMMSS[_NNN]`),
   ordenados como vídeo (timestamp + sufixo) e agrupados em **cenas**: frames consecutivos
   com ≤ 1 s de intervalo e o mesmo ground truth (contagem do label YOLO). Cenas com < 3
   frames foram descartadas. Cada (cena × classe presente) é uma sequência.
3. Alvo: `alvo = GT` (ATINGIDA é o estado correto) e dois cenários de **ATINGIDA falsa**:
   `alvo = GT+1` (bandeja com uma peça a menos que o alvo) e `alvo = GT−1` (uma a mais).
4. Métricas por N: mudanças de estado; entradas e saídas de `QUANTIDADE ATINGIDA`
   (saída = "piscada"); entradas em `EXCEDIDA`; latência até a 1ª ATINGIDA (frames e
   segundos = frames/FPS); nº de sequências **elegíveis** (com ≥ N frames — uma sequência
   mais curta que N nunca pode atingir).
5. Execuções (CPU, sem treino, uma imagem por vez):
   - (A) `images/train+val+test` (640×640, redimensionadas pelo Roboflow) — 412 frames
     `frame_*` com label + 70 imagens sem nome de frame (ignoradas).
   - (B) `images/raw` (640×480, geometria original da câmera; GT casado pelo nome do frame
     com os labels dos splits) — 224 com GT.
   - Modelos: `models/best.pt` (baseline em uso) e o candidato
     `training/runs/yolo26n_porcas_v2/weights/best.pt` (época 58, ainda não adotado).

Comandos (a partir da raiz do repositório):

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.avaliar_estabilizacao `
  --imagens contador_componentes/dataset/images/raw --alvo-gt --salvar brutas_raw.csv
# idem com --modelo contador_componentes/training/runs/yolo26n_porcas_v2/weights/best.pt
# idem com --imagens .../images/train .../images/val .../images/test
```

### O que cada modelo já "viu" (essencial para ler os resultados)

| Frames | baseline `models/best.pt` | candidato `porcas_v2` |
|---|---|---|
| 23/09 e 30/09 (dataset v1) | vistos (train/val/test v1) | maioria vista (train) |
| 21/10 (importados do Roboflow, cenas com distratores: bits de chave de fenda) | **nunca vistos** | maioria vista (train/val) |

Logo, a evidência **mais honesta** de oscilação é **baseline × frames de 21/10 em `raw`**
(execução B). Os resultados do candidato sobre esses frames são otimistas (memorização).

---

## 2. Resultados

FPS de inferência medido nesta máquina (CPU, só `predict`, sem captura/exibição, após
aquecimento): **21,5–24,9 FPS**. O FPS real do pipeline ao vivo ainda **não foi medido**
(tarefa 6.4.1 pendente) e será menor (captura 1080p + ROI + exibição) — ver seção 3.

### 2.1 Oscilação da contagem bruta (alvo = GT)

| Execução | Modelo | Frames | % frames com contagem == GT | Mudanças entre frames consecutivos | Sequências que oscilam |
|---|---|---|---|---|---|
| B `raw` (21/10) | baseline | 111 | **26,1 %** | 43 | **19/25** |
| B `raw` (21/10) | porcas_v2 (viu os frames) | 111 | 100 % | 0 | 0/25 |
| A splits | baseline | 296 | 70,9 % | 34 | 20/42 |
| A splits | porcas_v2 (viu a maioria) | 296 | 99,7 % | 1 | 1/42 |

Exemplos reais (baseline, `raw`, frames quase idênticos da mesma rajada):
porca GT=2 → `1 0 1 0 1 1 1`; porca GT=2 → `4 5 3 3 4 3 2`; parafuso GT=4 → `8 7 6 7`;
porca GT=1 → `1 1 0 1 0`. E também **erro sistemático estável**: porca GT=2 →
`1 1 1 1 1 1 1`, porca GT=2 → `5 5 5`.

### 2.2 Baseline × `raw` 21/10 (frames nunca vistos) — evidência principal

25 sequências, comprimento 3–7 frames (nenhuma com ≥ 8). FPS usado: 24,94.

**alvo = GT** (ATINGIDA correta):

| N | elegíveis (len ≥ N) | seq. com ATINGIDA | mudanças de estado | entradas ATING. | saídas ATING. (piscadas) | entradas EXCED. | latência mediana 1ª ATING. |
|---|---|---|---|---|---|---|---|
| 1 | 25 | 14 | 43 | 17 | **11** | 22 | 1,5 fr (0,06 s) |
| 3 | 25 | 4 | 18 | 4 | 2 | 10 | 3 fr (0,12 s) |
| 5 | 10 | 0 | 4 | 0 | 0 | 3 | — |
| 8 | 0 | 0 | 0 | 0 | 0 | 0 | — (sem sequência elegível) |
| 10 | 0 | 0 | 0 | 0 | 0 | 0 | — (sem sequência elegível) |

**alvo = GT+1** (falta uma peça — qualquer ATINGIDA é FALSA):

| N | elegíveis | seq. com ATINGIDA falsa | entradas ATING. falsas | piscadas |
|---|---|---|---|---|
| 1 | 25 | **13** | 17 | 11 |
| 3 | 25 | **3** | 3 | 2 |
| 5 | 10 | 0 | 0 | 0 |
| 8 | 0 | 0 | 0 | 0 |
| 10 | 0 | 0 | 0 | 0 |

**alvo = GT−1** (uma peça a mais — qualquer ATINGIDA é FALSA):

| N | elegíveis | seq. com ATINGIDA falsa | entradas ATING. falsas |
|---|---|---|---|
| 1 | 24 | 5 | 7 |
| 3 | 24 | 3 | 3 |
| 5 | 9 | **2** | 2 |
| 8 | 0 | 0 | 0 |
| 10 | 0 | 0 | 0 |

### 2.3 Splits (A) — baseline e candidato

Baseline (FPS 23,45), 42 sequências; 16 delas (cenas de 23/09, vistas no treino) têm 10+
frames.

| N | elegíveis | alvo=GT: seq. c/ ATING. | alvo=GT: piscadas | alvo=GT: latência mediana | alvo=GT+1: seq. c/ ATING. falsa | alvo=GT−1: seq. c/ ATING. falsa |
|---|---|---|---|---|---|---|
| 1 | 42 | 26 | 6 | 1 fr (0,04 s) | 9 | 5 |
| 3 | 42 | 21 | 0 | 3 fr (0,13 s) | 1 | 2 |
| 5 | 27 | 18 | 0 | 5 fr (0,21 s) | 0 | 1 |
| 8 | 16 | 16 | 0 | 8 fr (0,34 s) | 0 | 0 |
| 10 | 16 | 16 | 0 | 10 fr (0,43 s) | 0 | 0 |

Candidato `porcas_v2` (FPS 21,54): alvo=GT atingido em todas as sequências elegíveis para
todos os N, 0 piscadas para N ≥ 3; 1 ATINGIDA falsa só com N=1 (alvo=GT+1); 0 com N ≥ 3.
**Viés**: o candidato treinou na maioria desses frames; isso NÃO prova estabilidade ao vivo.
Nos 12 frames de 21/10 do split **test** (nunca vistos por ele), acertou a contagem exata em
83 % dos frames (amostra pequena, não forma sequências ≥ 3).

### 2.4 Leitura dos resultados

1. **A oscilação bruta é real e frequente** com o modelo em uso em cenas novas: só 26 % dos
   frames com contagem exata e 19/25 rajadas oscilando entre frames quase idênticos. Sem
   estabilização (N=1) o status piscaria (11 saídas de ATINGIDA em 25 sequências curtas) e
   haveria **ATINGIDA falsa em 13/25 sequências** quando falta uma peça.
2. **N=3 reduz muito, mas não elimina** ATINGIDA falsa (3/25 com GT+1; 3/24 com GT−1).
3. **N=5 eliminou ATINGIDA falsa no cenário "falta 1 peça"** nas sequências elegíveis, mas
   ainda houve 2 ATINGIDA falsas no cenário "1 a mais": eram **erros sistemáticos estáveis**
   do modelo (ex.: porca contada `1 1 1 1 1 1 1` com 2 reais). **Nenhum N corrige erro
   sistemático** — isso é qualidade do modelo/dataset (distratores, porcas), não
   estabilização.
4. **N ≥ 8 não pôde ser avaliado** nos frames não vistos: nenhuma rajada tem ≥ 8 frames.
   Nas rajadas longas (23/09, vistas no treino, contagem sempre correta) N=8/10 só
   acrescentou latência.
5. **Piscadas não são controladas por N** no desenho atual: `EstabilizadorContagem` não
   tem histerese de saída — uma única leitura fora do alvo derruba ATINGIDA. N só atrasa a
   (re)entrada. Nos dados, com N ≥ 3 as saídas ficaram em 0–2, mas isso precisa ser
   confirmado ao vivo (sequências longas, mãos/sombras). Se o teste ao vivo mostrar quedas
   de ATINGIDA perceptíveis, o time pode avaliar histerese de saída — isso faz parte do
   ponto em aberto "método final de estabilização" e **não foi implementado aqui**.

---

## 3. Latência implicada (N / FPS)

Espera mínima entre a contagem ficar correta e o status virar ATINGIDA = N frames.

| N | a 24 FPS (inferência medida aqui) | a 15 FPS | a 10 FPS | a 5 FPS |
|---|---|---|---|---|
| 1 | 0,04 s | 0,07 s | 0,10 s | 0,20 s |
| 3 | 0,13 s | 0,20 s | 0,30 s | 0,60 s |
| 5 | 0,21 s | 0,33 s | 0,50 s | 1,00 s |
| 8 | 0,33 s | 0,53 s | 0,80 s | 1,60 s |
| 10 | 0,42 s | 0,67 s | 1,00 s | 2,00 s |

As colunas de 15/10/5 FPS são **hipotéticas**: o FPS real do pipeline ao vivo (1080p +
ROI + exibição, no PC final) ainda não foi medido (tarefas 6.4.1 / 11.3.1). O teste ao vivo
abaixo mede o FPS real e imprime a latência correspondente.

---

## 4. Recomendação PRELIMINAR (a decisão é do time)

- **Manter N = 5 como valor de trabalho** até o teste ao vivo. Não há evidência para
  mudar: N=1 é claramente insuficiente, N=3 ainda deixou passar ATINGIDA falsa por
  oscilação, N=5 eliminou as falsas por oscilação nos dados disponíveis, e sua latência
  (≈ 0,2–0,5 s entre 24 e 10 FPS) é baixa para uma tarefa manual de conferência.
- Se o FPS ao vivo ficar baixo (≲ 5 FPS), a latência de N=5 passa de ~1 s; aí o time pode
  preferir N menor **ou** definir N em função de tempo — decisão do time.
- N=8/10 só se justifica se o teste ao vivo mostrar ATINGIDA falsa com N=5 por oscilação
  (não por erro sistemático).
- Erros sistemáticos (contagem estável, porém errada) devem ser tratados no modelo/dataset
  (ex.: adoção do candidato `porcas_v2`, decisão pendente do time), não com N maior.

---

## 5. Limitações

1. **Rajadas não são vídeo contínuo.** Os frames foram salvos com a tecla `s` do
   `dataset_capture.py` (resolução de nome de 1 s; até ~25 frames/s nas rajadas de 23/09,
   3–7 frames nas de 21/10). Não há movimento real de mãos, colocação de peças, sombras ou
   variação de iluminação ao longo de segundos.
2. **Sequências curtas** (21/10: 3–7 frames): N=8/10 não são avaliáveis nelas; N=5 só em
   10/25 sequências. Latência medida é limitada pelo comprimento da rajada.
3. **Vazamento de treino**: o candidato viu a maior parte dos frames; o baseline viu os de
   23/09 e 30/09. Só "baseline × 21/10" é realmente fora da amostra.
4. **GT estático por cena**: assume-se que a bandeja não mudou dentro da rajada (cena é
   quebrada se o label muda).
5. **FPS medido = vazão de inferência offline** em imagens 640×480/640×640, não o FPS do
   pipeline ao vivo a 1080p com ROI. A ROI ainda não está calibrada (`config.ROI = None`).
6. O modo `--webcam` do script **não foi executado** nesta avaliação (sem a webcam/bandeja
   física disponível para QA); ele está pronto para o checklist abaixo.

---

## 6. Checklist de teste ao vivo (para fechar 8.2.1 / 8.2.2)

Pré-requisitos: webcam GoodVision na posição definitiva, iluminação definitiva, ROI
calibrada em `app/config.py` (`python -m contador_componentes.scripts.calibrar_roi`), modelo
a validar em `models/best.pt` (ou passe `--modelo`). Use K = quantidade realista para a
bandeja (ponto em aberto PRD 29 "quantidade máxima"; sugestão: K = 10 parafusos, K = 4
porcas). Grave os CSVs numa pasta simples, ex.: `contador_componentes/tests/resultados_8_2/`
(arquivos CSV/markdown — **sem banco de dados**).

Comando base (PowerShell, raiz do repositório):

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.avaliar_estabilizacao --webcam `
  --classe parafuso --alvo 10 --segundos 60 --ns 1,3,5,8,10 `
  --salvar contador_componentes/tests/resultados_8_2/A_parafuso_10.csv
```

A janela mostra a contagem bruta e o estado de cada N em paralelo; `q`/`Esc` encerra antes.
Ao final o script imprime FPS medido, oscilação bruta e a tabela por N.

| # | Cenário | Montagem física | `--classe` / `--alvo` | Esperado com o N escolhido | OK? |
|---|---|---|---|---|---|
| 1 | Estável correto | exatamente K peças paradas, 60 s | parafuso / K | 1 entrada em ATINGIDA, **0 piscadas** | ☐ |
| 2 | Falta uma | K−1 peças paradas, 60 s | parafuso / K | **0 entradas** em ATINGIDA | ☐ |
| 3 | Uma a mais | K+1 peças paradas, 60 s | parafuso / K | **0 entradas** em ATINGIDA (EXCEDIDA estável) | ☐ |
| 4 | Enchimento | bandeja vazia; colocar 1 peça a cada ~3 s até K; mão entra e sai | parafuso / K | ATINGIDA só depois da última peça; anotar latência | ☐ |
| 5 | Peças encostadas | K peças com 2–3 pares tocando | parafuso / K | igual ao 1 | ☐ |
| 6 | Classe porca | repetir 1–3 com porcas | porca / K | idem | ☐ |
| 7 | Mistura (RB-01) | K parafusos + algumas porcas | parafuso / K | idem 1 (porcas ignoradas) | ☐ |
| 8 | Candidato | repetir 1–4 com `--modelo contador_componentes/training/runs/yolo26n_porcas_v2/weights/best.pt` | — | comparar com o baseline | ☐ |

Reanálise sem câmera (testar outros N sobre o mesmo CSV):

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.avaliar_estabilizacao `
  --csv contador_componentes/tests/resultados_8_2/A_parafuso_10.csv `
  --classe parafuso --alvo 10 --ns 1,2,3,4,5,6,8,10
```

Registrar para cada cenário: FPS medido, tabela por N, e se houve oscilação perceptível
de status (8.2.1). Critérios de aceite sugeridos (o time confirma ou ajusta): cenários 2/3
com 0 ATINGIDA falsa; cenário 1 sem piscadas; latência do cenário 4 aceitável para o
operador (limite em segundos **a definir pelo time** — o PRD não fixa um valor).

Fechamento (8.2.2, feito pelo time): escolher N, atualizar `FRAMES_ESTABILIZACAO` em
`app/config.py`, registrar aqui a decisão (N, FPS medido, data, modelo usado) e marcar 8.2
no `TASKS.md`. Se houver piscadas mesmo com N alto, decidir sobre histerese de saída
(ponto em aberto "método final de estabilização").

### Registro da decisão (preencher pelo time)

- N adotado: ____  · FPS ao vivo medido: ____ · Modelo: ____ · Data: ____
- Justificativa: ____
