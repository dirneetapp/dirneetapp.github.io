@echo off
title Subir Carta Digital Bar Sergio's a GitHub Pages
cd /d "%~dp0"

echo ========================================================
echo   BAR SERGIO'S - SINCRONIZADOR DE CARTA DIGITAL
echo ========================================================
echo.
echo 1. Sincronizando platos, fotos y orden desde Firebase Firestore...
python sync_firestore_a_web.py

echo.
echo ========================================================
echo 2. Subiendo cambios a GitHub Pages (dirneetapp.github.io)...
echo ========================================================
git add -A
git commit -m "Sincronizacion automatica de carta Bar Sergio's (fotos, orden y platos)"
git push origin main

echo.
if %ERRORLEVEL% equ 0 (
    echo ========================================================
    echo   EXITO: Carta digital subida a https://dirneetapp.github.io/
    echo   La carta web ya tiene las fotos, platos y orden exactos.
    echo ========================================================
) else (
    echo ========================================================
    echo   AVISO: Si se abrio una ventana de GitHub en tu navegador,
    echo   completa la autorizacion para terminar de subir.
    echo ========================================================
)
echo.
pause
