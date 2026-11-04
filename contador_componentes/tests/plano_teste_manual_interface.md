# Plano de teste manual da interface — tarefas 9.3.1 a 9.3.4

Roteiro para o time validar a janela Tkinter **com a webcam e as peças reais**. A lógica já é
coberta por testes automatizados (`test_interface_integracao.py`, com câmera e detector falsos);
este roteiro confirma o que só o hardware real mostra: o modelo contando as peças de verdade, a
webcam sendo desconectada e o tempo de reação na tela.

Todos os comandos são rodados **na raiz do repositório** (`ia-count-objects`), no PowerShell:

```powershell
cd C:\Users\jejun\programs\ia-count-objects
venv\Scripts\activate
```

Para abrir a aplicação:

```powershell
venv\Scripts\python.exe -m contador_componentes.app.main
```

Para fechar, use o **X** da janela. O terminal mostra o log (troca de configuração, reset, erros
de câmera ou de modelo). Deixe-o visível durante o teste.

---

## Antes de começar

| Item | Como conferir | OK? |
|---|---|---|
| `contador_componentes\models\best.pt` é o modelo escolhido (PENDENCIAS_HUMANAS item 1) | anotar qual modelo é | ☐ |
| Webcam conectada e **nenhum outro programa** usando a câmera (Câmera do Windows, Teams, Zoom) | LED da webcam apagado antes de abrir o app | ☐ |
| ROI calibrada (PENDENCIAS_HUMANAS item 3) ou anotar que está `ROI = None` (frame inteiro) | `ROI` em `contador_componentes/app/config.py` | ☐ |
| Iluminação e posição da câmera iguais às do treino/validação | — | ☐ |
| Peças separadas: pelo menos **12 parafusos e 4 porcas** | — | ☐ |

Valores atuais que afetam o que você vai ver (todos em `contador_componentes/app/config.py`):

- `FRAMES_ESTABILIZACAO = 5`: o status só muda para `QUANTIDADE ATINGIDA`/`EXCEDIDA` depois de
  5 frames seguidos com o mesmo resultado. É um **ponto em aberto** (tarefa 8.2): anote se a
  espera parecer longa ou curta demais.
- `INTERVALO_RECONEXAO_CAMERA_S = 2.0`: com a webcam com falha, o app tenta reabrir a cada 2 s.
- Resolução: o PRD (seção 28) define 1080p/30fps, mas o app hoje abre a webcam na resolução
  padrão do driver (640x480 neste PC). Anote a resolução que o vídeo mostra.
- Referência de desempenho (smoke test do QA em 28/10/2026, neste PC, sem janela, `ROI = None`,
  captura de **640x480**): **~8,6 FPS**. Ou seja, 5 frames levam cerca de **0,6 s**. Com a janela
  aberta o FPS pode ser um pouco menor.

> **Contagem errada x status errado.** Se o número de peças exibido estiver errado (por
> exemplo, 11 com 12 parafusos na bandeja), isso é um problema do modelo/dataset: anote, tire
> uma foto e siga em frente. Se o número estiver **certo** e o status ou a quantidade desejada
> estiverem errados, isso é bug de código: anote os passos exatos e avise.

Ao preencher os resultados, use **OK**, **FALHOU** ou **N/A**, com uma observação curta.

---

## 9.3.1 — Trocar o componente e ver a contagem mudar

**Montagem:** 12 parafusos + 4 porcas na bandeja, **separados** (sem encostar uns nos outros).

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Abrir o app, sem selecionar nada | Vídeo ao vivo com caixas em **todas** as peças. Status `AGUARDANDO CONFIGURAÇÃO`. Detectada `—`, desejada `—` | |
| 2 | Clicar em **Parafuso** (sem quantidade) | Detectada **12**, status ainda `AGUARDANDO CONFIGURAÇÃO`. Caixas **só nos parafusos** | |
| 3 | Digitar `12` no campo e apertar **Enter** | Desejada **12**. `CONTANDO` (com "estabilizando k/5") e depois `QUANTIDADE ATINGIDA` em menos de ~1 s | |
| 4 | Clicar em **Porca** | Detectada **4** quase na hora, desejada 12, status `CONTANDO`. Caixas **só nas porcas** | |
| 5 | Mudar a quantidade para `4` + Enter | `QUANTIDADE ATINGIDA` após ~5 frames | |
| 6 | Clicar em **Parafuso** de novo (desejada continua 4) | Detectada 12, `CONTANDO` por um instante e depois `QUANTIDADE EXCEDIDA` | |
| 7 | Alternar Parafuso ↔ Porca rapidamente umas 5 vezes | A janela **não trava**. A contagem sempre corresponde à classe marcada | |

**Como validar:** os passos 2, 4 e 6 mostram a contagem da classe marcada e ignoram a outra
(RB-01). Nenhuma troca exigiu reiniciar o app.

---

## 9.3.2 — Alterar a quantidade desejada em tempo real

