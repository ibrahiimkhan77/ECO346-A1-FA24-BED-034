import csv

PROV = 3
AREA = 1


def to_number(text):
    if text is None:
        return None
    text = text.strip()
    if text == "":
        return None
    return float(text)


# ---- household keys: hhid -> (hhweight, prov_code, urban_rural) ----
hh_keys = {}
with open("data/pslm_hh_subset.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        hhid = int(float(row["hhid"]))
        hh_keys[hhid] = (
            to_number(row["hhweight"]),
            to_number(row["prov_code"]),
            to_number(row["urban_rural"]),
        )

# ---- accumulate n, sum of weights, sum of weight * literate per cell ----
cells = {}
with open("data/pslm_person_subset.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        hhid = int(float(row["hhid"]))
        keys = hh_keys.get(hhid)
        if keys is None:
            continue
        weight, prov, area = keys
        if prov != PROV or area != AREA:
            continue

        age = to_number(row["age"])
        literate = to_number(row["literate"])
        sex = to_number(row["sex"])
        if age is None or literate is None or sex is None or weight is None:
            continue
        if age < 10 or age > 64:
            continue

        # integer arithmetic: bands closed on the left, as in R
        band_start = 10 + 5 * ((int(age) - 10) // 5)
        sex_label = "Men" if int(sex) == 1 else "Women"

        key = (sex_label, band_start)
        if key not in cells:
            cells[key] = {"n": 0, "sum_w": 0.0, "sum_wx": 0.0}
        cells[key]["n"] += 1
        cells[key]["sum_w"] += weight
        cells[key]["sum_wx"] += weight * literate

# ---- band table ----
py_rows = []
for (sex_label, band_start), c in sorted(cells.items()):
    py_rows.append({
        "sex_label": sex_label,
        "band": str(band_start) + "-" + str(band_start + 4),
        "band_mid": band_start + 2,
        "n": c["n"],
        "rate": 100 * c["sum_wx"] / c["sum_w"],
        "thin": c["n"] < 30,
    })

with open("figures/band_table_python.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["sex_label", "band", "band_mid", "n", "rate", "thin"])
    for r in py_rows:
        writer.writerow([r["sex_label"], r["band"], r["band_mid"], r["n"], r["rate"], r["thin"]])

# ---- compare with the R table to one decimal ----
r_rates = {}
with open("figures/band_table_R.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        r_rates[(row["sex_label"], int(float(row["band_mid"])))] = float(row["rate"])

mismatches = 0
for r in py_rows:
    r_value = r_rates.get((r["sex_label"], r["band_mid"]))
    if r_value is None or round(r_value, 1) != round(r["rate"], 1):
        mismatches += 1
        print("MISMATCH:", r["sex_label"], r["band_mid"], r_value, r["rate"])
print("Cells compared:", len(py_rows), " Mismatches:", mismatches)

women_py = [r["rate"] for r in py_rows if r["sex_label"] == "Women" and r["band"] == "15-19"][0]
print("Women 15-19: R =", round(r_rates[("Women", 17)], 1), " Python =", round(women_py, 1))
for r in py_rows:
    print(r["sex_label"], r["band"], r["n"], round(r["rate"], 1), r["thin"])

# ---- largest gap ----
rate_by = {(r["sex_label"], r["band_mid"]): r["rate"] for r in py_rows}
top_mid = None
top_gap = None
for mid in range(12, 63, 5):
    men = rate_by.get(("Men", mid))
    women = rate_by.get(("Women", mid))
    if men is None or women is None:
        continue
    gap = abs(men - women)
    if top_gap is None or gap > top_gap:
        top_gap = gap
        top_mid = mid

# ---- draw the SVG by hand ----
W, H = 900, 550
ML, MR, MT, MB = 70, 90, 50, 90
COLOURS = {"Men": "#1b6ca8", "Women": "#c0392b"}


def px(x):
    return ML + (x - 10) / 60 * (W - ML - MR)


def py(y):
    return H - MB - y / 100 * (H - MT - MB)


out = []
out.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" font-family="sans-serif">' % (W, H, W, H))
out.append('<rect width="%d" height="%d" fill="white"/>' % (W, H))
out.append('<text x="%d" y="28" font-size="15" font-weight="bold">'
           'Rural Sindh: literacy gap between men and women by age band</text>' % ML)

for y in [0, 25, 50, 75, 100]:
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e5e5e5"/>'
               % (ML, py(y), W - MR, py(y)))
    out.append('<text x="%d" y="%.1f" font-size="12" text-anchor="end" fill="#444">%d</text>'
               % (ML - 8, py(y) + 4, y))
for x in range(12, 63, 5):
    out.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle" fill="#444">%d</text>'
               % (px(x), H - MB + 20, x))
out.append('<text x="%.1f" y="%d" font-size="13" text-anchor="middle">Age (band midpoint)</text>'
           % ((ML + W - MR) / 2, H - MB + 42))
out.append('<text transform="translate(20,%.1f) rotate(-90)" font-size="13" '
           'text-anchor="middle">Literacy rate (%%)</text>' % ((MT + H - MB) / 2))

for sex_label in ["Men", "Women"]:
    colour = COLOURS[sex_label]
    pts = [r for r in py_rows if r["sex_label"] == sex_label]
    pts.sort(key=lambda r: r["band_mid"])
    path = " ".join("%.1f,%.1f" % (px(r["band_mid"]), py(r["rate"])) for r in pts)
    out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (path, colour))
    for r in pts:
        fill = "white" if r["thin"] else colour
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="%s" stroke-width="2"/>'
                   % (px(r["band_mid"]), py(r["rate"]), fill, colour))
    last = pts[-1]
    out.append('<text x="%.1f" y="%.1f" font-size="13" font-weight="bold" fill="%s">%s</text>'
               % (px(last["band_mid"]) + 12, py(last["rate"]) + 4, colour, sex_label))

if top_mid is not None:
    y_men = rate_by[("Men", top_mid)]
    y_women = rate_by[("Women", top_mid)]
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#555" stroke-width="1.5"/>'
               % (px(top_mid), py(y_men), px(top_mid), py(y_women)))
    out.append('<text x="%.1f" y="%.1f" font-size="12" fill="#333">Largest gap: %.1f points</text>'
               % (px(top_mid) + 8, py((y_men + y_women) / 2), top_gap))

out.append('<text x="%d" y="%d" font-size="10" fill="#333">Source: PSLM 2019-20 person file. '
           'Persons aged 10-64, Sindh rural. Weighted by hhweight.</text>' % (ML, H - 22))
out.append('<text x="%d" y="%d" font-size="10" fill="#333">'
           'Hollow markers: fewer than 30 observations in that band and sex.</text>' % (ML, H - 8))
out.append("</svg>")

with open("figures/literacy_age_python.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(out))