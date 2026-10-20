@echo off
REM ---------------------------------------------------------------------
REM  BANNARAKX - FIVE M . FPS OPTIMIZER  ::  build dist\BANNARAKX.exe
REM  Needs Windows + Python 3.10 or newer on PATH.
REM ---------------------------------------------------------------------
setlocal
cd /d "%~dp0"

echo.
echo   BANNARAKX - build
echo   -----------------
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo   [X] Python not found on PATH.
    echo       Install Python 3.10+ and tick "Add python.exe to PATH".
    pause & exit /b 1
)

echo   [1/4] dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller || (
    echo   [X] pip install failed. & pause & exit /b 1
)

echo   [2/4] cleaning...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo   [3/4] building...
python -m PyInstaller BANNARAKX.spec --noconfirm || (
    echo   [X] build failed - see output above. & pause & exit /b 1
)

echo   [4/4] done.
echo.
echo   Output:  dist\BANNARAKX.exe
echo   The exe asks for Administrator on launch - it has to.
echo.
pause
