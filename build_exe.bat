@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

echo Instalando o PyInstaller...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto erro

echo.
echo Gerando a versao com bandeja, sem console...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name LembretesSaude --hidden-import tray lembretes.py
if errorlevel 1 goto erro

echo.
echo Gerando a versao de linha de comando...
%PY% -m PyInstaller --noconfirm --clean --onefile --console ^
    --name LembretesSaude-cli --hidden-import tray lembretes.py
if errorlevel 1 goto erro

echo.
echo Executaveis gerados em dist\
echo  - dist\LembretesSaude.exe
echo  - dist\LembretesSaude-cli.exe
echo.
echo Para personalizar, copie config.exemplo.json como config.json
echo na mesma pasta do executavel.
exit /b 0

:erro
echo.
echo Falha ao gerar os executaveis.
exit /b 1
