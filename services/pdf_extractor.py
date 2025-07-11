import os
import fitz  # PyMuPDF
import pandas as pd
from services.utils import log, REFERENCE_TAGS

def extract_pdf_materials(pdf_path, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    log.info(f"📄 Reading PDF: {pdf_path}")
    pdf = fitz.open(pdf_path)
    material_lines = []

    for i, page in enumerate(pdf):
        text = page.get_text()
        for ref, desc in REFERENCE_TAGS.items():
            if ref in text:
                lines = [l.strip() for l in text.splitlines() if ref in l]
                material_lines.extend([(ref, desc, l) for l in lines])
                log.info(f"🔎 Page {i+1}: Found {ref}")

    ref_df = pd.DataFrame(material_lines, columns=["Partition", "Description", "Matched Line"])
    ref_df.to_csv(f"{output_dir}/PDF_Reference_Partitions.csv", index=False)
    return ref_df