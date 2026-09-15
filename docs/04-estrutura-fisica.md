# Estrutura Física

## Componentes da estação

1. suporte estrutural;
2. câmera posicionada acima;
3. bandeja fixa;
4. iluminação uniforme;
5. fundo deslizante;
6. rampa afunilada;
7. recipiente de coleta.

## Representação conceitual

```text
                  CÂMERA
                     ↓
             ┌───────────────┐
             │    BANDEJA    │
             │  🔩  🔩  ⬡    │
             │               │
             ├───────────────┤ ← fundo deslizante
             └───────┬───────┘
                     ↓
                componentes
                   caem
                     ↓
                ┌────────┐
                │ RAMPA  │
                │ \    / │
                │  \  /  │
                │   \/   │
                └────┬───┘
                     ↓
                RECIPIENTE
```

## Bandeja

Permanece fixa durante toda a contagem.

Requisitos:

- área interna totalmente visível pela câmera;
- bordas suficientes para impedir que os componentes escapem;
- superfície com bom contraste em relação aos objetos;
- geometria adequada para impressão 3D;
- fundo independente da estrutura lateral.

## Fundo deslizante

Placa que desliza horizontalmente.

- **Fechado:** sustenta os componentes durante a inspeção.
- **Aberto:** ao ser puxado manualmente, libera os componentes para a rampa.

Requisitos:

- movimentação suave;
- pequena folga mecânica;
- puxador acessível;
- trilhos/guias;
- abertura suficiente para descarregar todos os componentes.

## Rampa

Fica imediatamente abaixo da bandeja.

Funções:

- receber os componentes;
- impedir espalhamento;
- conduzir os objetos por gravidade;
- afunilar a saída;
- direcionar os componentes ao recipiente.

A abertura do fundo é sempre **manual** — não há automação mecânica na v1 (ver
[Escopo](02-escopo.md)).
