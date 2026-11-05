"""Genera las imágenes de la presentación a partir de los datos.

    python reports/build_assets.py

Salen en reports/assets.
    mapa_estados.png   mapa de mosaico de EE. UU. con los 10 estados de descuento alto
    portada.png        gráfico de portada, ventas que crecen y margen que no
Los íconos de reports/assets/icons son de Lucide (licencia ISC), exportados a PNG.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "assets"
OUT.mkdir(exist_ok=True)
BLACK, YELLOW, GRAY, DARK = "#111111", "#F5C400", "#5A5A5A", "#2A2A2A"
FONT = "Montserrat"

ABBR = {"Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT",
        "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Idaho": "ID", "Illinois": "IL",
        "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
        "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
        "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
        "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
        "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
        "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
        "Alaska": "AK", "Hawaii": "HI"}

# Mosaico de estados, columna y fila.
GRID = {"AK": (0, 0), "ME": (10, 0), "VT": (9, 1), "NH": (10, 1),
        "WA": (0, 2), "ID": (1, 2), "MT": (2, 2), "ND": (3, 2), "MN": (4, 2), "IL": (5, 2), "WI": (6, 2), "MI": (7, 2),
        "NY": (8, 2), "RI": (9, 2), "MA": (10, 2),
        "OR": (0, 3), "NV": (1, 3), "WY": (2, 3), "SD": (3, 3), "IA": (4, 3), "IN": (5, 3), "OH": (6, 3), "PA": (7, 3),
        "NJ": (8, 3), "CT": (9, 3),
        "CA": (0, 4), "UT": (1, 4), "CO": (2, 4), "NE": (3, 4), "MO": (4, 4), "KY": (5, 4), "WV": (6, 4), "VA": (7, 4),
        "MD": (8, 4), "DE": (9, 4),
        "AZ": (1, 5), "NM": (2, 5), "KS": (3, 5), "AR": (4, 5), "TN": (5, 5), "NC": (6, 5), "SC": (7, 5), "DC": (8, 5),
        "OK": (3, 6), "LA": (4, 6), "MS": (5, 6), "AL": (6, 6), "GA": (7, 6),
        "HI": (0, 7), "TX": (3, 7), "FL": (8, 7)}


def font():
    from matplotlib import font_manager
    names = {f.name for f in font_manager.fontManager.ttflist}
    return FONT if FONT in names else "DejaVu Sans"


def tile_map():
    cross = json.loads((HERE / "metrics" / "cross.json").read_text(encoding="utf-8"))
    high = {ABBR[s] for s in cross["estados_alto_descuento"]}
    lines = pd.read_csv(ROOT / "data" / "processed" / "lines.csv")
    present = {ABBR[s] for s in lines["state"].unique()}
    loss = lines[lines["profit"] < 0].groupby("state")["profit"].sum().abs()
    loss = {ABBR[k]: v for k, v in loss.items()}

    f = font()
    fig, ax = plt.subplots(figsize=(8.0, 5.6), dpi=200)
    fig.patch.set_facecolor(BLACK)
    ax.set_facecolor(BLACK)
    for st, (c, r) in GRID.items():
        if st in high:
            fc, tc = YELLOW, BLACK
        elif st in present:
            fc, tc = DARK, "#BBBBBB"
        else:
            fc, tc = BLACK, "#444444"
        ax.add_patch(FancyBboxPatch((c + 0.06, -r + 0.06), 0.88, 0.88, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc=fc, ec="#444444" if st not in present else fc, lw=0.8))
        ax.text(c + 0.5, -r + 0.58, st, ha="center", va="center", fontsize=11, fontweight="bold", color=tc, family=f)
        if st in high:
            ax.text(c + 0.5, -r + 0.3, f"-${loss.get(st, 0) / 1000:.0f}K", ha="center", va="center", fontsize=7.5,
                    color=BLACK, family=f)
    ax.set_xlim(-0.1, 11.1)
    ax.set_ylim(-7.1, 1.1)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(OUT / "mapa_estados.png", facecolor=BLACK, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def cover():
    lines = pd.read_csv(ROOT / "data" / "processed" / "lines.csv")
    lines["q"] = lines["year"].astype(str) + "T" + ((lines["month"] - 1) // 3 + 1).astype(str)
    g = lines.groupby("q").agg(s=("sales", "sum"), p=("profit", "sum")).reset_index()
    g["m"] = g["p"] / g["s"]
    fig, ax = plt.subplots(figsize=(6.0, 6.0), dpi=200)
    fig.patch.set_facecolor(BLACK)
    ax.set_facecolor(BLACK)
    x = range(len(g))
    ax.bar(x, g["s"] / g["s"].max(), color=DARK, width=0.72)
    g["m"] = g["m"].rolling(4, min_periods=1).mean()
    ax.plot(x, g["m"] / g["m"].max() * 0.55, color=YELLOW, lw=5, solid_capstyle="round")
    ax.scatter([len(g) - 1], [g["m"].iloc[-1] / g["m"].max() * 0.55], s=160, color=YELLOW, zorder=3)
    ax.axis("off")
    ax.set_ylim(0, 1.05)
    fig.savefig(OUT / "portada.png", facecolor=BLACK, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    tile_map()
    cover()
    print("Imágenes listas en", OUT)
