@echo off
echo Uruchamianie aplikacji WOW_RD...
cd /d "%~dp0"

:: Sprawdzenie czy venv istnieje
if not exist venv (
    echo Tworzenie srodowiska wirtualnego...
    python -m venv venv
)

:: Aktywacja i instalacja zaleznosci
call venv\Scripts\activate
echo Instalowanie/Aktualizacja bibliotek...
python -m pip install --upgrade pip
pip install flask flask_sqlalchemy flask_login openpyxl

:: Uruchomienie aplikacji
echo Start serwera Flask...
python app.py

:: To zatrzyma okno, jesli aplikacja sie wywali
echo.
echo [UWAGA] Serwer zostal zatrzymany.
pause