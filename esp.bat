@echo off
setlocal
set "PYEXE=%USERPROFILE%\AppData\Local\Python\pythoncore-3.12-64\python.exe"
if not exist C:\esphome\appdata mkdir C:\esphome\appdata
if not exist C:\esphome\tmp mkdir C:\esphome\tmp
if not exist C:\esphome\idf mkdir C:\esphome\idf
set "LOCALAPPDATA=C:\esphome\appdata"
set "TEMP=C:\esphome\tmp"
set "TMP=C:\esphome\tmp"
set "PLATFORMIO_CORE_DIR=C:\esphome\pio"
set "ESPHOME_ESP_IDF_PREFIX=C:\esphome\idf"
cd /d "%~dp0"
echo === Zabirayu svezhie fayly s GitHub ===
git pull
if not exist secrets.yaml (
  echo.
  echo NET FAYLA secrets.yaml - polozhite ego v papku %~dp0
  pause
  exit /b 1
)
if exist ".esphome\build\%~n1\build\CMakeCache.txt" del /q ".esphome\build\%~n1\build\CMakeCache.txt"
"%PYEXE%" -m esphome run %1
endlocal
