@echo off
chcp 65001 >nul
title Radar de Concursos
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo.
echo  Radar de Concursos - pasta: %~dp0
echo.

rem --- rodando de dentro do .zip? ---
echo %~dp0 | find /i "\Temp\" >nul
if %errorlevel%==0 (
    echo  ATENCAO: parece que voce abriu o arquivo direto de dentro do .zip.
    echo  Clique com o botao direito no RadarConcursos.zip, escolha "Extrair tudo...",
    echo  entre na pasta extraida e rode o iniciar.bat de la.
    echo.
    pause
    exit /b
)

if not exist "%~dp0app.py" (
    echo  ERRO: nao achei o arquivo app.py nesta pasta.
    echo  Extraia o .zip inteiro e rode o iniciar.bat de dentro da pasta RadarConcursos.
    echo.
    pause
    exit /b
)

rem --- procura um Python que funcione de verdade ---
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo  ERRO: nao encontrei o Python 3.8 ou mais novo.
    echo  1. Instale pelo site https://www.python.org/downloads/
    echo  2. Na primeira tela da instalacao marque "Add python.exe to PATH".
    echo  3. Feche esta janela e rode o iniciar.bat de novo.
    echo.
    pause
    exit /b
)

echo  Usando: %PY%
%PY% --version
echo.
%PY% app.py %*

echo.
echo  O Radar de Concursos foi encerrado. Se apareceu algum erro acima,
echo  tire um print desta janela e mande para o Claude.
pause
