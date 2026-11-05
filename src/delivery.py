"""Problema 2. Pedidos fuera del tiempo de entrega prometido.

Pregunta analitica
    Con la informacion disponible al capturar un pedido, se puede anticipar
    si va a exceder el tiempo de entrega prometido por su modalidad?

Como la modalidad de envio define el rango de dias casi por completo, la
pregunta relevante es si DENTRO de cada modalidad hay alguna variable que
explique el retraso. Se prueba de dos formas.

    1. Pruebas chi-cuadrada de independencia entre dias de envio y cada
       variable, por modalidad, con correccion de Bonferroni.
    2. Modelos de clasificacion por modalidad con particion temporal. Si el
       AUC es cercano a 0.5 no hay senal aprovechable.
"""
import json

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import METRICS, PROCESSED, SEED, SLA_DAYS, TEST_YEAR
import viz

MODES = ["Same Day", "First Class", "Second Class", "Standard Class"]
TEST_VARS = ["region", "segment", "main_category", "month", "dow", "year"]
CAT = ["region", "segment", "main_category", "state"]
NUM = ["month", "dow", "n_lines", "log_sales", "avg_discount"]


def load() -> pd.DataFrame:
    o = pd.read_csv(PROCESSED / "orders.csv", parse_dates=["order_date", "ship_date"])
    o["log_sales"] = np.log1p(o["sales"])
    return o


def describe(o: pd.DataFrame) -> dict:
    out = {}
    for m in MODES:
        g = o[o["ship_mode"] == m]
        dist = g["days_to_ship"].value_counts(normalize=True).sort_index()
        out[m] = {
            "pedidos": int(len(g)),
            "promesa_dias": SLA_DAYS[m],
            "fuera_de_tiempo_pct": float(g["is_late"].mean()),
            "dias_mediana": float(g["days_to_ship"].median()),
            "dias_p90": float(g["days_to_ship"].quantile(0.90)),
            "dias_p95": float(g["days_to_ship"].quantile(0.95)),
            "dias_max": int(g["days_to_ship"].max()),
            "distribucion": {int(k): float(v) for k, v in dist.items()},
        }
    out["global_fuera_de_tiempo_pct"] = float(o["is_late"].mean())
    return out


def sensitivity(o: pd.DataFrame) -> list[dict]:
    """Cumplimiento si la promesa fuera la actual, +1 dia, o el p95."""
    rows = []
    for m in MODES:
        g = o[o["ship_mode"] == m]
        p95 = int(np.ceil(g["days_to_ship"].quantile(0.95)))
        for label, sla in [("actual", SLA_DAYS[m]), ("actual + 1", SLA_DAYS[m] + 1), ("p95", p95)]:
            rows.append({"modalidad": m, "escenario": label, "promesa_dias": sla,
                         "cumplimiento": float((g["days_to_ship"] <= sla).mean())})
    return rows


def chi2_tests(o: pd.DataFrame) -> tuple[list[dict], float]:
    rows = []
    for m in MODES:
        g = o[o["ship_mode"] == m]
        for v in TEST_VARS:
            ct = pd.crosstab(g[v], g["days_to_ship"])
            ct = ct.loc[:, ct.sum() >= 5]  # quita columnas casi vacias
            if ct.shape[1] < 2:
                continue
            chi2, p, dof, _ = chi2_contingency(ct)
            n = ct.values.sum()
            cramer = np.sqrt(chi2 / (n * (min(ct.shape) - 1)))
            rows.append({"modalidad": m, "variable": v, "chi2": float(chi2), "gl": int(dof),
                         "p_valor": float(p), "v_cramer": float(cramer)})
    alpha = 0.05 / len(rows)
    for r in rows:
        r["significativo_bonferroni"] = bool(r["p_valor"] < alpha)
    return rows, alpha


