# dxf_extractor.py

import os
import ezdxf
import pandas as pd
from math import sqrt, pi
from services.utils import log, MATERIAL_KEYS, REFERENCE_TAGS, UNIT_SCALE_MAP
import matplotlib.pyplot as plt

def calc_line_length(start, end):
    return sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)

def generate_drawing_preview(rows, output_file="output/drawing_preview.png"):
    fig, ax = plt.subplots(figsize=(12, 10))
    for row in rows:
        if row['Entity Type'] == 'LINE':
            ax.plot([row['Start X'], row['End X']], [row['Start Y'], row['End Y']], color='blue')
        elif row['Entity Type'] == 'CIRCLE':
            c = plt.Circle((row['Start X'], row['Start Y']), row.get("Radius", 1), color='red', fill=False)
            ax.add_patch(c)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"🖼️ Drawing preview saved to {output_file}")

def calc_polyline_area(points):
    n = len(points)
    return abs(sum(points[i][0] * points[(i+1)%n][1] - points[(i+1)%n][0] * points[i][1] for i in range(n)) / 2)

def extract_from_dxf(dxf_path, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
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
                "Area (m²)": 0, "Count": 0, "Material Tag": "",
                "Material Key": "", "Partition Ref": "",
                "Start X": None, "Start Y": None, "End X": None, "End Y": None, "Radius": None
            }

            if etype == "LINE":
                s = [entity.dxf.start.x, entity.dxf.start.y]
                e = [entity.dxf.end.x, entity.dxf.end.y]
                row.update({
                    "Start X": s[0], "Start Y": s[1],
                    "End X": e[0], "End Y": e[1],
                    "Linear (m)": round(calc_line_length(s, e) * scale, 2),
                    "Count": 1
                })

            elif etype == "LWPOLYLINE" and entity.closed:
                pts = [(v[0], v[1]) for v in entity]
                row.update({
                    "Area (m²)": round(calc_polyline_area(pts) * (scale ** 2), 2),
                    "Count": 1
                })

            elif etype == "CIRCLE":
                r = entity.dxf.radius
                row.update({
                    "Start X": entity.dxf.center.x,
                    "Start Y": entity.dxf.center.y,
                    "Radius": r,
                    "Area (m²)": round((pi * r * r) * (scale ** 2), 2),
                    "Count": 1
                })

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

    try:
        generate_drawing_preview(rows)
    except Exception as e:
        print(f"⚠️ Failed to generate preview: {e}")

    summary.to_csv(f"{output_dir}/BoQ_Summary.csv", index=False)
    summary.to_excel(f"{output_dir}/BoQ_Summary.xlsx", index=False)
    log.info("✅ DXF BoQ extraction complete.")
