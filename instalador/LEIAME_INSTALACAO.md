# Instalação do Contador de Componentes no PC final

Pacote autocontido (PyInstaller, modo pasta): **o PC final não precisa de Python**.
Contém só o necessário para a inferência — sem dataset, treino, testes nem scripts de captura.

## Requisitos do PC final

- Windows 10 ou 11, **64 bits**.
- Webcam USB (índice padrão 0).
- Cerca de 1,5 GB livres.
- **Não** é preciso instalar o Visual C++ Redistributable: as DLLs de runtime necessárias
  (`vcruntime140*.dll`, `msvcp140*.dll`) vão dentro do pacote.
- Roda em CPU (o pacote usa o torch de CPU). A especificação do PC final ainda está em aberto
  (PRD 29.13); medir FPS lá (TASKS 11.3).

## 1. Gerar o pacote (máquina de desenvolvimento)

Na raiz do repositório, no PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File instalador\build.ps1
```

O script cria um venv de build separado (`instalador\venv_build\`, só dependências de inferência),
roda os testes, gera o executável e copia o modelo atual de `contador_componentes\models\`.
Saídas em `dist\`:

| Arquivo | Uso |
|---|---|
| `dist\Instalar_ContadorComponentes.exe` | instalador (gerado só se o Inno Setup 6 estiver instalado) |
| `dist\ContadorComponentes.zip` | a mesma pasta compactada, para instalar sem instalador |
| `dist\ContadorComponentes\` | pasta do programa |

Para diagnosticar erros de inicialização, gere com console: `...\build.ps1 -Console`.

> O modelo empacotado é o `contador_componentes\models\best.pt` atual. A escolha do modelo final
> ainda é pendência do time (`PENDENCIAS_HUMANAS.md`, item 1).

## 2. Instalar na próxima máquina

**Com o instalador:** copie `Instalar_ContadorComponentes.exe` e execute. Não pede administrador:
instala em `%LOCALAPPDATA%\Programs\ContadorComponentes` e cria atalhos no Menu Iniciar
(“Contador de Componentes”, “Calibrar ROI da camera”, “Pasta do programa”) e, se marcado, na
Área de Trabalho. O Windows SmartScreen pode avisar (executável não assinado): “Mais
informações” → “Executar assim mesmo”.

**Com o zip:** extraia `ContadorComponentes.zip` numa pasta **com permissão de escrita** (ex.:
`C:\ContadorComponentes`, não em `C:\Program Files`) e abra `ContadorComponentes.exe`.

A primeira abertura demora alguns segundos (carregamento do torch/modelo).
Sem webcam a janela abre mostrando `ERRO DE CÂMERA`; sem modelo, `MODELO NÃO CARREGADO`.
Erros ficam em `ContadorComponentes.log`, ao lado do `.exe` (sobrescrito a cada execução).

## 3. Trocar o modelo (sem gerar o pacote de novo)

Feche o programa e substitua `models\best.pt` na pasta do programa pelo novo modelo
(classes 0 = parafuso, 1 = porca). Se não houver `best.pt` mas houver `models\best.onnx`, o
`.onnx` é usado — porém o suporte a ONNX só vai no pacote se ele tiver sido gerado com um
`best.onnx` presente em `contador_componentes\models\` (o build instala o `onnxruntime` nesse caso).
O formato final `.pt` × `.onnx` ainda está em aberto (TASKS 11.2.3).

Reinstalar com um pacote novo **sobrescreve** `models\`.

## 4. Calibrar a ROI e escolher a câmera

A ROI e o índice da câmera ficam em `config_local.json`, ao lado do `.exe` (opcional; sem ele valem
os padrões: câmera 0 e ROI desativada). Reinstalar **não** apaga esse arquivo.

**ROI:** com a câmera na posição definitiva, use o atalho “Calibrar ROI da camera” (ou
`ContadorComponentes.exe --calibrar-roi`). Ajuste o retângulo sobre a bandeja (mouse; `w a s d`
movem, `j/l` largura, `i/k` altura, `f` passo, `r` frame inteiro), pressione **P** ou **Enter**
para gravar e **Q**/Esc para sair. Uma mensagem confirma onde a ROI foi gravada. Reabra o programa.

**Câmera:** se a webcam não for o dispositivo 0, edite (ou crie a partir de
`config_local.exemplo.json`):

```json
{
  "camera_index": 1,
  "roi": [x, y, largura, altura]
}
```

`roi` pode ser `null` (frame inteiro). Valor inválido é ignorado (usa o padrão) e registrado no log.
Se a câmera, a altura dela ou a resolução de captura mudarem, recalibre a ROI.
