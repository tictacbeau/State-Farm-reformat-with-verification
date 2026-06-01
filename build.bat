@echo off
echo Installing required dependencies...
pip install customtkinter pdfplumber reportlab pypdf

echo Building executable with PyInstaller...
pyinstaller --onedir --noconsole ^
            --collect-all pdfplumber ^
            --collect-all customtkinter ^
            --name StateFarmFormatter ^
            main.py

echo Build complete! The output is located in the "dist\StateFarmFormatter" folder.
