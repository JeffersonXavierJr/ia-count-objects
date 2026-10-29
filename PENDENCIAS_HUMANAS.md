# Pendências que dependem do time (interação humana)

Lista do que ficou em aberto nas Sprints 1–8 porque precisa de alguém com a webcam, a bandeja ou
o poder de decidir. Para cada item: **o que fazer**, **como executar** e **como validar**.
Ao concluir, marque o item correspondente no `TASKS.md`.

Todos os comandos são rodados **na raiz do repositório** (`ia-count-objects`), no PowerShell:

```powershell
cd C:\Users\jejun\programs\ia-count-objects
venv\Scripts\activate
```

Em todas as janelas OpenCV, `q` ou `Esc` encerra.

---

## Ordem sugerida

| # | Pendência | Tarefa no TASKS.md | Depende de |
|---|---|---|---|
| 1 | Decidir qual modelo usar | (Sprint 5, recomendação) | — |
| 2 | Corrigir labels incompletos | (Sprint 5, recomendação) | — |
| 3 | Calibrar e travar a ROI | 6.1.1 | câmera na posição definitiva |
| 4 | Medir FPS, CPU e RAM | 6.4.1–6.4.3 | 1, 3 |
| 5 | Teste ao vivo da contagem | 7.4 (checklist ao vivo) | 1, 3 |
| 6 | Escolher o N da estabilização | 8.2.1–8.2.2 | 1, 3, 4 |
| 7 | Decisões de documentação | — | — |

Os itens 1, 2 e 7 podem ser feitos em paralelo. Os itens 3 a 6 precisam da webcam e devem seguir
a ordem, porque o resultado de cada um muda os seguintes (o modelo muda a contagem, a ROI muda o
FPS e o FPS muda a espera de N frames).

---

## 1. Decidir qual modelo usar (`contador_componentes/models/best.pt`)

**Situação:** `contador_componentes/models/best.pt` ainda é o modelo antigo. O modelo novo (`yolo26n_porcas_v2`) treinou
só 58 de 100 épocas (o treino foi interrompido por falta de memória), mas já acerta muito mais
porcas: recall de porca no teste 0,955 contra 0,356 do antigo. Em compensação, perde parafusos
encostados uns nos outros. Detalhes em `contador_componentes/training/validacao_sprint5.md`.

**Opção A — adotar o modelo da época 58 como está:**

```powershell
Copy-Item contador_componentes\models\best.pt contador_componentes\models\best_baseline.pt
Copy-Item contador_componentes\training\runs\yolo26n_porcas_v2\weights\best.pt contador_componentes\models\best.pt
```

> O app carrega o modelo de `contador_componentes\models\best.pt` (`MODEL_PATH` em
> `contador_componentes/app/config.py`). O primeiro comando guarda o modelo antigo, para poder
> voltar atrás.

**Opção B — terminar o treino até 100 épocas (recomendado).** Feche outros programas pesados e
use um batch menor, para não faltar memória de novo:

```powershell
venv\Scripts\python.exe -c "from ultralytics import YOLO; YOLO(r'contador_componentes\training\runs\yolo26n_porcas_v2\weights\last.pt').train(resume=True, batch=8, workers=2)"
```

Leva algumas horas na CPU. Ao terminar, copie o novo `best.pt` como na opção A.

**Como validar:**

1. Rode a avaliação no conjunto de teste e compare com os números da Sprint 5:
   ```powershell
   venv\Scripts\python.exe contador_componentes/training/avaliar_teste.py --nome modelo_final
   venv\Scripts\python.exe contador_componentes/training/metricas_teste.py contador_componentes/training/runs/sprint5/modelo_final/predicoes.json --com-map
   ```
   O primeiro usa o modelo de `contador_componentes\models\best.pt` (ou outro, com `--modelo`) e
   gera as imagens com as caixas desenhadas; o segundo calcula precisão, recall e erro de contagem.
2. Precisão e recall de porca devem ficar ≥ 0,95, e parafuso não pode piorar em relação ao
   modelo antigo no grupo de imagens independentes.
3. Registre o resultado em `contador_componentes/training/registro_treinos.md`.

---

