@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Ambiente Python nao encontrado na pasta do projeto.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" -m contador_componentes.app.main
if errorlevel 1 (
    echo.
    echo O aplicativo encontrou um erro. Veja a mensagem acima.
    pause
    exit /b 1
)