def models(o: pd.DataFrame) -> list[dict]:
    rows = []
    tr_all, te_all = o["year"] < TEST_YEAR, o["year"] == TEST_YEAR
    prep = lambda scale: ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ("num", StandardScaler() if scale else "passthrough", NUM)])
    makers = {
        "Regresion logistica": lambda: Pipeline([("p", prep(True)), ("c", LogisticRegression(max_iter=2000, C=0.5))]),
        "Gradient boosting": lambda: Pipeline([("p", prep(False)), ("c", HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_depth=4, random_state=SEED))]),
    }
    for m in MODES:
        sel = o["ship_mode"] == m
        tr, te = o[sel & tr_all], o[sel & te_all]
        if tr["is_late"].nunique() < 2 or te["is_late"].nunique() < 2:
            continue
        for name, mk in makers.items():
            pipe = mk().fit(tr[CAT + NUM], tr["is_late"])
            auc = roc_auc_score(te["is_late"], pipe.predict_proba(te[CAT + NUM])[:, 1])
            rows.append({"modalidad": m, "modelo": name, "auc_prueba": float(auc),
                         "pedidos_prueba": int(len(te)), "positivos_prueba": int(te["is_late"].sum())})
    # Modelo global con la modalidad incluida, para contrastar.
    feats = CAT + NUM + ["ship_mode"]
    pipe = Pipeline([("p", ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT + ["ship_mode"]),
        ("num", "passthrough", NUM)])), ("c", HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_depth=4, random_state=SEED))])
    pipe.fit(o.loc[tr_all, feats], o.loc[tr_all, "is_late"])
    auc_all = roc_auc_score(o.loc[te_all, "is_late"], pipe.predict_proba(o.loc[te_all, feats])[:, 1])
    rows.append({"modalidad": "Todas (incluye modalidad)", "modelo": "Gradient boosting",
                 "auc_prueba": float(auc_all), "pedidos_prueba": int(te_all.sum()),
                 "positivos_prueba": int(o.loc[te_all, "is_late"].sum())})
    return rows


def figure(o: pd.DataFrame):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 4, figsize=(6.6, 2.4), sharey=True)
    for ax, m in zip(axes, MODES):
        g = o[o["ship_mode"] == m]["days_to_ship"].value_counts(normalize=True).reindex(range(0, 8), fill_value=0)
        colors = [viz.DARK if d <= SLA_DAYS[m] else viz.LIGHT for d in g.index]
        ax.bar(g.index, g.values, color=colors, edgecolor=viz.BLACK, lw=0.4, width=0.8)
        ax.set_title(m, fontsize=8)
        ax.set_xticks(range(0, 8))
        ax.tick_params(labelsize=7)
        ax.set_xlabel("Días", fontsize=7)
    axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    axes[0].set_ylabel("Pedidos", fontsize=8)
    viz.save(fig, "f4_dias_envio")


def run() -> dict:
    o = load()
    tests, alpha = chi2_tests(o)
    out = {
        "promesa_supuesta": SLA_DAYS,
        "descripcion": describe(o),
        "sensibilidad_promesa": sensitivity(o),
        "pruebas_chi2": tests,
        "alpha_bonferroni": alpha,
        "pruebas_significativas": int(sum(t["significativo_bonferroni"] for t in tests)),
        "modelos": models(o),
    }
    figure(o)
    with open(METRICS / "delivery.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    r = run()
    for m in MODES:
        d = r["descripcion"][m]
        print(m, d["pedidos"], f"tarde {d['fuera_de_tiempo_pct']:.1%}", "p95", d["dias_p95"])
    print("Significativas:", r["pruebas_significativas"], "de", len(r["pruebas_chi2"]), "alpha", r["alpha_bonferroni"])
    print("min p:", min(t["p_valor"] for t in r["pruebas_chi2"]), "max V:", max(t["v_cramer"] for t in r["pruebas_chi2"]))
    for x in r["modelos"]:
        print(x)
    for x in r["sensibilidad_promesa"]:
        print(x)
