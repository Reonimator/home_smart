@echo off
rem Zapusk: esp.bat ekran.yaml  |  esp.bat ekran.yaml 192.168.1.121 (proshivka po IP)  |  esp.bat ekran.yaml clean
cd /d "%~dp0"
echo === Zabirayu svezhie fayly s GitHub ===
git pull
call "%~dp0tools\build.bat" %*
