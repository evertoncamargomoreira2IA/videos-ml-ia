@echo off
rem Inicia a interface local de validacao do MVA. Duplo clique neste arquivo.
chcp 65001 >nul
setlocal EnableExtensions
set "ROOT=%~dp0"
set "VENV=%LOCALAPPDATA%\mva\venv"
set "VPY=%VENV%\Scripts\python.exe"
set "REQ=%ROOT%mva\requirements.txt"

if exist "%VPY%" goto deps

rem 1) Python ja instalado? (o atalho da Microsoft Store nao conta)
set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>nul && set "PY=python"
if defined PY (
  echo Criando ambiente Python em "%VENV%" ...
  %PY% -m venv "%VENV%" || goto fail
  goto deps
)

rem 2) Sem Python: usa o uv (Astral), instalado so para o seu usuario, sem administrador.
if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul && goto uvvenv
echo.
echo Nao encontrei Python neste computador.
echo Posso baixar o "uv" (gerenciador de Python da Astral, cerca de 20 MB) para a sua pasta
echo de usuario, sem administrador. Ele baixa um Python 3.12 so para este projeto.
echo Se o seu PC for corporativo, confirme antes se a TI permite.
choice /C SN /M "Baixar agora"
if errorlevel 2 goto manual
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" || goto manual
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
:uvvenv
uv venv "%VENV%" --python 3.12 --seed || goto fail

:deps
rem Reinstala dependencias so quando requirements.txt mudar.
fc /b "%REQ%" "%VENV%\requirements.ok" >nul 2>nul && goto run
echo Instalando dependencias (so na primeira vez ou quando mudarem) ...
"%VPY%" -m pip install --disable-pip-version-check -q -r "%REQ%" || goto fail
copy /y "%REQ%" "%VENV%\requirements.ok" >nul

:run
rem PYTHONPATH em vez de "pip install -e": o "#" no nome da pasta confunde o pip.
set "PYTHONPATH=%ROOT%mva\src"
echo.
echo Abrindo http://127.0.0.1:8765/  (feche esta janela para encerrar)
"%VPY%" -m mva serve --open
goto end

:manual
echo.
echo Instale o Python 3.10+ (python.org ou o portal de software da empresa)
echo marcando "Add python.exe to PATH" e rode este arquivo de novo.
goto end

:fail
echo.
echo Algo falhou acima. Copie a mensagem de erro e mande para o Claude.

:end
pause