## 2. Corrigir labels incompletos

**Situação:** 7 imagens do conjunto de teste têm peças reais sem anotação. Isso faz o modelo
parecer pior do que é (as detecções certas contam como falsos positivos) e ensina errado no
treino, se o mesmo problema estiver nas fotos vizinhas.

**Como executar:** abra cada imagem no Roboflow (ou na ferramenta de anotação usada) e acrescente
as caixas que faltam.

| Arquivo (test) | Faltando | Posição aprox. (px, 640x640) |
|---|---|---|
| `WhatsApp-Image-2026-10-22-at-19-40-31` | 3 porcas + 1 parafuso preto | (267,291), (210,299), (306,223) |
| `WhatsApp-Image-2026-10-22-at-19-40-32` | 2 porcas | (393,187) porca preta; (562,256) porca flangeada |
| `WhatsApp-Image-2026-10-22-at-19-40-22` | 1 porca | (264,404) porca preta flangeada |
| `frame_20260930_205151` | 2 porcas rosqueadas | (234,362) no 2º parafuso; (334,205) no topo do 4º parafuso |
| `frame_20261021_202749` | 2 porcas | (230,306) porca quadrada; (350,32) porca cortada na borda superior |
| `frame_20261021_202827` | 1 porca castelo + verificar objeto quadrado cinza | (221,89); objeto em ~(220,355) |
| `frame_20261021_202445_001` | 1 parafuso (encostado no bit) | (276,422) |

Revise também as fotos **vizinhas da mesma rajada** em `train/` e `val/` (mesmo prefixo de data e
hora): os mesmos tipos de porca (quadrada, castelo, flangeada preta, rosqueada no parafuso)
provavelmente estão sem label lá também.

Depois de exportar do Roboflow:

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.importar_roboflow <pasta_do_export> --dry-run
venv\Scripts\python.exe -m contador_componentes.scripts.poligonos_para_bbox
```

> O `importar_roboflow` **pula** arquivos que já existem. Para substituir labels corrigidos, copie
> os `.txt` novos por cima dos antigos em `contador_componentes/dataset/labels/<split>/` e apague
> os arquivos `*.cache` dessa pasta.

**Como validar:** abra as imagens corrigidas com as caixas desenhadas (o `avaliar_teste` gera
imagens anotadas) e confira que toda peça visível tem uma caixa. Depois rode de novo as métricas
do teste: os falsos positivos dessas imagens devem cair.

---

## 3. Calibrar e travar a ROI — tarefa 6.1.1

**Pré-requisito:** câmera fixada na posição definitiva sobre a bandeja (se a iluminação da
Sprint 10 ainda não existir, use a posição de referência registrada na Sprint 1).

**Como executar:**

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.calibrar_roi
```

| Tecla | Ação |
|---|---|
| arrastar com o mouse | desenhar um novo retângulo |
| `w` `a` `s` `d` | mover o retângulo |
| `j` / `l` | diminuir / aumentar a largura |
| `i` / `k` | diminuir / aumentar a altura |
| `f` | alternar passo fino (1 px) / grosso (10 px) |
| `r` | voltar ao frame inteiro |
| `p` ou Enter | imprimir a linha `ROI = (...)` no terminal |

1. Ajuste o retângulo para cobrir **toda a área útil da bandeja** e um pouco de margem, sem
   pegar o que está fora dela.
2. Aperte `p` e copie a linha impressa para `contador_componentes/app/config.py`, substituindo
   `ROI = None`.
3. Tire uma foto da montagem e anote a altura da câmera (útil para a Sprint 10).

**Como validar:**

- Rode `venv\Scripts\python.exe -m contador_componentes.scripts.pipeline_ao_vivo`: a janela deve
  mostrar só a bandeja, inteira.
- Coloque peças **nos quatro cantos e encostadas nas bordas**: todas devem aparecer inteiras e
  com caixa.
- Marque **6.1.1** e **6.1** no `TASKS.md`.

---

## 4. Medir FPS, CPU e RAM — tarefas 6.4.1 a 6.4.3

**Pré-requisito:** ROI calibrada (item 3) e o modelo escolhido (item 1) em `contador_componentes/models/best.pt`.

