# Relatório — Testes da lógica de contagem (Sprint 7, tarefa 7.4)

Data: 28/10/2026 · Pipeline: `detector.run_inference` (conf 0.5, imgsz 640) →
`counter.filter_by_class` → `count_objects` → `determinar_estado`.
Sem estabilização temporal (Sprint 8): cada imagem = 1 frame.

- Modelo **A** = `contador_componentes/models/best.pt` (baseline, `config.MODEL_PATH`)
- Modelo **B** = `contador_componentes/training/runs/yolo26n_porcas_v2/weights/best.pt`
- Imagens: split `test` (não vistas no treino); GT = contagem dos labels YOLO.
  As 7 imagens com label incompleto (`validacao_sprint5.md`, 5.3) **não** foram usadas.
- Reprodução: `python -m contador_componentes.scripts.testar_contagem IMG... --classe C --alvo N [--modelo M]`
  e `python -m pytest contador_componentes/tests/test_contagem_integracao.py -rx`.
- "Passou?" avalia a cadeia completa contra o GT. Toda falha abaixo é **erro de
  detecção do modelo**; nenhum erro foi do `counter` (com a contagem do modelo, o
  estado obtido é sempre o correto para `compare_counts`).

## 7.4.1 — Alvo = quantidade exata de parafusos

| Imagem (prefixo) | Classe | Alvo | GT | A | Estado A | B | Estado B | Esperado | Passou? (A / B) |
|---|---|---|---|---|---|---|---|---|---|
| frame_20260923_204911_001 | parafuso | 1 | 1 | 1 | ATINGIDA | 1 | ATINGIDA | ATINGIDA | ✅ / ✅ |
| frame_20260930_205533 | parafuso | 3 | 3 | 3 | ATINGIDA | 3 | ATINGIDA | ATINGIDA | ✅ / ✅ |
| frame_20261021_202903 | parafuso | 4 | 4 | **5** | **EXCEDIDA** | 4 | ATINGIDA | ATINGIDA | ❌ / ✅ |
| frame_20260923_205522 | parafuso | 6 | 6 | 6 | ATINGIDA | 6 | ATINGIDA | ATINGIDA | ✅ / ✅ |
| frame_20260923_205009_003 | parafuso | 7 | 7 | 7 | ATINGIDA | 7 | ATINGIDA | ATINGIDA | ✅ / ✅ |
| frame_20260930_210437 | parafuso | 12 | 12 | 12 | ATINGIDA | **9** | **CONTANDO** | ATINGIDA | ✅ / ❌ |
| frame_20260923_204759_008 | parafuso | 14 | 14 | 14 | ATINGIDA | 14 | ATINGIDA | ATINGIDA | ✅ / ✅ |

Na varredura de todo o split test, ambos acertam as 18 fotos só-parafuso da série
`frame_20260923_*`. Erros: A conta objetos estranhos como parafuso
(`202903/202905/202922`: 5–6 para GT 4) → EXCEDIDA falso; B perde parafusos
encostados (`210437`: 9/12) → nunca chega a ATINGIDA.

## 7.4.2 — Cena mista (RB-01)

Não há no dataset (test/val/train) cena com exatamente 12 parafusos + 4 porcas
(PRD seção 17). Mais próximas no test: 14+2 (`204903`), 13+1 (`205043`, pilha —
descartada por oclusão), 6+2, 4+2, 4+1. O exemplo 12+4 exato fica para o teste ao
vivo (checklist abaixo).

