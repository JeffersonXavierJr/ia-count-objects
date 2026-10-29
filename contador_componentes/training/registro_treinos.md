# Registro de treinos

Registro simples dos parametros de cada treino (sem banco de dados). As
metricas detalhadas de cada run ficam no `results.csv` gerado pelo
ultralytics dentro de `runs/<nome_do_run>/`.

## yolo26n_baseline (tarefa 4.2)

- Data: 2026-10-14
- Modelo base: `yolo26n.pt` (baseline do PRD 13.3; YOLO26s nao usado)
- Tarefa: Object Detection (bounding boxes), 2 classes (0 parafuso, 1 porca)
- Dataset: train 199 / val 57 imagens (test 28 reservado para a Sprint 5)
- imgsz: 640 (baseline do PRD, secao 21, Etapa 4)
- Epocas: 100 (default do `train.py`); patience = 100 (default do ultralytics)
- Device: CPU (Intel Core Ultra 9 185H; maquina sem GPU/CUDA)
- Ultralytics 8.4.177 / torch 2.14.1+cpu / Python 3.12.9
- Tempo por epoca (CPU, incluindo validacao): ~46 s em media (~60 s nas
  primeiras epocas, ~42 s depois); total 100 epocas = ~76 min (1,27 h)
- Early stopping: nao ocorreu (100/100 epocas); melhor epoca = 98
- Nome do run: `runs/yolo26n_baseline`
- Comando (a partir da raiz do repo):
  `venv\Scripts\python.exe contador_componentes/training/train.py --epochs 100 --device cpu --name yolo26n_baseline`

Justificativa das epocas: teste curto de 2 epocas mediu ~85 s/epoca em CPU
(validacao incluida), projetando ~2-2,5 h para 100 epocas, dentro do limite
aceitavel (~3 h). Com dataset pequeno e pesos pre-treinados, 100 epocas
(default do proprio ultralytics) e um ponto de partida razoavel; o valor deve
ser ajustado experimentalmente nos proximos treinos olhando as curvas de
loss/mAP. Com patience = 100 o early stopping nao chega a atuar em 100
epocas — o `best.pt` e escolhido pelo melhor fitness de validacao.

### Metricas preliminares (tarefa 4.3)

Metricas PRELIMINARES de validacao (split `val`, 57 imagens), nao finais.
O split `test` (28 imagens) NAO foi usado — fica reservado para a Sprint 5
(validacao em fotos nunca vistas pelo modelo).

Peso escolhido: `best.pt` do run (melhor fitness de validacao, epoca 98),
copiado (nao movido) para `contador_componentes/models/best.pt`. O original
continua em `runs/yolo26n_baseline/weights/best.pt` (mesmo SHA-256). Pesos
`*.pt` ficam fora do Git (`.gitignore`). Conferido: carrega com
`YOLO("contador_componentes/models/best.pt")`, task `detect`,
`model.names == {0: 'parafuso', 1: 'porca'}`.

Do `results.csv` (validacao feita pelo ultralytics durante o treino):

| Epoca | Precision(B) | Recall(B) | mAP50(B) | mAP50-95(B) | val/box_loss | val/cls_loss | val/l1_loss |
|---|---|---|---|---|---|---|---|
| 98 (melhor) | 0,98651 | 0,91872 | 0,97077 | 0,81077 | 0,65055 | 0,38798 | 0,00261 |
| 100 (final) | 0,98717 | 0,91572 | 0,97225 | 0,81005 | 0,65232 | 0,38798 | 0,00261 |

Diferenca entre epoca 98 e 100 e minima — as curvas estabilizaram no fim.

Validacao por classe com `models/best.pt` (split `val`, imgsz 640, CPU):

| Classe | Imagens | Instancias | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| todas | 57 | 513 | 0,987 | 0,919 | 0,972 | 0,811 |
| parafuso | 53 | 446 | 0,985 | 0,897 | 0,971 | 0,826 |
| porca | 12 | 67 | 0,988 | 0,940 | 0,973 | 0,796 |

- Velocidade (CPU de treino, por imagem): ~2,2 ms pre-processamento,
  ~42,6 ms inferencia, ~0,8 ms pos-processamento. Nao e a medida do PC final.
- Saida do val: `runs/yolo26n_baseline_val/` (fora do Git, como todo `runs/`).
- Comando (a partir da raiz do repo, script avulso):
  `YOLO("contador_componentes/models/best.pt").val(data="contador_componentes/training/dataset.yaml", split="val", device="cpu", imgsz=640, project=<abs>/contador_componentes/training/runs, name="yolo26n_baseline_val")`

Observacoes preliminares (a investigar na Sprint 5, antes de pensar em
YOLO26s):
- Precision alta e recall menor: o modelo erra mais por deixar de detectar
  (falso negativo) do que por detectar errado — ponto critico para contagem.
  O recall de parafuso (0,897) e o mais baixo.
- Desbalanceamento: no val, porca tem so 67 instancias em 12 imagens contra
  446 de parafuso em 53 imagens; as metricas de porca tem pouca base
  estatistica.
- Val com apenas 57 imagens: numeros otimistas/instaveis; o teste em fotos
  nunca vistas e que vai confirmar.

## yolo26n_porcas_v2 (Sprint 5)

- Data: 2026-10-27/28
- Dataset: train 339 / val 96 / test 47, apos importar export do Roboflow
  com 198 imagens novas (mais porcas) via `scripts/importar_roboflow.py`
- Mesmos parametros do baseline: `yolo26n.pt`, imgsz 640, 100 epocas
  planejadas, CPU
- **Interrompido na epoca 58/100** por falta de memoria do sistema
  (`last.pt` existe; `best.pt` = melhor fitness ate a ep 58)
- Nome do run: `runs/yolo26n_porcas_v2`
- Validacao do `best.pt` parcial no val NOVO (96 imagens), comparada ao
  baseline no MESMO val:

| Modelo | Classe | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| porcas_v2 (ep 58) | todas | 0,958 | 0,958 | 0,981 | 0,845 |
| porcas_v2 (ep 58) | parafuso | 0,979 | 0,934 | 0,976 | 0,816 |
| porcas_v2 (ep 58) | porca | 0,937 | 0,981 | 0,986 | 0,875 |
| baseline | todas | 0,882 | 0,672 | 0,797 | 0,665 |
| baseline | parafuso | — | 0,877 | — | — |
| baseline | porca | 0,854 | 0,467 | 0,658 | — |

- `models/best.pt` **NAO foi substituido** — pendente decisao do time
  (ver `validacao_sprint5.md`, secao 5.3: corrigir labels, terminar/refazer
  o treino e reorganizar o split antes de trocar).
