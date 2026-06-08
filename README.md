# Visual Novel Dialogue Extractor
A web-based tool to extract dialogue from gameplay videos using OCR. 

## Prerequisites
1. Python 3.8+
2. [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system.

## Setup
1. Clone the repository.
2. Run `pip install -r requirements.txt`.
3. Install Tesseract OCR:
   - Windows: install from https://github.com/tesseract-ocr/tesseract/releases
   - macOS: `brew install tesseract`
   - Linux: `sudo apt install tesseract-ocr`
4. If Tesseract is not on your system PATH, set `TESSERACT_CMD` to the executable path before running the app.
   - Windows example: `setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"`
5. Run `python app.py` and open `http://127.0.0.1:5000/` in your browser.