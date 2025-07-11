import pytesseract
from pdf2image import convert_from_path
import os
from services.utils import log

def extract_text_with_ocr(pdf_path, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    log.info(f"🔍 Running OCR on {pdf_path}")

    pages = convert_from_path(pdf_path, dpi=300)
    all_text = []

    for i, image in enumerate(pages):
        text = pytesseract.image_to_string(image)
        all_text.append(f"--- Page {i+1} ---\n{text}")

    ocr_output = os.path.join(output_dir, "OCR_Text.txt")
    with open(ocr_output, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_text))

    log.info(f"✅ OCR text saved to {ocr_output}")
    return ocr_output
