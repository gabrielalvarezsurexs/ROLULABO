"""Datos del dashboard web de Rolulabo (dashboard/data.js).

    uv run python reports/build_dashboard_data.py

Necesita data/processed (correr src/run_all.py antes). Escribe las 9,993
líneas en formato columnar, con las categorías como enteros, para que el
navegador agregue al instante con cada filtro. También calcula, línea por
línea, la utilidad con los topes recomendados y el semáforo de 2017, con las
mismas fórmulas de src/loss_model.py y src/decision_rules.py. Las métricas
fijas (modelos, topes, entregas, grupos, hipótesis) se copian de reports/metrics.
"""
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from config import METRICS, read_csv  # noqa: E402
from decision_rules import semaforo  # noqa: E402

PROC = ROOT / "data" / "processed"
OUT = ROOT / "dashboard" / "data.js"


def jload(name):
    return json.loads((METRICS / name).read_text(encoding="utf-8"))


def codes(series, order=None):
    cats = order or sorted(series.dropna().unique().tolist())
    idx = {c: i for i, c in enumerate(cats)}
    return cats, [idx[v] for v in series]


def r2(x):
    return [round(float(v), 2) for v in x]


def main():
    lines = read_csv(PROC / "lines.csv")
    orders = read_csv(PROC / "orders.csv")
    cust = read_csv(PROC / "customers_clustered.csv")
    caps = read_csv(METRICS / "topes_descuento.csv")
    scores = read_csv(METRICS / "prueba_2017_scores.csv")
    loss, dec, dl, seg, hyp, rules = (jload(n) for n in (
        "loss_model.json", "decision.json", "delivery.json", "segmentation.json",
        "hypotheses.json", "decision_rules.json"))

    lines = lines.sort_values("row_id").reset_index(drop=True)

    # Utilidad con topes, misma fórmula que simulate_policy. Las líneas que no
    # cambian conservan su utilidad original para no arrastrar redondeos.
    tope = lines["sub_category"].map(caps.set_index("sub_category")["tope_recomendado"])
    new_d = np.minimum(lines["discount"], tope)
    affected = new_d < lines["discount"] - 1e-9
    new_sales = lines["quantity"] * lines["list_price"] * (1 - new_d)
    new_profit = new_sales - lines["quantity"] * lines["unit_cost"]
    p2 = np.where(affected, new_profit, lines["profit"])
    s2 = np.where(affected, new_sales, lines["sales"])

    # Semáforo y predicción del modelo solo existen para la prueba de 2017.
    umbral = loss["modelos"][loss["modelo_elegido"]]["umbral"]
    sc = scores.set_index("row_id")
    sem_code = {"Rojo": 1, "Amarillo": 2, "Verde": 3}
    sem, pred = [], []
    for rid, d, t in zip(lines["row_id"], lines["discount"], tope):
        if rid in sc.index:
            sem.append(sem_code[semaforo(d, sc.at[rid, "p_loss"], t, umbral)["semaforo"]])
            pred.append(int(sc.at[rid, "pred"]))
        else:
            sem.append(0)
            pred.append(-1)

    # Una marca por pedido para contar entregas sin duplicar líneas.
    first = ~lines.duplicated("order_id")
    late = lines["order_id"].map(orders.set_index("order_id")["is_late"]).fillna(0).astype(int)
    cl_map = cust.set_index("customer_id")["cluster_name"]

    regions, rg = codes(lines["region"])
    states, st = codes(lines["state"])
    cats, ca = codes(lines["category"])
    subs, sb = codes(lines["sub_category"])
    segs, sg = codes(lines["segment"])
    modes, sm = codes(lines["ship_mode"], ["Same Day", "First Class", "Second Class", "Standard Class"])
    grupos = [p["nombre"] for p in seg["perfiles"]]
    _, cl = codes(lines["customer_id"].map(cl_map), grupos)
    _, cu = codes(lines["customer_id"])

    test = loss["modelos"]
    data = {
        "meta": {
            "generado": date.today().isoformat(),
            "lineas": int(len(lines)),
            "pedidos": int(first.sum()),
            "clientes": int(lines["customer_id"].nunique()),
            "anios": [int(lines["year"].min()), int(lines["year"].max())],
            "modelo_elegido": loss["modelo_elegido"],
            "umbral": umbral,
        },
        "dims": {"region": regions, "state": states, "category": cats, "sub": subs,
                 "segment": segs, "ship": modes, "cluster": grupos},
        "cols": {
            "y": lines["year"].astype(int).tolist(),
            "m": lines["month"].astype(int).tolist(),
            "rg": rg, "st": st, "ca": ca, "sb": sb, "sg": sg, "sm": sm, "cl": cl, "cu": cu,
            "d": [int(round(v * 100)) for v in lines["discount"]],
            "d2": [int(round(v * 100)) for v in new_d],
            "q": lines["quantity"].astype(int).tolist(),
            "s": r2(lines["sales"]), "p": r2(lines["profit"]),
            "s2": r2(s2), "p2": r2(p2),
            "dts": lines["days_to_ship"].astype(int).tolist(),
            "o1": first.astype(int).tolist(),
            "late": late.tolist(),
            "sem": sem, "pred": pred,
        },
        "topes": [{"sub": r.sub_category, "cat": r.category, "actual": round(r.descuento_prom_actual, 4),
                   "max": round(r.descuento_max_actual, 2), "tope": round(r.tope_recomendado, 2),
                   "perdida_hist": round(r.perdida_pct_hist, 4), "utilidad_hist": round(r.utilidad_hist, 2)}
                  for r in caps.itertuples()],
        "modelos": [{"nombre": k, "pr_auc": v["pr_auc"], "f1": v["f1"], "precision": v["precision"],
                     "recall": v["recall"]} for k, v in test.items()],
        "ic95": {"modelo": loss["ic95_modelo_elegido"]["f1_ic95"], "regla": loss["ic95_regla"]["f1_ic95"]},
        "descuento_20": loss["descuento_20"],
        "escenarios": loss["simulacion_2017"]["escenarios"],
        "decision": dec,
        "promesa": dl["promesa_supuesta"],
        "p95": {r["modalidad"]: r["promesa_dias"] for r in dl["sensibilidad_promesa"] if r["escenario"] == "p95"},
        "auc_entregas": [m["auc_prueba"] for m in dl["modelos"]],
        "grupos": seg["perfiles"],
        "hipotesis": [{k: h[k] for k in ("id", "creencia", "resultado", "evidencia", "implicacion")}
                      for h in hyp["hipotesis"]],
        "h2_rho": next(h for h in hyp["hipotesis"] if h["id"] == "H2")["stats"]["rho"],
        "semaforo": rules["semaforo_2017"],
    }
    OUT.parent.mkdir(exist_ok=True)
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text("// Generado por reports/build_dashboard_data.py, no editar a mano.\nwindow.DATA = " + txt + ";\n",
                   encoding="utf-8")

    t17 = lines["year"] == 2017
    print(f"data.js listo, {OUT.stat().st_size / 1e6:.2f} MB")
    print("2017 utilidad", round(lines.loc[t17, "profit"].sum(), 2), "con topes", round(p2[t17].sum(), 2))
    alto = lines["state"].isin(dec["estados"])
    print("opción C", round(np.where(alto, p2, lines["profit"])[t17].sum(), 2))
    print("semáforo", {k: sem.count(v) for k, v in sem_code.items()})


if __name__ == "__main__":
    main()
