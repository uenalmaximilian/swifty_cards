@echo off

rm main.exe
pyinstaller --onefile --icon=assets\images\icon.ico --noconsole --add-data "assets;assets" main.py
rm main.spec
mv dist\main.exe .
rd dist
rd /s /q build
.\main.exe --debug