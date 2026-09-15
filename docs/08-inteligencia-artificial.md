# Inteligência Artificial

## Tipo de problema

**Object Detection** (bounding boxes), não segmentação — salvo se testes mostrarem que
bounding boxes são insuficientes.

## Classes iniciais

```text
0 = parafuso
1 = porca
```

Nenhuma outra classe faz parte da v1 (arruelas e outros componentes são expansão futura —
ver [Pontos em aberto e expansões](14-pontos-em-aberto-e-expansoes.md)).

## Modelo inicial recomendado

Baseline: **YOLO26n**.

Motivos:

- leve;
- adequado para inferência em computadores modestos;
- apenas duas classes;
- ambiente controlado;
- câmera fixa;
- iluminação padronizada.

Se a precisão for insuficiente:

```text
YOLO26n
   ↓
analisar dataset e erros
   ↓
YOLO26s
```

Não aumentar o modelo antes de verificar a qualidade do dataset.

## Treinamento e inferência são separados

O computador de treinamento não precisa ser o mesmo computador do aplicativo.

```text
PC DE TREINAMENTO
      ↓
dataset
      ↓
treinamento YOLO
      ↓
best.pt
      ↓
opcionalmente exportar
      ↓
best.onnx
      ↓
copiar modelo
      ↓
PC DO PROTÓTIPO
      ↓
carrega modelo treinado
      ↓
somente inferência
```

## Dataset

Criado preferencialmente usando a própria configuração física do protótipo.

### Variações recomendadas

- diferentes quantidades de parafusos;
- diferentes quantidades de porcas;
- parafusos + porcas;
- posições diferentes;
- rotações diferentes;
- objetos próximos;
- objetos parcialmente encostados;
- objetos próximos às bordas;
- bandeja vazia.

### Quantidade inicial sugerida

```text
200 a 500 imagens variadas
```

Apenas uma referência inicial — priorizar diversidade e qualidade de anotação.

### Anotação

Cada item deve possuir bounding box e classe correta.

### Estrutura sugerida

```text
dataset/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
│
└── labels/
    ├── train/
    ├── val/
    └── test/
```

### Exemplo de `dataset.yaml`

```yaml
path: C:/Projetos/contador_componentes/dataset

train: images/train
val: images/val
test: images/test

names:
  0: parafuso
  1: porca
```

## Região de interesse — ROI

Como a câmera e a bandeja permanecem fixas, o sistema deve considerar o uso de ROI.

```text
Imagem completa
      ↓
recorte da bandeja
      ↓
imagem da área útil
      ↓
YOLO
```

Vantagens: reduz processamento, elimina elementos externos, aumenta consistência, pode
melhorar desempenho.

## Estabilização da contagem

A contagem pode oscilar entre frames:

```text
Frame 1 → 19
Frame 2 → 20
Frame 3 → 19
Frame 4 → 20
Frame 5 → 20
```

O sistema deve evitar alternância constante de status.

Baseline sugerido:

```text
Quantidade alvo detectada
por N frames consecutivos
        ↓
QUANTIDADE ATINGIDA
```

Valor inicial sugerido: **N = 5**. Deve ser validado experimentalmente.
