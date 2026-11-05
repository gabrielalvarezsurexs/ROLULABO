"""Pruebas del pipeline de Rolulabo.

Se ejecutan después de python src/run_all.py

    pytest -q
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import METRICS, PROCESSED  # noqa: E402
from decision_rules import semaforo  # noqa: E402
from loss_model import FEATURES  # noqa: E402


def load(name):
    return json.loads((METRICS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def lines():
    return pd.read_csv(PROCESSED / "lines.csv")


def test_calidad_de_datos():
    q = load("data_quality.json")
    assert q["nulos_totales"] == 0
    assert q["pedidos_inconsistentes"] == 0
    assert q["filas_limpias"] == q["filas_crudas"] - q["duplicados_exactos_eliminados"]


def test_modelo_estrella_no_pierde_filas(lines):
    fact = pd.read_csv(PROCESSED / "bi" / "fact_lineas.csv")
    assert len(fact) == len(lines)
    for dim, key in [("dim_cliente", "cliente_key"), ("dim_producto", "producto_key"), ("dim_geografia", "geo_key")]:
        d = pd.read_csv(PROCESSED / "bi" / f"{dim}.csv")
        assert d[key].is_unique
        assert fact[key].isin(d[key]).all()


def test_sin_fuga_de_informacion():
    prohibidas = {"profit", "margin", "unit_cost", "cost_ratio", "breakeven_discount", "is_loss"}
    assert not prohibidas & set(FEATURES)


def test_regla_de_equilibrio_explica_las_perdidas():
    assert load("data_quality.json")["regla_equilibrio_exactitud"] == 1.0


def test_modelo_supera_la_regla():
    m = load("loss_model.json")
    gb, rule = m["modelos"]["Gradient boosting"], m["modelos"]["Regla descuento > 20%"]
    assert gb["f1"] > rule["f1"]
    assert m["ic95_modelo_elegido"]["f1_ic95"][0] > m["ic95_regla"]["f1_ic95"][1]


def test_particion_temporal():
    p = load("loss_model.json")["particion"]
    assert p["entrenamiento"] == "2014-2016" and p["prueba"] == "2017"


def test_semaforo():
    assert semaforo(0.5, 0.1, 0.2, 0.37)["semaforo"] == "Rojo"
    assert semaforo(0.1, 0.9, 0.2, 0.37)["semaforo"] == "Amarillo"
    assert semaforo(0.1, 0.1, 0.2, 0.37)["semaforo"] == "Verde"
    # Toda recomendación tiene un responsable humano.
    for d, s in [(0.5, 0.1), (0.1, 0.9), (0.1, 0.1)]:
        assert semaforo(d, s, 0.2, 0.37)["decide"]


def test_hipotesis_completas():
    h = load("hypotheses.json")
    assert len(h["hipotesis"]) == 8
    assert {x["resultado"] for x in h["hipotesis"]} <= {"Refutada", "Confirmada"}
