"""Problema 1. Lineas de venta con perdida.

Pregunta analitica
    Con la informacion disponible al capturar un pedido (descuento,
    subcategoria, region, segmento, cantidad, precio de lista y modalidad de
    envio), se puede anticipar si la linea va a cerrar con utilidad negativa,
    y hasta que descuento sigue siendo rentable cada subcategoria?

Pasos
    1. Particion temporal. Entrenamiento 2014-2016, prueba 2017.
    2. Validacion cruzada temporal dentro de entrenamiento (expanding window
       por anio) para elegir hiperparametros y umbral de decision.
    3. Comparacion contra una linea base de regla simple (descuento > 20%).
    4. Interpretacion con importancia por permutacion y un arbol poco profundo.
    5. Topes de descuento por subcategoria, calculados solo con 2014-2016.
    6. Simulacion de la politica de topes sobre 2017.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from config import (CAP_PERCENTILE, DISCOUNT_GRID, METRICS, MODELS, PROCESSED,
                    SEED, TEST_YEAR, VOLUME_LOSS_SCENARIOS)
import viz

CAT_FEATURES = ["sub_category", "category", "region", "segment", "ship_mode"]
NUM_FEATURES = ["discount", "quantity", "log_list_price", "month"]
FEATURES = CAT_FEATURES + NUM_FEATURES
TARGET = "is_loss"
# Variables que NO entran al modelo porque no se conocen al capturar el
# pedido o porque son el propio objetivo: profit, margin, unit_cost,
# cost_ratio, breakeven_discount.


def load() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "lines.csv", parse_dates=["order_date"])
    df["log_list_price"] = np.log1p(df["list_price"])
    return df


def preprocessor(scale: bool) -> ColumnTransformer:
    num = StandardScaler() if scale else "passthrough"
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT_FEATURES),
        ("num", num, NUM_FEATURES),
    ])


CANDIDATES = {
    "Regresion logistica": (
        lambda p: LogisticRegression(max_iter=2000, class_weight="balanced", **p), True,
        {"C": [0.1, 1.0, 10.0]},
    ),
    "Arbol de decision": (
        lambda p: DecisionTreeClassifier(random_state=SEED, class_weight="balanced", **p), False,
        {"max_depth": [3, 5, 8, None], "min_samples_leaf": [1, 10, 30]},
    ),
    "Random forest": (
        lambda p: RandomForestClassifier(n_estimators=300, random_state=SEED, n_jobs=-1,
                                         class_weight="balanced", **p), False,
        {"max_depth": [None, 10], "min_samples_leaf": [1, 5]},
    ),
    "Gradient boosting": (
        lambda p: HistGradientBoostingClassifier(random_state=SEED, max_iter=300, **p), False,
        {"learning_rate": [0.05, 0.1], "max_depth": [None, 6]},
    ),
}


def temporal_folds(train: pd.DataFrame):
    """Ventana creciente. 2014 predice 2015, 2014-2015 predicen 2016."""
    years = sorted(train["year"].unique())
    for i in range(1, len(years)):
        tr = train.index[train["year"] < years[i]]
        va = train.index[train["year"] == years[i]]
        yield tr, va


def best_threshold(y, p) -> float:
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-12, None)
    return float(thr[np.argmax(f1[:-1])])


def scores(y, p, thr) -> dict:
    yhat = (p >= thr).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "f1": float(f1_score(y, yhat)),
        "precision": float(precision_score(y, yhat, zero_division=0)),
        "recall": float(recall_score(y, yhat)),
        "accuracy": float((yhat == y).mean()),
        "umbral": float(thr),
    }


def business_scores(df_test: pd.DataFrame, yhat: np.ndarray) -> dict:
    y = df_test[TARGET].values
    loss = -df_test["profit"].where(df_test["profit"] < 0, 0).values
    caught = loss[(yhat == 1) & (y == 1)].sum()
    fp_profit = df_test["profit"].values[(yhat == 1) & (y == 0)].sum()
    return {
        "perdida_total_prueba": float(loss.sum()),
        "perdida_detectada": float(caught),
        "perdida_detectada_pct": float(caught / loss.sum()),
        "utilidad_en_falsos_positivos": float(fp_profit),
    }


def select_models(train: pd.DataFrame) -> dict:
    results = {}
    for name, (make, scale, grid) in CANDIDATES.items():
        best = None
        for params in ParameterGrid(grid):
            oof_y, oof_p = [], []
            for tr, va in temporal_folds(train):
                pipe = Pipeline([("prep", preprocessor(scale)), ("clf", make(params))])
                pipe.fit(train.loc[tr, FEATURES], train.loc[tr, TARGET])
                oof_p.append(pipe.predict_proba(train.loc[va, FEATURES])[:, 1])
                oof_y.append(train.loc[va, TARGET].values)
            y, p = np.concatenate(oof_y), np.concatenate(oof_p)
            ap = average_precision_score(y, p)
            if best is None or ap > best["cv_pr_auc"]:
                best = {"params": params, "cv_pr_auc": float(ap),
                        "umbral": best_threshold(y, p),
                        "cv_f1": float(f1_score(y, (p >= best_threshold(y, p)).astype(int)))}
        results[name] = best
        print(f"  {name}: CV PR-AUC {best['cv_pr_auc']:.3f} params {best['params']}")
    return results


def bootstrap_ci(y, p, thr, n=1000) -> dict:
    rng = np.random.default_rng(SEED)
    f1s, aps = [], []
    idx = np.arange(len(y))
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        if y[b].sum() == 0:
            continue
        f1s.append(f1_score(y[b], (p[b] >= thr).astype(int)))
        aps.append(average_precision_score(y[b], p[b]))
    return {"f1_ic95": [float(np.percentile(f1s, 2.5)), float(np.percentile(f1s, 97.5))],
            "pr_auc_ic95": [float(np.percentile(aps, 2.5)), float(np.percentile(aps, 97.5))]}


def discount_caps(train: pd.DataFrame, model: Pipeline, thr: float) -> pd.DataFrame:
    """Tope de descuento por subcategoria con dos metodos independientes.

    Costo. Percentil CAP_PERCENTILE del descuento de equilibrio de las lineas
    historicas, redondeado hacia abajo al multiplo de 5% mas cercano.

    Modelo. Se toman las lineas historicas de la subcategoria, se les asigna
    cada nivel de DISCOUNT_GRID y se promedia la probabilidad predicha de
    perdida. El tope es el mayor descuento con probabilidad promedio menor
    al umbral de decision.
    """
    rows = []
    for sub, g in train.groupby("sub_category"):
        be = g["breakeven_discount"].quantile(CAP_PERCENTILE)
        cap_cost = np.floor(be * 20 + 1e-9) / 20
        cap_model = 0.0
        probs = {}
        for d in DISCOUNT_GRID:
            x = g[FEATURES].copy()
            x["discount"] = d
            pr = float(model.predict_proba(x)[:, 1].mean())
            probs[d] = pr
            if pr < thr:
                cap_model = d
        rows.append({
            "sub_category": sub,
            "category": g["category"].iloc[0],
            "lineas_hist": int(len(g)),
            "descuento_prom_actual": float(g["discount"].mean()),
            "descuento_max_actual": float(g["discount"].max()),
            "perdida_pct_hist": float(g["is_loss"].mean()),
            "utilidad_hist": float(g["profit"].sum()),
            "equilibrio_mediana": float(g["breakeven_discount"].median()),
            "tope_costo": float(cap_cost),
            "tope_modelo": float(cap_model),
            **{f"p_perdida_{int(d*100)}": v for d, v in probs.items()},
        })
    caps = pd.DataFrame(rows).sort_values("utilidad_hist")
    # El tope recomendado es el mas conservador de los dos metodos.
    caps["tope_recomendado"] = caps[["tope_costo", "tope_modelo"]].min(axis=1)
    return caps


def simulate_policy(test: pd.DataFrame, caps: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Aplica el tope recomendado a 2017 y recalcula utilidad de forma exacta.

    Como el costo unitario es fijo por producto, la utilidad con otro
    descuento d es cantidad * (precio_lista * (1 - d) - costo_unitario).
    Supuesto principal: el volumen no cambia. Se agrega sensibilidad con
    perdida de volumen en las lineas cuyo descuento se reduce.
    """
    t = test.merge(caps[["sub_category", "tope_recomendado"]], on="sub_category")
    t["new_discount"] = np.minimum(t["discount"], t["tope_recomendado"])
    t["affected"] = t["new_discount"] < t["discount"] - 1e-9
    t["new_sales"] = t["quantity"] * t["list_price"] * (1 - t["new_discount"])
    t["new_profit"] = t["new_sales"] - t["quantity"] * t["unit_cost"]

    base_profit = t["profit"].sum()
    unaffected = t.loc[~t["affected"], "profit"].sum()
    a_old = t.loc[t["affected"], "profit"].sum()
    a_new = t.loc[t["affected"], "new_profit"].sum()

    scen = []
    for v in VOLUME_LOSS_SCENARIOS:
        prof = unaffected + (1 - v) * a_new
        sales = t.loc[~t["affected"], "sales"].sum() + (1 - v) * t.loc[t["affected"], "new_sales"].sum()
        scen.append({"perdida_volumen": v, "utilidad": float(prof), "ventas": float(sales),
                     "delta_utilidad": float(prof - base_profit)})
    # Perdida de volumen a partir de la cual la politica deja de convenir.
    # Si las lineas afectadas ya pierden dinero en conjunto, la politica
    # conviene incluso perdiendo todo su volumen y el valor se reporta como None.
    v_breakeven = float(1 - a_old / a_new) if (a_new > 0 and a_old > 0) else None

    res = {
        "lineas_prueba": int(len(t)),
        "lineas_afectadas": int(t["affected"].sum()),
        "lineas_afectadas_pct": float(t["affected"].mean()),
        "utilidad_actual": float(base_profit),
        "ventas_actuales": float(t["sales"].sum()),
        "lineas_perdida_actual": int((t["profit"] < 0).sum()),
        "lineas_perdida_simulada": int((t["new_profit"] < -1e-6).sum()),
        "monto_perdida_actual": float(-t.loc[t["profit"] < 0, "profit"].sum()),
        "monto_perdida_simulada": float(-t.loc[t["new_profit"] < -1e-6, "new_profit"].sum()),
        "utilidad_afectadas_antes": float(a_old),
        "utilidad_afectadas_despues": float(a_new),
        "escenarios": scen,
        "perdida_volumen_equilibrio": v_breakeven,
    }
    by_sub = t.groupby("sub_category").agg(
        utilidad_actual=("profit", "sum"), utilidad_simulada=("new_profit", "sum"),
        lineas_afectadas=("affected", "sum")).reset_index()
    by_sub["delta"] = by_sub["utilidad_simulada"] - by_sub["utilidad_actual"]
    return res, by_sub.sort_values("delta", ascending=False)