| Imagem (prefixo) | Classe | Alvo | GT | A | Estado A | B | Estado B | Esperado | Passou? (A / B) |
|---|---|---|---|---|---|---|---|---|---|
| frame_20260930_204903 (14+2) | parafuso | 14 | 14 | 13 | CONTANDO | 13 | CONTANDO | ATINGIDA | ❌ / ❌ |
| frame_20260930_204903 | porca | 2 | 2 | 2 | ATINGIDA | 2 | ATINGIDA | ATINGIDA | ✅ / ✅ |
| frame_20260930_210643 (6+2) | parafuso | 6 | 6 | 5 | CONTANDO | 5 | CONTANDO | ATINGIDA | ❌ / ❌ |
| frame_20260930_210643 | porca | 2 | 2 | 2 | ATINGIDA | 2 | ATINGIDA | ATINGIDA | ✅ / ✅ |
| frame_20261021_202458_001 (4+2) | parafuso | 4 | 4 | 5 | EXCEDIDA | 4 | ATINGIDA | ATINGIDA | ❌ / ✅ |
| frame_20261021_202458_001 | porca | 2 | 2 | 1 | CONTANDO | 2 | ATINGIDA | ATINGIDA | ❌ / ✅ |
| frame_20261021_202525 (4+2) | parafuso | 4 | 4 | 7 | EXCEDIDA | 4 | ATINGIDA | ATINGIDA | ❌ / ✅ |
| frame_20261021_202525 | porca | 2 | 2 | 1 | CONTANDO | 2 | ATINGIDA | ATINGIDA | ❌ / ✅ |
| frame_20261021_202334 (4+1) | parafuso | 4 | 4 | 6 | EXCEDIDA | 4 | ATINGIDA | ATINGIDA | ❌ / ✅ |
| frame_20261021_202334 | porca | 1 | 1 | 2 | EXCEDIDA | 1 | ATINGIDA | ATINGIDA | ❌ / ✅ |

**RB-01 validado em todas as 5 cenas × 2 modelos**: a contagem exibida é igual ao
número de detecções da classe selecionada, e a outra classe nunca entra. Ex.:
modelo B em `202458_001` com classe=parafuso, alvo 4 → exibe 4 / ATINGIDA (se as
porcas fossem somadas seria 6 / EXCEDIDA).

## 7.4.3 — Transições (alvo fixo = 6, fotos com quantidade crescente)

| Passo | Imagem (prefixo) | Classe | Config | GT | A → estado | B → estado | Esperado | Passou? (A / B) |
|---|---|---|---|---|---|---|---|---|
| 0 | frame_20260930_210535 | parafuso | nenhuma | 0 | 0 → AGUARDANDO | 0 → AGUARDANDO | AGUARDANDO CONFIGURAÇÃO | ✅ / ✅ |
| 1 | frame_20260930_210535 (vazia) | parafuso | 6 | 0 | 0 → CONTANDO | 0 → CONTANDO | CONTANDO | ✅ / ✅ |
| 2 | frame_20260923_204911_001 | parafuso | 6 | 1 | 1 → CONTANDO | 1 → CONTANDO | CONTANDO | ✅ / ✅ |
| 3 | frame_20260930_205533 | parafuso | 6 | 3 | 3 → CONTANDO | 3 → CONTANDO | CONTANDO | ✅ / ✅ |
| 4 | frame_20260923_205522 | parafuso | 6 | 6 | 6 → ATINGIDA | 6 → ATINGIDA | QUANTIDADE ATINGIDA | ✅ / ✅ |
| 5 | frame_20260923_205009_003 | parafuso | 6 | 7 | 7 → EXCEDIDA | 7 → EXCEDIDA | QUANTIDADE EXCEDIDA | ✅ / ✅ |
| 1 | frame_20261021_202611 | porca | 6 | 2 | 2 → CONTANDO | 2 → CONTANDO | CONTANDO | ✅ / ✅ |
| 2 | WhatsApp-…-21-59-24_ | porca | 6 | 4 | **0** → CONTANDO | 4 → CONTANDO | CONTANDO | ⚠️ (certo por acaso) / ✅ |
| 3 | WhatsApp-…-21-59-25-4- | porca | 6 | 6 | **0** → CONTANDO | 6 → ATINGIDA | QUANTIDADE ATINGIDA | ❌ / ✅ |
| 4 | WhatsApp-…-21-59-23-2- | porca | 6 | 11 | **0** → CONTANDO | 11 → EXCEDIDA | QUANTIDADE EXCEDIDA | ❌ / ✅ |
| erro | `--modelo nao_existe.pt` / `load_model(...)` | — | 6 | — | MODELO NÃO CARREGADO | idem | MODELO NÃO CARREGADO | ✅ |
| erro | `camera.open_camera(99)` → `CameraError` → `estado_de_erro` | — | 6 | — | ERRO DE CÂMERA | idem | ERRO DE CÂMERA | ✅ |

