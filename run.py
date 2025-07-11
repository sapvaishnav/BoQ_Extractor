import os
import ezdxf
import fitz  # PyMuPDF
import pytesseract
import pandas as pd
import logging
from math import sqrt, pi
from PIL import Image

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# === Material & Partition Reference from Reference PDF ===
REFERENCE_TAGS = {
    "P01": "Double metal studs party walls - K10-125",
    "P01A": "Party wall with Fire Moisture Board - K10-126",
    "P02": "Siniat metal stud partition - K10-128",
    "P02A": "Bathroom acoustic wall with MF board - K10-129",
    "P03": "Internal Apartment Wall - K10-130",
    "P04": "Siniat Single Frame - 120min Fire - K10-132",
    "P05": "Shaftwall 120min - K10-134",
    "P06": "Double Height Amenity Wall - K10-135",
    "P04A": "Shaftwall Smoke Shaft - K10-138",
    "P04C": "Thinner Shaft Wall - K10-137",
    "P50": "Drylining to Concrete - K10-175",
    "P51": "Acoustic Lining to Concrete - K10-165",
    "P56": "Lining to Lift Wall - K10-176",
    "P54": "Vanity Boxing - K10-168",
}

MATERIAL_KEYS = {
    "RCC": "Reinforced Cement Concrete",
    "BRICK": "Brick Masonry",
    "PLASTERBOARD": "Gypsum Board",
    "GLASS": "Glazing",
    "STEEL": "Mild Steel",
    "CONCRETE": "Concrete Mix",
    "WOOD": "Timber",
    "BLOCK": "Concrete Block",
    "STONE": "Stone Veneer",
    "WALL": "Wall Paneling",
    "PLASTER": "Plaster Finish",
    "ALUMINIUM": "Aluminium Frame"
}

UNIT_SCALE_MAP = {0: 1.0, 1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}

def calc_line_length(start, end):
    return sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)

def calc_polyline_area(points):
    n = len(points)
    return abs(sum(points[i][0] * points[(i+1)%n][1] - points[(i+1)%n][0] * points[i][1] for i in range(n)) / 2)

def extract_from_dxf(dxf_path, output_dir="boq_output"):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    log.info(f"📂 Reading DXF: {dxf_path}")
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        units = doc.header.get('$INSUNITS', 0)
        scale = UNIT_SCALE_MAP.get(units, 1.0)
    except Exception as e:
        log.error(f"❌ Failed DXF load: {e}")
        return

    rows = []

    for idx, entity in enumerate(msp):
        try:
            etype = entity.dxftype()
            layer = entity.dxf.layer
            row = {
                "Layer": layer, "Entity Type": etype, "Linear (m)": 0,
                "Area (m²)": 0, "Count": 0, "Material Tag": "", "Material Key": "", "Partition Ref": ""
            }

            if etype == "LINE":
                s = [entity.dxf.start.x, entity.dxf.start.y]
                e = [entity.dxf.end.x, entity.dxf.end.y]
                row["Linear (m)"] = round(calc_line_length(s, e) * scale, 2)
                row["Count"] = 1

            elif etype == "LWPOLYLINE" and entity.closed:
                pts = [(v[0], v[1]) for v in entity]
                row["Area (m²)"] = round(calc_polyline_area(pts) * (scale ** 2), 2)
                row["Count"] = 1

            elif etype == "CIRCLE":
                r = entity.dxf.radius
                a = pi * r * r
                row["Area (m²)"] = round(a * (scale ** 2), 2)
                row["Count"] = 1

            elif etype in ["TEXT", "MTEXT"]:
                val = entity.dxf.text if etype == "TEXT" else entity.text
                upper = val.upper()
                row["Count"] = 1
                for k, v in MATERIAL_KEYS.items():
                    if k in upper:
                        row["Material Tag"] = val.strip()
                        row["Material Key"] = v
                for pcode, pdesc in REFERENCE_TAGS.items():
                    if pcode in upper:
                        row["Partition Ref"] = pdesc

            elif etype in ["INSERT", "DIMENSION"]:
                row["Count"] = 1

            else:
                continue

            rows.append(row)

        except Exception as e:
            log.warning(f"⚠️ Skipping entity {idx}: {e}")
            continue

    df = pd.DataFrame(rows)
    df.to_csv(f"{output_dir}/BoQ_Detail.csv", index=False)

    summary = df.groupby(["Layer", "Entity Type", "Material Key", "Partition Ref"]).agg({
        "Linear (m)": "sum", "Area (m²)": "sum", "Count": "sum"
    }).reset_index()

    summary.to_csv(f"{output_dir}/BoQ_Summary.csv", index=False)
    summary.to_excel(f"{output_dir}/BoQ_Summary.xlsx", index=False)
    log.info("✅ DXF BoQ extraction complete.")

def extract_pdf_materials(pdf_path, output_dir="boq_output"):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
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

# === EXECUTION ===
if __name__ == "__main__":
    extract_from_dxf("P19053-FCH-BA-12-DR-A-3112.dxf", "boq_output")
    extract_pdf_materials("P19053-FCH-BA-12-DR-A-3112.pdf", "boq_output")
    extract_pdf_materials("P19053-FCH-BA-XX-DR-A-3150.pdf", "boq_output")  # Reference mapping
