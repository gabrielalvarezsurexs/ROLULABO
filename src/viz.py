"""Estilo de graficas para el reporte. Blanco y negro, sin cuadricula ni
marcos innecesarios, tipografia Montserrat si esta instalada."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from config import FIGURES

_fonts = {f.name for f in font_manager.fontManager.ttflist}
FONT = "Montserrat" if "Montserrat" in _fonts else "DejaVu Sans"

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 9,
    "axes.edgecolor": "black",
    "axes.labelcolor": "black",
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "xtick.color": "black",
    "ytick.color": "black",
    "legend.frameon": False,
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

BLACK = "#000000"
DARK = "#404040"
MID = "#8c8c8c"
LIGHT = "#cfcfcf"


def save(fig, name: str):
    path = FIGURES / f"{name}.png"
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path