**Como executar:**

1. **FPS (6.4.1):** com algumas peças na bandeja, rode por 60 segundos:
   ```powershell
   venv\Scripts\python.exe -m contador_componentes.scripts.avaliar_estabilizacao --webcam --classe parafuso --alvo 10 --segundos 60 --ns 5
   ```
   O FPS medido é impresso no fim. O `pipeline_ao_vivo` também mostra o FPS na tela, como
   conferência.
2. **CPU e RAM (6.4.2):** enquanto o comando acima roda, abra **outro** PowerShell e rode:
   ```powershell
   Get-Process python | Select-Object Id, @{n='RAM_MB';e={[math]::Round($_.WorkingSet64/1MB)}}
   (Get-Counter '\Processo(python*)\% tempo de processador' -SampleInterval 2 -MaxSamples 10).CounterSamples | Select-Object InstanceName, @{n='CPU_%';e={[math]::Round($_.CookedValue / $env:NUMBER_OF_PROCESSORS,1)}}
   ```
   (Se o Windows estiver em inglês, o contador é `'\Process(python*)\% Processor Time'`.)
   Alternativa sem comando: **Gerenciador de Tarefas → Detalhes →** `python.exe`, colunas CPU e
   Memória.
3. **Registro (6.4.3):** anote em uma tabela, por exemplo num arquivo novo
   `contador_componentes/tests/desempenho_6_4.md`:

   | Data | Computador | Modelo | Resolução | ROI | FPS | CPU % | RAM MB |
   |---|---|---|---|---|---|---|---|

**Como validar:** repita a medição 2 ou 3 vezes; os números devem ficar próximos. Como
referência, só a inferência deu 21–25 FPS nesta máquina; o pipeline completo deve ficar abaixo
disso. Se ficar abaixo de ~5 FPS, avise antes de seguir para a Sprint 9 (a interface pode
travar). Marque **6.4.1–6.4.3**, **6.4** e, com o item 3, a **Sprint 6** no `TASKS.md`.

---

## 5. Teste ao vivo da contagem — checklist da Sprint 7

**Situação:** a Sprint 7 foi validada com fotos do dataset, mas nenhuma delas tem o exemplo exato
do PRD (12 parafusos + 4 porcas). O checklist completo está em
`contador_componentes/tests/relatorio_testes_contagem.md`.

**Como executar:**

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.testar_contagem --webcam --classe parafuso --alvo 12
```

O terminal imprime uma linha a cada mudança de contagem ou estado.

| Cenário | Resultado esperado |
|---|---|
| Bandeja vazia | `0 \| CONTANDO` |
| Sem `--classe` e `--alvo` | `AGUARDANDO CONFIGURAÇÃO` |
| Colocar parafusos um a um até 12, separados | `CONTANDO` até 11, `QUANTIDADE ATINGIDA` em 12 |
| Colocar o 13º parafuso | `QUANTIDADE EXCEDIDA` |
| Retirar um | volta para `QUANTIDADE ATINGIDA` |
| 12 parafusos + 4 porcas, `--classe parafuso --alvo 12` | exibe 12, `QUANTIDADE ATINGIDA` |
| A mesma cena, `--classe porca --alvo 4` | exibe 4, `QUANTIDADE ATINGIDA` |
| Peças encostadas lado a lado | anotar a contagem (ponto fraco do modelo novo) |
| Bit ou chave junto das peças | anotar se vira parafuso falso (ponto fraco do modelo antigo) |
| Mão entrando na bandeja | anotar o que acontece com o estado |
| `--modelo nao_existe.pt` | `MODELO NÃO CARREGADO`, sem travar |
| Desconectar a webcam com o script rodando | `ERRO DE CÂMERA`, sem travar |

**Como validar:** todos os cenários com resultado esperado devem bater. Anote os que falharem
(com foto da bandeja, se possível) na seção de checklist do `relatorio_testes_contagem.md`.
Falha de contagem (número errado) é problema do modelo/dataset (itens 1 e 2); falha de estado
com a contagem certa é bug no código e deve ser reportada.

> Esse script ainda não usa a estabilização da Sprint 8, então alguma oscilação de estado é
> esperada aqui. A oscilação é avaliada no item 6.

---

## 6. Escolher o N da estabilização — tarefas 8.2.1 e 8.2.2

**Situação:** a estabilização está pronta com N = 5 (`FRAMES_ESTABILIZACAO` em
`contador_componentes/app/config.py`). O teste offline recomendou manter 5, mas foi feito com
fotos em rajada, não com vídeo. Detalhes e o checklist completo em
`contador_componentes/tests/relatorio_estabilizacao.md`.

**Como executar:** grave cada cenário por 60 segundos, simulando vários N ao mesmo tempo:

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.avaliar_estabilizacao --webcam --classe parafuso --alvo 10 --segundos 60 --ns 1,3,5,8,10 --salvar contador_componentes/tests/resultados_8_2/A_parafuso_10.csv
```