Observação: as fotos são de cenas diferentes (não a mesma bandeja sendo
preenchida); simulam a sequência, mas o teste real é o ao vivo abaixo.

## Resultado do pytest

`venv\Scripts\python.exe -m pytest contador_componentes/tests -q` →
**147 passed, 13 xfailed** (os 13 xfail = erros de contagem do modelo listados acima,
marcados em `FALHAS_CONHECIDAS` de `test_contagem_integracao.py`; se o modelo
passar a acertar, viram "passed" automaticamente).

## Achados

- **Nenhum bug no `counter.py`** nos cenários testados.
- Observação (baixo risco, não corrigido): `compare_counts` / `ConfiguracaoContagem`
  rejeitam `numpy.int64` (`ValueError`), pois validam `isinstance(x, int)`. Hoje
  não afeta (`count_objects` devolve `int`), mas o estabilizador da Sprint 8 ou o
  widget de alvo da Sprint 9 devem converter para `int` antes.
- Modelo A não serve para porcas em foto de outro domínio (WhatsApp: 0 detectadas)
  e conta objetos estranhos como parafuso → estados EXCEDIDA falsos. Modelo B é
  melhor em tudo exceto parafusos encostados (`210437`: 9/12). Isso reforça a
  decisão pendente de qual `best.pt` vai para `models/`.

## Checklist de teste manual ao vivo (time, com a webcam)

Comando base (raiz do repo, venv ativo; `q`/Esc encerra; o terminal imprime uma
linha a cada mudança):
`python -m contador_componentes.scripts.testar_contagem --webcam --classe parafuso --alvo 12 [--modelo CAMINHO]`

Rodar com o modelo que será o oficial (e, se possível, com A e B). Anotar, para
cada item: modelo, contagem exibida, estado e se oscilou (oscilação é esperada até
a Sprint 8 — anotar mesmo assim, serve para escolher N).

- [ ] ROI calibrada (`config.ROI`) e iluminação definitiva; bandeja vazia → `0 | CONTANDO`.
- [ ] Sem `--classe/--alvo` → `AGUARDANDO CONFIGURAÇÃO` (contagem não exibida).
- [ ] 7.4.1: colocar parafusos um a um até 12, separados → CONTANDO até 11, ATINGIDA em 12; o 13º → EXCEDIDA; retirar um → volta a ATINGIDA.
- [ ] 7.4.2 (PRD seção 17): 12 parafusos + 4 porcas na bandeja: `--classe parafuso --alvo 12` → exibe 12 / ATINGIDA; `--classe porca --alvo 4` → exibe 4 / ATINGIDA. Conferir no "bruto" que a outra classe está sendo detectada mas não somada.
- [ ] Repetir o 7.4.2 com peças encostadas (lado a lado) e anotar a contagem (ponto fraco conhecido do modelo B).
- [ ] Colocar um objeto estranho (bit, chave) junto → verificar se vira parafuso falso (ponto fraco do modelo A).
- [ ] Mão entrando na bandeja durante a contagem → anotar o que acontece com o estado.
- [ ] `--modelo nao_existe.pt` → `MODELO NÃO CARREGADO`, sem travar.
- [ ] Desconectar a webcam com o script rodando → `ERRO DE CÂMERA`, sem travar.
