#!/usr/bin/env python3
"""
build.py — reads Shopify_Dump.csv and produces index.html
Run locally:  python3 build.py
Runs automatically on GitHub via .github/workflows/build.yml
"""

import pandas as pd
import json
import re
import os

CSV_FILE      = "Shopify_Dump.csv"
TEMPLATE_FILE = "template.html"
OUTPUT_FILE   = "index.html"

THEME_MAP = {
    "Abstract Lux":          "Abstract Lux",
    "Italian Mid Century":   "Italian Mid Century",
    "Italian mid century":   "Italian Mid Century",
    "Italian":               "Italian Mid Century",
    "Art Deco":              "Art Deco",
    "Art deco":              "Art Deco",
    "Art Decor":             "Art Deco",
    "Japandi":               "Japandi",
    "Japndi":                "Japandi",
    "Abstract":              "Abstract",
    "Neo Industrial":        "Neo Industrial",
    "neo industrial":        "Neo Industrial",
    "Miscellanous":          "Miscellaneous",
    "Miscellaneous":         "Miscellaneous",
    "Traditional":           "Traditional",
}

THEME_COLORS = {
    "Italian Mid Century":   "#2a7a6e",
    "Abstract Lux":          "#b8902a",
    "Art Deco":              "#c45c2e",
    "Japandi":               "#4aada0",
    "Abstract":              "#e8845a",
    "Neo Industrial":        "#7a5a8a",
    "Miscellaneous":         "#8a7a6a",
    "Traditional":           "#5a8a6a",
}

def build():
    print(f"Reading {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE, encoding="latin-1")
    df["status_norm"] = df["Status"].str.lower().str.strip()

    print(f"  Rows: {len(df)}, Unique products: {df['Product No'].nunique()}")

    # ── Build row data ─────────────────────────────────────────
    rows = []
    theme_counts = {}

    for _, row in df.iterrows():
        tags = str(row["Variant Tags"]) if pd.notna(row["Variant Tags"]) else ""
        raw_themes = re.findall(r"Theme:([^,]+)", tags)
        themes = list(set([THEME_MAP.get(t.strip(), t.strip()) for t in raw_themes]))
        for t in themes:
            theme_counts[t] = theme_counts.get(t, 0) + 1

        rows.append([
            int(row["Product No"])               if pd.notna(row["Product No"])           else 0,   # 0  prodNo
            str(row["Variant Title"])            if pd.notna(row["Variant Title"])         else "",  # 1  title
            str(row["Brand Name"])               if pd.notna(row["Brand Name"])            else "",  # 2  brand
            str(row["Main Category"])            if pd.notna(row["Main Category"])         else "",  # 3  mainCat
            str(row["Category"])                 if pd.notna(row["Category"])              else "",  # 4  cat
            str(row["Subcategory"])              if pd.notna(row["Subcategory"])           else "",  # 5  subcat
            str(row["Material"])                 if pd.notna(row["Material"])              else "",  # 6  material
            int(row["Variant MRP"])              if pd.notna(row["Variant MRP"])           else 0,   # 7  mrp
            int(row["Bengaluru Variant SP"])     if pd.notna(row["Bengaluru Variant SP"])  else 0,   # 8  sp_blr
            int(row["Mumbai Variant SP"])        if pd.notna(row["Mumbai Variant SP"])     else 0,   # 9  sp_mum
            str(row["status_norm"]),                                                                  # 10 status
            str(row["Storage Type"])             if pd.notna(row["Storage Type"])          else "",  # 11 storage
            str(row["Secondary Material"])       if pd.notna(row["Secondary Material"])   else "",  # 12 secMat
            themes,                                                                                   # 13 themes[]
        ])

    # ── Compute reference counts ───────────────────────────────
    mc_counts   = df["Main Category"].value_counts().to_dict()
    cat_counts  = df["Category"].value_counts().to_dict()
    brand_counts= df["Brand Name"].value_counts()
    brand_ref   = brand_counts.index.tolist()

    mc_order    = ["Decor","Living Room","Bedroom","Lighting","Dining","Kitchen","Outdoor Furniture"]
    cat_order   = list(dict.fromkeys(
                    [c for c in ["Wall Decor","Bed","Decorative Lights","Tables","Chairs",
                                 "Floor Décor","Luxe","Sofa","Dining","Decor","Outdoor Seating",
                                 "Sofa cum Bed","Bed Accessories","Outdoor Dining","Outdoor Table",
                                 "Dining Accessories","Outdoor Décor"]
                     if c in cat_counts]
                    + [c for c in cat_counts if c not in ["Wall Decor","Bed","Decorative Lights",
                                                           "Tables","Chairs","Floor Décor","Luxe",
                                                           "Sofa","Dining","Decor","Outdoor Seating",
                                                           "Sofa cum Bed","Bed Accessories",
                                                           "Outdoor Dining","Outdoor Table",
                                                           "Dining Accessories","Outdoor Décor"]]))

    stor_counts = df["Storage Type"].value_counts(dropna=False)
    stor_ref    = [s for s in ["Non-Storage","Storage"] if s in stor_counts.index] + ["NA"]

    mat_ref     = df["Material"].value_counts().index.tolist()

    # ── Themes JS object ──────────────────────────────────────
    themes_js_lines = []
    for name in sorted(theme_counts, key=lambda x: -theme_counts[x]):
        color = THEME_COLORS.get(name, "#888888")
        themes_js_lines.append(f'  "{name}": {{skus:{theme_counts[name]}, color:"{color}"}}')
    themes_js = "var THEMES = {\n" + ",\n".join(themes_js_lines) + "\n};"

    # ── Read template and inject ──────────────────────────────
    print(f"Reading {TEMPLATE_FILE}...")
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    data_js     = json.dumps(rows, separators=(",", ":"))
    brand_js    = json.dumps(brand_ref)
    mc_js       = json.dumps(mc_order)
    cat_js      = json.dumps(cat_order)
    stor_js     = json.dumps(stor_ref)
    mat_js      = json.dumps(mat_ref)

    def safe_replace(html, pattern, replacement):
        m = re.search(pattern, html, flags=re.DOTALL)
        if m:
            return html[:m.start()] + replacement + html[m.end():]
        return html

    html = html.replace("%%DATA%%",      data_js)
    html = safe_replace(html, r"var BRAND_REF = \[.*?\];",  f"var BRAND_REF = {brand_js};")
    html = safe_replace(html, r"var MC_REF = \[.*?\];",      f"var MC_REF = {mc_js};")
    html = safe_replace(html, r"var CAT_REF = \[.*?\];",     f"var CAT_REF = {cat_js};")
    html = safe_replace(html, r"var STOR_REF = \[.*?\];",    f"var STOR_REF = {stor_js};")
    html = safe_replace(html, r"var MAT_REF = \[.*?\];",     f"var MAT_REF = {mat_js};")
    html = safe_replace(html, r"var THEMES = \{.*?\};",      themes_js)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(OUTPUT_FILE)
    print(f"  Written: {OUTPUT_FILE} ({size:,} bytes / {size//1024} KB)")
    print(f"  Brands: {len(brand_ref)}, Themes: {len(theme_counts)}")
    print(f"  Active: {sum(1 for r in rows if r[10]=='active')}, Draft: {sum(1 for r in rows if r[10]=='draft')}")
    print("Done ✓")

if __name__ == "__main__":
    build()
