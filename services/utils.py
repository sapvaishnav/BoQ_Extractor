import logging

import os
import ezdxf
from PIL import Image, ImageDraw

def generate_layer_images_from_dxf(dxf_path, output_dir="output/drawing_preview", image_size=(2000, 2000), margin=50):
    os.makedirs(output_dir, exist_ok=True)
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Group entities by layer
    layer_entities = {}
    for e in msp:
        if e.dxftype() in ("LINE", "LWPOLYLINE"):
            layer = e.dxf.layer
            layer_entities.setdefault(layer, []).append(e)

    image_paths = []

    for layer, entities in layer_entities.items():
        # Calculate bounds
        points = []
        for e in entities:
            if e.dxftype() == "LINE":
                points.append((e.dxf.start.x, e.dxf.start.y))
                points.append((e.dxf.end.x, e.dxf.end.y))
            elif e.dxftype() == "LWPOLYLINE":
                points.extend([(p[0], p[1]) for p in e.get_points()])
        if not points:
            continue

        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        width = max_x - min_x
        height = max_y - min_y

        scale_x = (image_size[0] - 2 * margin) / width if width != 0 else 1
        scale_y = (image_size[1] - 2 * margin) / height if height != 0 else 1
        scale = min(scale_x, scale_y)

        # Create image
        img = Image.new("RGB", image_size, "white")
        draw = ImageDraw.Draw(img)

        for e in entities:
            if e.dxftype() == "LINE":
                x1 = int((e.dxf.start.x - min_x) * scale + margin)
                y1 = int((max_y - e.dxf.start.y) * scale + margin)
                x2 = int((e.dxf.end.x - min_x) * scale + margin)
                y2 = int((max_y - e.dxf.end.y) * scale + margin)
                draw.line((x1, y1, x2, y2), fill="blue", width=1)
            elif e.dxftype() == "LWPOLYLINE":
                pts = [(int((x - min_x) * scale + margin), int((max_y - y) * scale + margin)) for x, y, *_ in e.get_points()]
                if len(pts) > 1:
                    draw.line(pts, fill="green", width=1)

        filename = f"{layer.replace('/', '_')}.png"
        path = os.path.join(output_dir, filename)
        img.save(path)
        image_paths.append(path)

    return image_paths


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

def setup_logger():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return logging.getLogger(__name__)

log = setup_logger()