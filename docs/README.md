# Documentação do Projeto

Índice da documentação do **Sistema Inteligente de Identificação e Contagem de Componentes**.

Esta pasta organiza, por tema, o conteúdo já definido em [`PRD.md`](../PRD.md), que é a
**fonte de verdade do projeto**. Em caso de conflito entre qualquer documento aqui e o PRD,
o PRD prevalece.

O projeto está em fase de **planejamento** — não há código, dataset ou ferramentas de build
implementados ainda. Esta documentação descreve o que já foi decidido, não funcionalidades
futuras ou hipotéticas.

## Sumário

1. [Visão geral](01-visao-geral.md) — resumo executivo, problema, objetivos.
2. [Escopo da v1](02-escopo.md) — o que entra e o que fica fora da primeira versão.
3. [Arquitetura](03-arquitetura.md) — arquitetura lógica, física e estrutura de módulos.
4. [Estrutura física](04-estrutura-fisica.md) — bandeja, fundo deslizante, rampa.
5. [Fluxo operacional](05-fluxo-operacional.md) — passo a passo de uso.
6. [Comunicação](06-comunicacao.md) — MQTT e transmissão de vídeo.
7. [Interface do usuário](07-interface-usuario.md) — Home Assistant como interface única.
8. [Inteligência artificial](08-inteligencia-artificial.md) — classes, modelo, dataset, ROI, estabilização.
9. [Regras de negócio](09-regras-de-negocio.md) — regras e estados do sistema.
10. [Requisitos](10-requisitos.md) — requisitos funcionais e não funcionais.
11. [Diretrizes de desenvolvimento](11-diretrizes-de-desenvolvimento.md) — padrões, ordem de build, o que não presumir.
12. [Materiais e impressão 3D](12-materiais-e-impressao-3d.md) — lista de materiais e peças impressas.
13. [Equipe](13-equipe.md) — integrantes e responsabilidades.
14. [Pontos em aberto e expansões futuras](14-pontos-em-aberto-e-expansoes.md) — o que ainda não foi decidido.
15. [Diagrama de arquitetura](diagrama_arquitetura_contagem_componentes.md) — diagrama Mermaid detalhado.

## Referência

- [`PRD.md`](../PRD.md) — documento de requisitos completo (fonte de verdade).
- [`CLAUDE.md`](../CLAUDE.md) — guia para assistentes de IA que trabalharem neste repositório.
