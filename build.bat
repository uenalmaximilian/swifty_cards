@echo off

rm swiftycards.exe
rm swiftycards.zip
pyinstaller --onefile --icon=assets\images\icon.ico --noconsole --add-data "assets;assets" main.py
rm main.spec
mv dist\main.exe swiftycards.exe
powershell -Command "Compress-Archive -Path swiftycards.exe -DestinationPath swiftycards.zip"
rd dist
rd /s /q build