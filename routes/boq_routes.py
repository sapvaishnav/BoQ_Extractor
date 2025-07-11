from flask import Blueprint, request, render_template, send_from_directory
from werkzeug.utils import secure_filename
from services.dxf_extractor import extract_from_dxf
from services.pdf_extractor import extract_pdf_materials
from services.utils import generate_layer_images_from_dxf

import os
import pandas as pd

boq_bp = Blueprint('boq', __name__)
UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "output"

@boq_bp.route('/')
def index():
    return render_template('index.html')

@@boq_bp.route('/upload', methods=['POST'])
def upload_files():
    dxf = request.files.get('dxf')
    pdfs = request.files.getlist('pdfs')

    if not dxf:
        return "DXF file is required", 400

    # Save DXF file
    dxf_filename = secure_filename(dxf.filename)
    dxf_path = os.path.join(UPLOAD_FOLDER, dxf_filename)
    dxf.save(dxf_path)

    # Save PDF files
    pdf_paths = []
    for pdf in pdfs:
        pdf_filename = secure_filename(pdf.filename)
        pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
        pdf.save(pdf_path)
        pdf_paths.append(pdf_path)

    # Run Extraction
    extract_from_dxf(dxf_path, OUTPUT_FOLDER)
    for path in pdf_paths:
        extract_pdf_materials(path, OUTPUT_FOLDER)

    # Load Summary Data
    summary_file = os.path.join(OUTPUT_FOLDER, "BoQ_Summary.csv")
    if not os.path.exists(summary_file):
        return "Failed to extract summary", 500

    df = pd.read_csv(summary_file)
    table_data = df.to_dict(orient="records")

    # Drawing & Layer Images
    drawing_path = os.path.join("output", "drawing_preview.png")
    drawing_exists = os.path.exists(drawing_path)
    
    # NEW: Generate layer-wise DXF images
    layer_images = generate_layer_images_from_dxf(dxf_path)

    return render_template(
        "result.html",
        table_data=table_data,
        drawing_exists=drawing_exists,
        drawing_file=drawing_path,
        layer_images=layer_images  # Pass to template
    drawing_path = os.path.join("output", "drawing_preview.png")
    drawing_exists = os.path.exists(drawing_path)

    return render_template(
        "result.html",
        table_data=table_data,
        drawing_exists=drawing_exists,
        drawing_file=drawing_path
    )



@boq_bp.route('/output/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