def figures(df, y_test, p_best, best_name, rule_pred, caps):
    import matplotlib.pyplot as plt

    # Figura 1. Tasa de perdida por nivel de descuento.
    g = df.groupby("discount").agg(n=("is_loss", "size"), loss=("is_loss", "mean")).reset_index()
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    ax.bar([f"{d:.0%}" for d in g["discount"]], g["loss"], color=viz.DARK, width=0.7)
    for i, (l, n) in enumerate(zip(g["loss"], g["n"])):
        ax.text(i, l + 0.02, f"{l:.0%}", ha="center", fontsize=7)
    ax.set_ylabel("Líneas con pérdida")
    ax.set_xlabel("Descuento aplicado")
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    viz.save(fig, "f1_perdida_por_descuento")

    # Figura 2. Curva precision-recall en 2017.
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    pr, rc, _ = precision_recall_curve(y_test, p_best)
    ax.plot(rc, pr, color=viz.BLACK, lw=1.6, label=best_name)
    ax.scatter([recall_score(y_test, rule_pred)], [precision_score(y_test, rule_pred)],
               color=viz.MID, edgecolor=viz.BLACK, zorder=3, s=40, label="Regla descuento > 20%")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precisión")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="lower left", fontsize=8)
    viz.save(fig, "f2_precision_recall")

    # Figura 3. Descuento promedio actual contra tope recomendado.
    c = caps.sort_values("descuento_prom_actual")
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    yy = np.arange(len(c))
    ax.barh(yy, c["descuento_max_actual"], color=viz.LIGHT, label="Descuento máximo actual")
    ax.scatter(c["tope_recomendado"], yy, color=viz.BLACK, marker="|", s=160, lw=2.2,
               label="Tope recomendado", zorder=3)
    for yi, t in zip(yy, c["tope_recomendado"]):
        ax.text(t + 0.012, yi, f"{t:.0%}", va="center", fontsize=7, fontweight="bold")
    ax.set_yticks(yy)
    ax.set_yticklabels(c["sub_category"], fontsize=8)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Descuento")
    ax.legend(loc="lower right", fontsize=8)
    viz.save(fig, "f3_topes_descuento")


