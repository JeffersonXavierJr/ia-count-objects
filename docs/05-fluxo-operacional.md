# Fluxo Operacional

```text
INÍCIO
  ↓
Usuário acessa Home Assistant
  ↓
Seleciona o tipo de componente
  ↓
Define a quantidade desejada
  ↓
Usuário adiciona componentes à bandeja
  ↓
Câmera captura continuamente
  ↓
IA identifica os objetos
  ↓
Sistema conta a classe selecionada
  ↓
Quantidade detectada < quantidade desejada?
  ├── SIM → continua contando
  └── NÃO
        ↓
Home Assistant informa
"QUANTIDADE ATINGIDA"
        ↓
Usuário puxa o fundo deslizante
        ↓
Componentes caem na rampa
        ↓
Rampa direciona ao recipiente
        ↓
Usuário fecha novamente o fundo
        ↓
Nova contagem pode ser iniciada
```

## Cenário de uso de referência

```text
Componente selecionado: Parafuso
Quantidade desejada: 20

Detectado: 14
Status: CONTANDO

Detectado: 17
Status: CONTANDO

Detectado: 19
Status: CONTANDO

Detectado: 20
Status: QUANTIDADE ATINGIDA
```

Após isso, o usuário descarrega manualmente os componentes.
