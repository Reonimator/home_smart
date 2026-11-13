@echo off
rem Zapusk: esp.bat ekran.yaml   ili   esp.bat ekran.yaml clean (polnaya peresborka)
cd /d "%~dp0"
echo === Zabirayu svezhie fayly s GitHub ===
git pull
call "%~dp0tools\build.bat" %*
