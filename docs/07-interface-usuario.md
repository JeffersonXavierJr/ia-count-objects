# Interface do Usuário

O **Home Assistant** é, preferencialmente, a única interface do operador — não deve existir
uma interface web/desktop separada.

## Configuração

- selecionar `Parafuso` ou `Porca`;
- informar quantidade desejada;
- reiniciar a contagem.

## Monitoramento

- visualizar câmera;
- visualizar bounding boxes;
- visualizar quantidade atual;
- visualizar quantidade desejada;
- visualizar status.

## Exemplo de layout

```text
┌──────────────────────────────────┐
│      CONTAGEM DE COMPONENTES     │
├──────────────────────────────────┤
│                                  │
│        [ CÂMERA AO VIVO ]        │
│                                  │
│    □parafuso     □parafuso       │
│         □parafuso                │
│                                  │
├──────────────────────────────────┤
│ Componente:        Parafuso      │
│ Quantidade alvo:   20            │
│ Detectado:         17            │
│ Status: CONTANDO                 │
└──────────────────────────────────┘
```

Quando atingir o valor:

```text
Detectado: 20
Status: QUANTIDADE ATINGIDA
```

O layout final do dashboard ainda não está definido (ver
[Pontos em aberto](14-pontos-em-aberto-e-expansoes.md)) — o exemplo acima é conceitual.
