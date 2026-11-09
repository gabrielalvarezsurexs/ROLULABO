"""Configuración central del proyecto Rolulabo.

Todas las rutas, semillas y supuestos de negocio viven aqui para que el
pipeline sea reproducible y los supuestos queden documentados en un solo lugar.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path, **kw):
    """Lee un CSV con los flotantes exactos en cualquier versión de pandas.

    pandas 2 lee por omisión con un último dígito distinto al de pandas 3, y
    esa diferencia mínima cambia los cortes del gradient boosting y el umbral.
    Con lectura exacta el pipeline da los mismos números en ambas versiones.
    """
    if int(pd.__version__.split(".")[0]) < 3:
        kw.setdefault("float_precision", "round_trip")
    return pd.read_csv(path, **kw)

RAW_CSV = ROOT / "data" / "raw" / "superstore.csv"
PROCESSED = ROOT / "data" / "processed"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
METRICS = REPORTS / "metrics"

for _p in (PROCESSED, MODELS, FIGURES, METRICS):
    _p.mkdir(parents=True, exist_ok=True)

SEED = 42

# Particion temporal. Se entrena con 2014-2016 y se evalua con 2017
# para simular que el modelo se usa sobre pedidos futuros.
TEST_YEAR = 2017

# Supuesto de negocio. Promesa de entrega en dias naturales por modalidad.
# El dataset no trae la promesa, asi que se define aqui y se analiza su
# sensibilidad en delivery.py.
SLA_DAYS = {
    "Same Day": 0,
    "First Class": 2,
    "Second Class": 3,
    "Standard Class": 5,
}

# Niveles de descuento que se usan para evaluar topes y simulaciones.
DISCOUNT_GRID = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40,
                 0.45, 0.50, 0.60, 0.70, 0.80]

# Percentil del descuento de equilibrio que se usa como tope seguro
# por subcategoria. 0.10 significa que el tope deja con margen positivo
# al 90% de las lineas historicas de esa subcategoria.
CAP_PERCENTILE = 0.10

# Escenarios de perdida de volumen para el analisis de sensibilidad del tope.
VOLUME_LOSS_SCENARIOS = [0.0, 0.10, 0.25, 0.50, 1.0]

# Clustering
K_RANGE = range(2, 9)
REFERENCE_DATE = "2017-12-31"
