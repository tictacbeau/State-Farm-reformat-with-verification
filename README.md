# State Farm EFT Formatter

A portable Windows GUI application that reformats State Farm EFT remittance PDFs into a compact single-page-per-payment format, stamps each page with a "Received" stamp, and merges them into a sorted packet.

This application was built specifically for Lewis Brisbois Bisgaard & Smith LLP Accounts Receivable.

## How to Build

If you are a developer with Python installed on your machine, you can package this application into a portable Windows executable folder.

1. Ensure Python 3.10+ is installed on your system.
2. Double-click the `build.bat` script.
3. The script will automatically install required dependencies (`customtkinter`, `pdfplumber`, `reportlab`, `pypdf`) and run PyInstaller.
4. Once completed, a self-contained portable folder will be created at `dist\StateFarmFormatter`.

## How to Run & Deploy

1. Copy the `dist\StateFarmFormatter` folder to any machine.
2. Inside that folder, double-click `StateFarmFormatter.exe` to run the application.
3. **No admin rights are needed** to run the packaged output, and Python does not need to be pre-installed on the target machine.

## Features

- **Portable:** Can be run anywhere from a standard user account.
- **Modern UI:** Built with CustomTkinter for a sleek, responsive interface.
- **Background Processing:** Keeps the GUI responsive while heavy PDF processing happens in the background.
- **Smart Parsing:** Accurately extracts EFT details using label-based state-machine parsing rather than brittle positional OCR.
- **Verification Checks:** Validates invoice counts, payment totals, and cross-checks filename values before generation.
- **Automatic Merging:** Generates clean, stamped PDFs for each payment and merges them largest-to-smallest into a final single packet.
