import sys
import json
import os
import pandas as pd
from glob import glob


# Define the columns and all possible JSON keys for each (across all known formats)
COLUMNS = [
    ("Item No.", ["item_no", "item_no.", "Item No."]),
    ("Mfr Catalog No.", ["mfr_catalog_no", "mfr_catalog_no.", "Mfr Catalog No."]),
    ("Brand Name", ["brand_name", "Brand Name"]),
    ("Item Description", ["item_description", "name", "Item Description"]),
    ("Image Link", ["image_link", "Image Link"]),
    ("Overview", ["overview", "Overview"]),
    ("Length", ["length", "Length"]),
    ("Width", ["width", "Width"]),
    ("Height", ["height", "Height"]),
    ("Volume", ["volume", "Volume"]),
    ("Diameter", ["diameter", "Diameter"]),
    ("Color", ["color", "Color"]),
    ("Material", ["material", "Material"]),
    ("EAN Code", ["ean_code", "EAN Code"]),
    ("Pattern", ["pattern", "Pattern"]),
    ("Barcode", ["barcode", "Barcode"]),
    # For debuyer-usa and other formats
    ("Product URL", ["url", "product_url"]),
    ("Price", ["price"]),
]

# List all .json files in the directory except empty ones
json_files = [f for f in glob("*.json") if os.path.getsize(f) > 2]
if not json_files:
    print("No JSON files found.")
    sys.exit(1)


rows = []
for file in json_files:
    with open(file, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue
        if not isinstance(data, list):
            print(f"Skipping {file}: not a list of records.")
            continue
        for entry in data:
            row = []
            for col, keys in COLUMNS:
                value = None
                for key in keys:
                    if key in entry:
                        value = entry[key]
                        break
                row.append(value)
            # Add a Source column for traceability
            row.append(file)
            rows.append(row)

# Create DataFrame and write to Excel
out_file = "all_products.xlsx"
df = pd.DataFrame(rows, columns=[col for col, _ in COLUMNS] + ["Source File"])
df.to_excel(out_file, index=False)
print(f"Wrote {len(rows)} rows to {out_file}")
