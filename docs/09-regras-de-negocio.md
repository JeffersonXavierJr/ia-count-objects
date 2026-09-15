# Regras de Negócio

## RB-01 — Contar somente a classe selecionada

```text
Selecionado: Parafuso

Imagem:
12 parafusos
4 porcas

Quantidade exibida: 12
```

## RB-02 — Comparação contínua

Comparar continuamente quantidade detectada e quantidade requisitada.

## RB-03 — Estados do sistema

Estados mínimos:

```text
AGUARDANDO CONFIGURAÇÃO
CONTANDO
QUANTIDADE ATINGIDA
```

Estados de erro opcionais:

```text
ERRO DE CÂMERA
MODELO NÃO CARREGADO
```

## RB-04 — Descarga manual

A descarga física ocorre manualmente após a indicação de quantidade atingida.

## RB-05 — Reinício da contagem

Após a descarga, deve existir forma de reiniciar a contagem.

Baseline recomendado: botão **RESET** no Home Assistant.
