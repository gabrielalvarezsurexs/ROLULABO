"""Pruebas del pipeline de Rolulabo.

Se ejecutan después de uv run python src/run_all.py

    uv run pytest -q
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import METRICS, PROCESSED, TEST_YEAR  # noqa: E402
from decision_rules import semaforo  # noqa: E402
from loss_model import FEATURES  # noqa: E402

REFERENCIA = json.loads((ROOT / "tests" / "referencia.json").read_text(encoding="utf-8"))


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
    assert set(q["atipicos_y_sesgos"]["atipicos_iqr"]) == {"sales", "quantity", "list_price", "profit"}


def test_modelo_estrella_no_pierde_filas(lines):
    fact = pd.read_csv(PROCESSED / "bi" / "fact_lineas.csv")
    assert len(fact) == len(lines)
    for dim, key in [("dim_cliente", "cliente_key"), ("dim_producto", "producto_key"), ("dim_geografia", "geo_key")]:
        d = pd.read_csv(PROCESSED / "bi" / f"{dim}.csv")
        assert d[key].is_unique
        assert fact[key].isin(d[key]).all()


def test_sin_fuga_de_informacion():
    prohibidas = {"profit", "margin", "unit_cost", "cost_ratio", "breakeven_discount", "is_loss", "product_key"}
    assert not prohibidas & set(FEATURES)


def test_regla_de_equilibrio_explica_las_perdidas():
    assert load("data_quality.json")["regla_equilibrio_exactitud"] == 1.0


def test_modelo_supera_la_regla():
    m = load("loss_model.json")
    elegido, rule = m["modelos"][m["modelo_elegido"]], m["modelos"]["Regla descuento > 20%"]
    assert elegido["f1"] > rule["f1"]
    assert m["ic95_modelo_elegido"]["f1_ic95"][0] > m["ic95_regla"]["f1_ic95"][1]


def test_particion_temporal(lines):
    m = load("loss_model.json")
    p = m["particion"]
    assert p["entrenamiento"] == "2014-2016" and p["prueba"] == str(TEST_YEAR)
    assert p["lineas_entrenamiento"] == int((lines["year"] < TEST_YEAR).sum())
    assert p["lineas_prueba"] == int((lines["year"] == TEST_YEAR).sum())
    # Las líneas evaluadas son todas de 2017 y ninguna se usó para entrenar.
    scored = pd.read_csv(METRICS / "prueba_2017_scores.csv")
    years = lines.set_index("row_id").loc[scored["row_id"], "year"]
    assert (years == TEST_YEAR).all()


def test_semaforo():
    assert semaforo(0.5, 0.1, 0.2, 0.45)["semaforo"] == "Rojo"
    assert semaforo(0.1, 0.9, 0.2, 0.45)["semaforo"] == "Amarillo"
    assert semaforo(0.1, 0.1, 0.2, 0.45)["semaforo"] == "Verde"
    # Toda recomendación tiene un responsable humano.
    for d, s in [(0.5, 0.1), (0.1, 0.9), (0.1, 0.1)]:
        assert semaforo(d, s, 0.2, 0.45)["decide"]


def test_semaforo_usa_umbral_del_modelo_elegido():
    m, r = load("loss_model.json"), load("decision_rules.json")
    assert r["umbral_score"] == m["modelos"][m["modelo_elegido"]]["umbral"]


def test_hipotesis_completas_y_coherentes():
    h = load("hypotheses.json")
    assert len(h["hipotesis"]) == 8
    assert {x["resultado"] for x in h["hipotesis"]} <= {"Refutada", "Confirmada"}
    assert all(x["criterio"] for x in h["hipotesis"])
    H = {x["id"]: x for x in h["hipotesis"]}
    # El veredicto tiene que salir del estadístico, no de un texto fijo.
    assert (H["H4"]["resultado"] == "Refutada") == (H["H4"]["stats"]["p"] >= 0.05)
    assert (H["H6"]["resultado"] == "Refutada") == (H["H6"]["stats"]["p_una_cola"] >= 0.05)
    m = load("loss_model.json")
    sin_traslape = m["ic95_modelo_elegido"]["f1_ic95"][0] > m["ic95_regla"]["f1_ic95"][1]
    assert (H["H8"]["resultado"] == "Confirmada") == sin_traslape


def test_resultados_reproducibles():
    """Con las versiones de uv.lock el pipeline reproduce los números de
    referencia que citan reporte, presentación y notebook."""
    m, r, d, s = load("loss_model.json"), load("decision_rules.json"), load("decision.json"), load("segmentation.json")
    e = m["modelos"][m["modelo_elegido"]]
    assert m["modelo_elegido"] == REFERENCIA["modelo_elegido"]
    assert e["umbral"] == pytest.approx(REFERENCIA["umbral"], abs=1e-9)
    assert e["f1"] == pytest.approx(REFERENCIA["f1"], abs=0.002)
    assert e["pr_auc"] == pytest.approx(REFERENCIA["pr_auc"], abs=0.002)
    assert m["modelos"]["Regla costo histórico"]["f1"] == pytest.approx(REFERENCIA["f1_regla_costo"], abs=0.002)
    assert {x["semaforo"]: x["lineas"] for x in r["semaforo_2017"]} == REFERENCIA["semaforo_2017"]
    assert [round(o["utilidad_2017"]) for o in d["opciones"]] == REFERENCIA["utilidad_opciones"]
    assert s["k_elegido"] == REFERENCIA["k_elegido"]