def run() -> dict:
    df = load()
    train = df[df["year"] < TEST_YEAR].reset_index(drop=True)
    test = df[df["year"] == TEST_YEAR].reset_index(drop=True)
    y_tr, y_te = train[TARGET].values, test[TARGET].values

    print("Seleccion de modelos con validacion temporal")
    sel = select_models(train)

    out = {"particion": {"entrenamiento": "2014-2016", "prueba": str(TEST_YEAR),
                         "lineas_entrenamiento": int(len(train)), "lineas_prueba": int(len(test)),
                         "perdida_pct_entrenamiento": float(y_tr.mean()),
                         "perdida_pct_prueba": float(y_te.mean())},
           "features": FEATURES, "modelos": {}}

    # Lineas base.
    dummy = DummyClassifier(strategy="prior").fit(train[FEATURES], y_tr)
    out["modelos"]["Linea base sin modelo"] = scores(y_te, dummy.predict_proba(test[FEATURES])[:, 1], 0.5)
    rule_pred = (test["discount"] > 0.20).astype(int).values
    out["modelos"]["Regla descuento > 20%"] = {
        **scores(y_te, test["discount"].values, 0.20 + 1e-9),
        **business_scores(test, rule_pred)}

    fitted, probs = {}, {}
    for name, (make, scale, _) in CANDIDATES.items():
        pipe = Pipeline([("prep", preprocessor(scale)), ("clf", make(sel[name]["params"]))])
        pipe.fit(train[FEATURES], y_tr)
        p = pipe.predict_proba(test[FEATURES])[:, 1]
        thr = sel[name]["umbral"]
        fitted[name], probs[name] = pipe, p
        out["modelos"][name] = {**scores(y_te, p, thr), **business_scores(test, (p >= thr).astype(int)),
                                "cv_pr_auc": sel[name]["cv_pr_auc"], "params": sel[name]["params"]}

    # El modelo final se elige por PR-AUC de validacion cruzada, no por prueba.
    best_name = max(sel, key=lambda k: sel[k]["cv_pr_auc"])
    best, thr = fitted[best_name], sel[best_name]["umbral"]
    p_best = probs[best_name]
    out["modelo_elegido"] = best_name
    out["ic95_modelo_elegido"] = bootstrap_ci(y_te, p_best, thr)
    out["ic95_regla"] = bootstrap_ci(y_te, test["discount"].values, 0.20 + 1e-9)
    cm = confusion_matrix(y_te, (p_best >= thr).astype(int))
    out["matriz_confusion"] = {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1])}

    # Donde gana el modelo a la regla. Segmento de descuento exacto 20%.
    m20 = (test["discount"] == 0.20).values
    out["descuento_20"] = {
        "lineas": int(m20.sum()), "perdidas": int(y_te[m20].sum()),
        "regla_detecta": 0,
        "modelo_detecta": int(((p_best >= thr) & (y_te == 1) & m20).sum()),
        "modelo_falsos_positivos": int(((p_best >= thr) & (y_te == 0) & m20).sum()),
    }

    # Interpretacion.
    pi = permutation_importance(best, test[FEATURES], y_te, scoring="average_precision",
                                n_repeats=10, random_state=SEED)
    out["importancia_permutacion"] = dict(sorted(
        {f: float(v) for f, v in zip(FEATURES, pi.importances_mean)}.items(), key=lambda kv: -kv[1]))
    tree = Pipeline([("prep", preprocessor(False)),
                     ("clf", DecisionTreeClassifier(max_depth=3, random_state=SEED))]).fit(train[FEATURES], y_tr)
    names = list(tree.named_steps["prep"].get_feature_names_out())
    (METRICS / "arbol_reglas.txt").write_text(
        export_text(tree.named_steps["clf"], feature_names=names, decimals=3), encoding="utf-8")

    # Topes y simulacion.
    caps = discount_caps(train, best, thr)
    caps.to_csv(METRICS / "topes_descuento.csv", index=False)
    sim, sim_sub = simulate_policy(test, caps)
    sim_sub.to_csv(METRICS / "simulacion_por_subcategoria.csv", index=False)
    out["simulacion_2017"] = sim

    # Mapa de perdidas por estado y subcategoria para el dashboard.
    heat = df.groupby(["state", "sub_category"]).agg(
        descuento=("discount", "first"), utilidad=("profit", "sum"), lineas=("row_id", "size")).reset_index()
    heat.to_csv(METRICS / "estado_subcategoria.csv", index=False)

    figures(df, y_te, p_best, best_name, rule_pred, caps)

    joblib.dump({"model": best, "threshold": thr, "features": FEATURES, "name": best_name},
                MODELS / "loss_model.joblib")
    test_scored = test[["row_id", "order_id", "customer_id", "sub_category", "state", "discount",
                        "sales", "profit", "is_loss"]].assign(p_loss=p_best, pred=(p_best >= thr).astype(int))
    test_scored.to_csv(METRICS / "prueba_2017_scores.csv", index=False)

    with open(METRICS / "loss_model.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    r = run()
    for k, v in r["modelos"].items():
        print(f"{k:28s} F1 {v['f1']:.3f}  PR-AUC {v['pr_auc']:.3f}  P {v['precision']:.3f}  R {v['recall']:.3f}")
    print("Elegido:", r["modelo_elegido"], r["ic95_modelo_elegido"])
    print("Descuento 20%:", r["descuento_20"])
    print("Importancia:", r["importancia_permutacion"])
    print(json.dumps(r["simulacion_2017"], indent=1))
