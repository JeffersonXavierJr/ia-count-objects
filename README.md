# Sistema Inteligente de Identificação e Contagem de Componentes

Sistema para identificação e contagem automática de componentes (parafusos e porcas) usando
visão computacional (YOLO) e integração com Home Assistant via MQTT.

A documentação completa e autoritativa do projeto está em [`PRD.md`](./PRD.md). As diretrizes de
desenvolvimento para agentes/colaboradores estão em [`CLAUDE.md`](./CLAUDE.md). O planejamento de
tarefas por sprint está em [`TASKS.md`](./TASKS.md).

## Ambiente

- **Python**: 3.12.x (testado com 3.12.9). Todo o time deve padronizar nessa versão.
- Ambiente virtual do projeto: `venv/` (criado na raiz do repositório via `python -m venv venv`).
- Dependências: ver [`requirements.txt`](./requirements.txt).

## Estrutura do projeto

O código da aplicação vive em `contador_componentes/`, organizado em `app/` (aplicação Python),
`training/` (treinamento do modelo YOLO), `models/` (pesos treinados), `dataset/` (imagens e
rótulos) e `tests/`. Veja a seção 20 do `PRD.md` para detalhes.

Pesos de modelo (`*.pt`, `*.onnx`) e as imagens/rótulos do dataset **não são versionados no Git**
(ver `.gitignore`) — são artefatos binários volumosos, gerados/capturados localmente, e não
código-fonte. Apenas a estrutura de pastas é mantida (via `.gitkeep`).

## Convenção de commits

Seguindo o padrão já usado no histórico do projeto, as mensagens de commit devem usar o formato
[Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>: <descrição curta no imperativo>
```

Tipos usados neste repositório:

- `feat`: nova funcionalidade (ex.: `feat: implementar captura de frame via webcam`)
- `fix`: correção de bug
- `docs`: mudanças em documentação (`README.md`, `PRD.md`, `TASKS.md`, comentários)
- `chore`: tarefas de manutenção sem impacto em código de produção (ex.: configurar `.gitignore`, dependências)
- `refactor`: mudança de código que não corrige bug nem adiciona funcionalidade
- `test`: adição ou ajuste de testes

Regras:

- Descrição em português, no imperativo (ex. "adicionar", não "adicionado" ou "adicionando").
- Use `docs` (não `doc`) para manter consistência — normalizando o único commit anterior que usou `doc:`.
- Prefira commits pequenos e focados em uma sub-tarefa do `TASKS.md` por vez.
