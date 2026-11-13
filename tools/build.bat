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
set "PYTHONUTF8=1"
cd /d "%~dp0.."
if not exist secrets.yaml (
  echo.
  echo NET FAYLA secrets.yaml - polozhite ego v papku %cd%
  pause
  exit /b 1
)
if /i "%~2"=="clean" (
  echo === Polnaya peresborka: udalyayu staruyu sborku %~n1 ===
  if exist ".esphome\build\%~n1" rmdir /s /q ".esphome\build\%~n1"
)
rem kesh CMake s russkimi bukvami lomaet povtornuyu sborku
if exist ".esphome\build\%~n1\build\CMakeCache.txt" del /q ".esphome\build\%~n1\build\CMakeCache.txt"
"%PYEXE%" -m esphome run %1
endlocal