Cenários sugeridos (troque o nome do CSV para cada um):

1. 10 parafusos parados, separados (alvo 10).
2. 9 parafusos com alvo 10 (não pode dar `QUANTIDADE ATINGIDA`).
3. 11 parafusos com alvo 10 (deve dar `QUANTIDADE EXCEDIDA`, não ATINGIDA).
4. Encher a bandeja peça por peça até 10.
5. 10 parafusos encostados entre si.
6. Porcas (`--classe porca`).
7. Parafusos e porcas misturados.

Para testar outros valores de N **sem câmera**, reprocesse um CSV já gravado:

```powershell
venv\Scripts\python.exe -m contador_componentes.scripts.avaliar_estabilizacao --csv contador_componentes/tests/resultados_8_2/A_parafuso_10.csv --classe parafuso --alvo 10 --ns 3,4,5,6,8
```

**Como validar e decidir:** para cada N, o script mostra quantas vezes o estado mudou, quantas
vezes entrou e saiu de `QUANTIDADE ATINGIDA` ("piscadas") e quanto tempo levou para estabilizar.
Escolha o **menor N** que:

- **nunca** dá `QUANTIDADE ATINGIDA` nos cenários 2 e 3 (o mais importante);
- não pisca no cenário 1;
- não demora mais do que o time aceita (em geral, até ~1 segundo).

Se o status ficar **caindo** de ATINGIDA por uma leitura isolada, mesmo com N alto, avise: a
saída do estado não tem tolerância hoje, e isso é uma mudança de código.

Registre a decisão na seção "Registro da decisão" do `relatorio_estabilizacao.md`, ajuste
`FRAMES_ESTABILIZACAO` se mudar e marque **8.2.1**, **8.2.2**, **8.2** e a **Sprint 8** no
`TASKS.md`.

---

## 7. Decisões de documentação (sem webcam)

Estas não têm teste; só precisam de uma decisão do time.

- [ ] **PRD, CLAUDE.md e agentes desatualizados.** O `TASKS.md` removeu Home Assistant, MQTT,
  streaming de vídeo e estrutura física, e trocou a interface por uma janela Tkinter local. O
  `PRD.md`, o `CLAUDE.md` e `.claude/agents/` (incluindo o `home-assistant-specialist`) ainda
  descrevem o desenho antigo. Como o PRD é a fonte da verdade, ele precisa ser atualizado para
  bater com o `TASKS.md`.
- [ ] **`paho-mqtt` no `requirements.txt`.** Sem MQTT na v1, pode ser removido.
- [ ] **`QUANTIDADE EXCEDIDA`.** O estado existe no `TASKS.md` e foi implementado, mas não está na
  regra RB-03 do PRD. Confirmar e incluir no PRD.
- [ ] **Sprint 10 (iluminação).** Confirmar se continua no escopo, já que a estrutura física foi
  removida.
- [ ] **Tarefa 1.2 no `TASKS.md`.** Todas as subtarefas estão marcadas, mas o título `1.2` ainda
  está `[ ]`. Confirmar e marcar.

**Como validar:** depois das alterações, PRD, CLAUDE.md e TASKS.md não devem se contradizer.
Uma busca por "Home Assistant" e "MQTT" deve aparecer só como itens fora do escopo ou expansão
futura.