**Montagem:** 12 parafusos na bandeja, **Parafuso** selecionado.

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Quantidade `20` + Enter | Desejada **20**, status `CONTANDO`, sem "estabilizando" | |
| 2 | Quantidade `12` + Enter | Desejada **12** na hora. "estabilizando 1/5 … 4/5" e depois `QUANTIDADE ATINGIDA` | |
| 3 | Com `QUANTIDADE ATINGIDA` na tela, quantidade `10` + Enter | Desejada **10**. O status passa por `CONTANDO` (não fica "atingida" antiga) e depois `QUANTIDADE EXCEDIDA` | |
| 4 | Usar a **seta para cima** do campo duas vezes (10 → 12) | Desejada acompanha cada clique (11, 12). Termina em `QUANTIDADE ATINGIDA` | |
| 5 | Digitar `11` no campo sem apertar Enter e apertar **Tab** (tirar o foco do campo) | A desejada vira 11 ao sair do campo. Se não mudar, anote: só o Enter e as setas confirmam | |
| 6 | Tentar digitar `0`, `-3`, `abc`, `1.5` | O campo **não aceita** os caracteres; nada muda no painel | |
| 7 | Apagar o campo e apertar Enter | Desejada `—`, status `AGUARDANDO CONFIGURAÇÃO` | |
| 8 | Conferir o terminal | Uma linha "Configuracao alterada" por mudança. **Nenhuma** linha "Camera aberta" ou "Modelo carregado" nova (o app não reiniciou) | |

---

## 9.3.3 — Botão RESET e nova contagem (RB-05)

**Montagem:** 12 parafusos na bandeja, **Parafuso** selecionado, quantidade 12, status
`QUANTIDADE ATINGIDA`.

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Clicar em **RESET** com as peças na bandeja | Status volta a `CONTANDO` ("estabilizando 1/5") e, ~5 frames depois, `QUANTIDADE ATINGIDA` de novo. Componente e quantidade **continuam** marcados | |
| 2 | Fazer a **descarga manual** (puxar o fundo da bandeja) | Detectada **0**, status `CONTANDO` | |
| 3 | Clicar em **RESET** | Desejada continua 12, Parafuso continua marcado, status `CONTANDO` | |
| 4 | Recolocar 12 parafusos, um por um | A detectada sobe peça a peça. `QUANTIDADE ATINGIDA` só quando as 12 estiverem paradas | |
| 5 | Clicar em RESET várias vezes seguidas | Nada trava. O comportamento é o mesmo de um único RESET | |
| 6 | Repetir o ciclo (descarga → RESET → 12 peças) 3 vezes | Todas as vezes chega a `QUANTIDADE ATINGIDA` | |

> **Ponto em aberto (PRD seção 29, item 14):** o método definitivo de reset ainda não foi decidido.
> Hoje o RESET é necessário? Anote se o time achou que o reset deveria ser automático após a
> descarga, já que a contagem volta a `CONTANDO` sozinha quando a bandeja esvazia.

---

## 9.3.4 — Câmera com falha e modelo ausente

### A. Webcam desconectada

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Com o app contando (Parafuso, 12, `QUANTIDADE ATINGIDA`), **desconectar o cabo USB** da webcam | Em poucos segundos: `ERRO DE CÂMERA` (selo vermelho), vídeo com "Sem imagem da câmera", detectada `—`, desejada continua 12. A janela **não trava** | Tempo até o erro: ___ s |
| 2 | Com o cabo desconectado, trocar o componente e a quantidade | Os controles respondem. A desejada é atualizada (pode levar até ~2 s) | |
| 3 | **Reconectar** o cabo na mesma porta | Em até ~2–5 s o vídeo volta, `CONTANDO` e depois `QUANTIDADE ATINGIDA`. Sem reiniciar o app | Tempo até voltar: ___ s |
| 4 | Fechar o app; desconectar a webcam; abrir o app de novo | Janela abre com `ERRO DE CÂMERA`. Reconectando, passa a contar | |
| 5 | Abrir o app do Windows **Câmera** (para ocupar a webcam) e depois abrir o contador | `ERRO DE CÂMERA`. Ao fechar o app Câmera, o contador passa a contar sozinho | |

> Se no passo 1 a janela **congelar** (vídeo parado sem aparecer `ERRO DE CÂMERA`), anote
> quanto tempo ficou parada: alguns drivers do Windows demoram a reportar a falha da leitura.
> Isso só se descobre com o hardware real.

### B. Modelo ausente

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Fechar o app e renomear o modelo: `Rename-Item contador_componentes\models\best.pt best.pt.bak` | — | |
| 2 | Abrir o app | Janela abre com `MODELO NÃO CARREGADO` (selo vermelho) e "Sem imagem da câmera". O terminal mostra "Arquivo do modelo nao encontrado". O LED da webcam **não** acende | |
| 3 | Selecionar Porca, quantidade 4 + Enter, clicar RESET | Os controles respondem, a desejada vira 4 (pode levar até ~2 s), o status continua `MODELO NÃO CARREGADO` | |
| 4 | Fechar pelo X | Fecha em até ~3 s, sem erro no terminal | |
| 5 | **Restaurar** o modelo: `Rename-Item contador_componentes\models\best.pt.bak best.pt` e abrir o app | Volta a contar normalmente | |

> O app **não** tenta recarregar o modelo sozinho: depois de copiar o `best.pt`, é preciso
> reiniciar o app. Esse é o comportamento previsto, não uma falha.

---

## Fechamento da janela (todas as seções)

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Fechar pelo **X** com o app contando | Fecha em até ~3 s. LED da webcam apaga. O terminal mostra "Camera liberada" e "Aplicacao encerrada" | |
| 2 | Abrir o app de novo logo em seguida | A webcam abre normalmente (prova que foi liberada) | |

---

## Registro

| Data | Quem | Computador | Modelo (`best.pt`) | ROI | FPS percebido | Resultado geral |
|---|---|---|---|---|---|---|
| | | | | | | |

**Como concluir:** se todos os passos estiverem **OK** (contagem errada por causa do modelo não
reprova a 9.3, apenas registre), marque **9.3.1–9.3.4** e **9.3** no `TASKS.md`. Falhas de
status ou de controle devem ser reportadas ao time de desenvolvimento, com os passos exatos.
