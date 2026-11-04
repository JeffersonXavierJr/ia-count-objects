<#
.SYNOPSIS
  Gera o pacote do Contador de Componentes para o PC final (Sprint 11, tarefa 11.1.3).

.DESCRIPTION
  1. Cria/atualiza o venv de build SEPARADO (instalador\venv_build) so com as
     dependencias de inferencia (instalador\requirements_build.txt).
  2. Roda os testes (python -m pytest contador_componentes/tests -q) nesse venv.
  3. Gera dist\ContadorComponentes\ContadorComponentes.exe (PyInstaller, one-folder).
  4. Copia o modelo (models\best.pt e/ou best.onnx) para FORA do exe:
     dist\ContadorComponentes\models\
  5. Gera dist\ContadorComponentes.zip.
  6. Se o Inno Setup 6 (ISCC.exe) existir, gera dist\Instalar_ContadorComponentes.exe.

  Uso (na raiz do repositorio, PowerShell):
    powershell -ExecutionPolicy Bypass -File instalador\build.ps1
    powershell -ExecutionPolicy Bypass -File instalador\build.ps1 -Console   # exe com console (diagnostico)

.PARAMETER Console
  Gera o exe com janela de console (mostra erros de import/log). Para o PC final, gere sem -Console.
.PARAMETER Python
  Interpretador Python 3.12 usado para criar o venv de build (padrao: "py -3.12", ou "python").
#>
param(
    [switch]$Console,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
# O PyInstaller importa submodulos do ultralytics durante a analise; sem isto o
# ultralytics tenta instalar dependencias opcionais (ex.: lap) via pip no venv de build.
$env:YOLO_AUTOINSTALL = "false"
$env:YOLO_OFFLINE = "true"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Raiz

$VenvBuild = Join-Path $PSScriptRoot "venv_build"
$Py = Join-Path $VenvBuild "Scripts\python.exe"
$Dist = Join-Path $Raiz "dist"
$Pacote = Join-Path $Dist "ContadorComponentes"
$ModelosOrigem = Join-Path $Raiz "contador_componentes\models"

function Etapa($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Executar([string]$exe, [string[]]$argumentos) {
    & $exe @argumentos
    if ($LASTEXITCODE -ne 0) { throw "Falhou (codigo $LASTEXITCODE): $exe $($argumentos -join ' ')" }
}

# --- 0. Modelo presente? --------------------------------------------------
$Modelos = @("best.pt", "best.onnx") | ForEach-Object { Join-Path $ModelosOrigem $_ } | Where-Object { Test-Path $_ }
if (-not $Modelos) {
    throw "Nenhum modelo em $ModelosOrigem (best.pt ou best.onnx). Copie o modelo validado antes de gerar o pacote."
}
Write-Host "AVISO: sera empacotado o modelo atual de contador_componentes\models\ ($((($Modelos | Split-Path -Leaf) -join ', '))). A escolha do modelo final ainda e pendencia do time (PENDENCIAS_HUMANAS.md, item 1)." -ForegroundColor Yellow

# --- 1. venv de build -----------------------------------------------------
Etapa "Preparando venv de build (somente inferencia): $VenvBuild"
if (-not (Test-Path $Py)) {
    if ($Python) { $criador = @($Python) }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $criador = @("py", "-3.12") }
    else { $criador = @("python") }
    $cmd = $criador[0]; $resto = @($criador | Select-Object -Skip 1)
    Executar $cmd ($resto + @("-m", "venv", $VenvBuild))
}
$versao = & $Py -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($versao -ne "3.12") { throw "O venv de build usa Python $versao; o projeto padroniza Python 3.12 (README). Apague $VenvBuild e rode de novo com -Python <caminho do python 3.12>." }

Executar $Py @("-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", (Join-Path $PSScriptRoot "requirements_build.txt"))
if (Test-Path (Join-Path $ModelosOrigem "best.onnx")) {
    # Necessario so para carregar .onnx (formato final ainda em aberto, PRD 29.14).
    Executar $Py @("-m", "pip", "install", "--disable-pip-version-check", "-q", "onnxruntime")
}

# --- 2. Testes --------------------------------------------------------------
Etapa "Rodando os testes"
Executar $Py @("-m", "pytest", "contador_componentes/tests", "-q")

# --- 3. PyInstaller ---------------------------------------------------------
Etapa "Gerando o executavel (PyInstaller, one-folder)"
if ($Console) { $env:CONTADOR_CONSOLE = "1" } else { $env:CONTADOR_CONSOLE = "0" }
try {
    Executar $Py @("-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", $Dist, "--workpath", (Join-Path $Raiz "build"),
        (Join-Path $PSScriptRoot "contador_componentes.spec"))
} finally {
    Remove-Item Env:\CONTADOR_CONSOLE -ErrorAction SilentlyContinue
}

# --- 4. Modelo e arquivos editaveis FORA do exe ----------------------------
Etapa "Copiando o modelo para $Pacote\models"
$ModelosDestino = Join-Path $Pacote "models"
New-Item -ItemType Directory -Force -Path $ModelosDestino | Out-Null
foreach ($m in $Modelos) { Copy-Item $m $ModelosDestino -Force }
Copy-Item (Join-Path $PSScriptRoot "config_local.exemplo.json") $Pacote -Force
Copy-Item (Join-Path $PSScriptRoot "LEIAME_INSTALACAO.md") $Pacote -Force

# --- 5. Zip -----------------------------------------------------------------
Etapa "Gerando o zip"
$Zip = Join-Path $Dist "ContadorComponentes.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($Pacote, $Zip, [System.IO.Compression.CompressionLevel]::Optimal, $true)

# --- 6. Instalador (Inno Setup, opcional) ----------------------------------
$Iscc = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($Iscc) {
    Etapa "Gerando o instalador com Inno Setup ($Iscc)"
    $versaoApp = Get-Date -Format "yyyy.MM.dd"
    Executar $Iscc @("/Q", "/DSourceDir=$Pacote", "/DOutputDir=$Dist", "/DMyAppVersion=$versaoApp",
        (Join-Path $PSScriptRoot "instalador.iss"))
} else {
    Write-Host "AVISO: Inno Setup 6 (ISCC.exe) nao encontrado; instalador .exe NAO gerado. Use o zip." -ForegroundColor Yellow
}

# --- Resumo -----------------------------------------------------------------
$tamPasta = (Get-ChildItem $Pacote -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Etapa "Pronto"
Write-Host ("Pasta : {0} ({1:N0} MB)" -f $Pacote, $tamPasta)
Write-Host ("Zip   : {0} ({1:N0} MB)" -f $Zip, ((Get-Item $Zip).Length / 1MB))
$Setup = Join-Path $Dist "Instalar_ContadorComponentes.exe"
if (Test-Path $Setup) { Write-Host ("Setup : {0} ({1:N0} MB)" -f $Setup, ((Get-Item $Setup).Length / 1MB)) }
