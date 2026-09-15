# Visão Geral

## Resumo de uma frase

> Sistema local de visão computacional que utiliza uma webcam, Python, OpenCV e YOLO para
> identificar e contar parafusos ou porcas colocados em uma bandeja fixa, recebe a quantidade
> desejada e apresenta vídeo, contagem e status no Home Assistant, permitindo posteriormente a
> descarga manual dos componentes por um fundo deslizante para uma rampa afunilada e recipiente.

## Resumo executivo

Estação inteligente para identificação e contagem automática de pequenos componentes,
inicialmente **parafusos** e **porcas**.

Os componentes são colocados manualmente por um usuário em uma **bandeja fixa**, posicionada
abaixo de uma câmera. Um computador executa um software em Python, usando OpenCV e um modelo
YOLO treinado, para:

1. capturar a imagem;
2. identificar os componentes;
3. classificar cada item;
4. contar os objetos da classe selecionada;
5. comparar a quantidade detectada com a quantidade requisitada.

O usuário configura, pelo Home Assistant, qual componente deseja contar e qual quantidade
deseja atingir. Quando a quantidade desejada é alcançada, o Home Assistant informa que a
contagem foi concluída.

A bandeja possui um **fundo deslizante manual**. Após a confirmação da quantidade, o usuário
puxa esse fundo e os componentes caem por gravidade em uma **rampa afunilada**, que os
direciona para um recipiente. A primeira versão não possui automação mecânica da descarga.

## Problema

A contagem manual de pequenos componentes como parafusos e porcas é repetitiva, demorada e
sujeita a erros humanos. Em processos de montagem, separação de kits ou preparação de
materiais, uma contagem incorreta pode causar:

- kits incompletos;
- retrabalho;
- necessidade de nova conferência;
- desperdício de tempo;
- erros de abastecimento;
- redução da confiabilidade do processo.

O projeto automatiza a identificação e contagem usando visão computacional, mantendo a
operação física simples e de baixo custo.

## Objetivo geral

Desenvolver um sistema inteligente capaz de identificar e contar automaticamente componentes
por visão computacional, permitindo ao usuário selecionar o tipo de componente e a quantidade
desejada através do Home Assistant.

## Objetivos específicos

- Capturar imagens de uma bandeja de inspeção através de uma webcam.
- Manter câmera, iluminação e bandeja em posições padronizadas.
- Utilizar Python como linguagem principal.
- Utilizar OpenCV para aquisição e manipulação das imagens.
- Treinar um modelo YOLO para identificar parafusos e porcas.
- Realizar automaticamente a contagem dos componentes detectados.
- Permitir ao usuário selecionar o tipo de componente.
- Permitir ao usuário definir a quantidade desejada.
- Comparar a quantidade identificada com a quantidade solicitada.
- Informar em tempo real o progresso da contagem.
- Informar quando a quantidade desejada for atingida.
- Exibir o vídeo da bandeja no Home Assistant.
- Exibir as marcações dos objetos identificados sobre o vídeo ou imagem.
- Utilizar MQTT para troca de informações entre os serviços.
- Utilizar HTTP/MJPEG ou RTSP para disponibilização do vídeo.
- Criar uma bandeja com fundo deslizante para descarga manual.
- Criar uma rampa afunilada para direcionar os componentes ao recipiente.
- Construir a maior parte da estrutura por impressão 3D.
- Permitir expansão futura para outros componentes.
