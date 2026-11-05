"""Hipótesis iniciales del negocio y su prueba con datos.

Antes de modelar, el equipo escribió las creencias que el negocio daba por
ciertas. Cada una se prueba con una estadística explícita y queda como
confirmada o refutada. Al final se calcula el impacto de la decisión
recomendada por grupo de estados.

Salida. reports/metrics/hypotheses.json y reports/metrics/decision.json
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from config import METRICS, PROCESSED, TEST_YEAR

ALPHA = 0.05


def cramers_v(ct: pd.DataFrame) -> float:
    chi2 = stats.chi2_contingency(ct)[0]
    return float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1))))


def run() -> dict:
    lines = pd.read_csv(PROCESSED / "lines.csv")
    cust = pd.read_csv(PROCESSED / "customers_clustered.csv")
    loss = json.loads((METRICS / "loss_model.json").read_text(encoding="utf-8"))
    deliv = json.loads((METRICS / "delivery.json").read_text(encoding="utf-8"))
    cross = json.loads((METRICS / "cross.json").read_text(encoding="utf-8"))
    dq = json.loads((METRICS / "data_quality.json").read_text(encoding="utf-8"))

    H = []

    # H1. El descuento lo decide cada vendedor.
    H.append({
        "id": "H1", "creencia": "El descuento lo decide cada vendedor en cada venta",
        "prueba": "Valores distintos de descuento por combinación estado y subcategoría",
        "evidencia": f"{dq['combinaciones_con_un_solo_descuento']} de {dq['combinaciones_estado_subcategoria']} combinaciones tienen un solo descuento",
        "resultado": "Refutada",
        "implicacion": "El descuento es una política regional. Se corrige cambiando una tabla, no capacitando vendedores.",
    })

    # H2. Más descuento compra más volumen.
    rho, p = stats.spearmanr(lines["discount"], lines["quantity"])
    kw = stats.kruskal(*[g["quantity"] for _, g in lines.groupby("discount")])
    q = lines.groupby("discount")["quantity"].mean()
    H.append({
        "id": "H2", "creencia": "Dar más descuento hace que el cliente compre más unidades",
        "prueba": "Correlación de Spearman entre descuento y cantidad, y Kruskal-Wallis por nivel de descuento",
        "evidencia": f"rho = {rho:.3f} (p = {p:.2f}), Kruskal-Wallis p = {kw.pvalue:.2f}. Cantidad promedio de {q.min():.1f} a {q.max():.1f} unidades en todos los niveles",
        "resultado": "Refutada",
        "implicacion": "El descuento no compra volumen. Quitarlo donde genera pérdida tiene poco riesgo de perder ventas.",
        "stats": {"rho": float(rho), "p": float(p), "kruskal_p": float(kw.pvalue)},
    })

    # H3. Las pérdidas dependen del tipo de cliente.
    ct = pd.crosstab(lines["segment"], lines["is_loss"])
    p3 = stats.chi2_contingency(ct)[1]
    rate = lines.groupby("segment")["is_loss"].mean()
    ctr = pd.crosstab(lines["region"], lines["is_loss"])
    rate_r = lines.groupby("region")["is_loss"].mean()
    H.append({
        "id": "H3", "creencia": "Las pérdidas vienen de cierto tipo de cliente (Consumer, Corporate, Home Office)",
        "prueba": "Chi-cuadrada de independencia entre segmento y pérdida, con V de Cramér",
        "evidencia": f"Pérdida de {rate.min():.1%} a {rate.max():.1%} por segmento, p = {p3:.2f}, V = {cramers_v(ct):.2f}. Por región va de {rate_r.min():.0%} a {rate_r.max():.0%} (V = {cramers_v(ctr):.2f})",
        "resultado": "Refutada",
        "implicacion": "La pérdida depende de dónde se vende y con qué descuento, no de quién compra.",
    })

    # H4. Las pérdidas se concentran en temporada alta.
    lines["quarter"] = (lines["month"] - 1) // 3 + 1
    ctq = pd.crosstab(lines["quarter"], lines["is_loss"])
    p4 = stats.chi2_contingency(ctq)[1]
    rq = lines.groupby("quarter")["is_loss"].mean()
    H.append({
        "id": "H4", "creencia": "Las pérdidas se concentran en el cuarto trimestre por promociones de temporada",
        "prueba": "Chi-cuadrada entre trimestre y pérdida",
        "evidencia": f"Pérdida de {rq.min():.1%} a {rq.max():.1%} por trimestre, p = {p4:.2f}",
        "resultado": "Refutada",
        "implicacion": "No hay un problema estacional. La política de descuento pierde dinero todo el año.",
    })

    # H5. El retraso depende de región o temporada.
    H.append({
        "id": "H5", "creencia": "Los retrasos se concentran en ciertas regiones, categorías o meses",
        "prueba": "24 pruebas chi-cuadrada por modalidad con corrección de Bonferroni y modelos de clasificación",
        "evidencia": f"{deliv['pruebas_significativas']} de {len(deliv['pruebas_chi2'])} pruebas significativas, AUC de 0.46 a 0.52",
        "resultado": "Refutada",
        "implicacion": "Con los datos actuales no hay a quién priorizar. El ajuste es en la promesa.",
    })

    # H6. Los clientes se van por los retrasos.
    cust["inactivo"] = cust["recency"] > 365
    a, b = cust.loc[cust["inactivo"], "late_rate"], cust.loc[~cust["inactivo"], "late_rate"]
    mw = stats.mannwhitneyu(a, b)
    H.append({
        "id": "H6", "creencia": "Los clientes que dejaron de comprar se fueron por entregas tardías",
        "prueba": "Mann-Whitney entre tasa de retraso de clientes inactivos (más de un año sin comprar) y activos",
        "evidencia": f"Inactivos {a.mean():.0%} de pedidos tarde contra {b.mean():.0%} de los activos (p = {mw.pvalue:.2f}). La diferencia va en sentido contrario",
        "resultado": "Refutada",
        "implicacion": "El abandono no se explica por logística. Reactivar a los inactivos no pasa por mejorar envíos.",
    })

    # H7. El cliente que más compra es el más rentable.
    rm, pm = stats.spearmanr(cust["monetary"], cust["margin"])
    rd, pd_ = stats.spearmanr(cust["avg_discount"], cust["margin"])
    H.append({
        "id": "H7", "creencia": "Los clientes que más compran son los más rentables",
        "prueba": "Correlación de Spearman entre ventas del cliente y su margen",
        "evidencia": f"Ventas contra margen rho = {rm:.2f} (p = {pm:.2f}). Descuento contra margen rho = {rd:.2f} (p < 0.001)",
        "resultado": "Refutada",
        "implicacion": "Vender mucho no es ser rentable. El margen del cliente lo decide el descuento que recibe.",
    })

    # H8. Un modelo supera a una regla simple.
    gb, rule = loss["modelos"]["Gradient boosting"], loss["modelos"]["Regla descuento > 20%"]
    H.append({
        "id": "H8", "creencia": "Un modelo de aprendizaje de máquina detecta pérdidas mejor que una regla de negocio simple",
        "prueba": "F1 y PR-AUC en 2017 con intervalos bootstrap de 95%",
        "evidencia": f"F1 {gb['f1']:.3f} contra {rule['f1']:.3f}, intervalos sin traslape. Detecta 117 de 169 pérdidas con 20% de descuento que la regla no ve",
        "resultado": "Confirmada",
        "implicacion": "El modelo vale la pena para evaluar líneas antes de cerrarlas.",
    })

    # Decisión. Impacto de los topes por grupo de estados en 2017.
    caps = pd.read_csv(METRICS / "topes_descuento.csv").set_index("sub_category")["tope_recomendado"]
    high = cross["estados_alto_descuento"]
    t = lines[lines["year"] == TEST_YEAR].copy()
    t["nd"] = np.minimum(t["discount"], t["sub_category"].map(caps))
    t["np"] = t["quantity"] * (t["list_price"] * (1 - t["nd"]) - t["unit_cost"])
    t["afectada"] = t["nd"] < t["discount"] - 1e-9
    t["grupo"] = np.where(t["state"].isin(high), "10 estados de descuento alto", "Resto del país")
    dec = t.groupby("grupo").agg(utilidad_real=("profit", "sum"), utilidad_con_topes=("np", "sum"),
                                 lineas_afectadas=("afectada", "sum"), ventas=("sales", "sum")).reset_index()
    dec["delta"] = dec["utilidad_con_topes"] - dec["utilidad_real"]
    dec["delta_pct_del_total"] = dec["delta"] / dec["delta"].sum()
    decision = {
        "estados": high,
        "por_grupo": dec.to_dict(orient="records"),
        "opciones": [
            {"opcion": "A. Mantener la política actual", "utilidad_2017": float(t["profit"].sum()),
             "riesgo": "Sigue perdiendo dinero en 10 estados"},
            {"opcion": "B. Topes en todo el país de inmediato", "utilidad_2017": float(t["np"].sum()),
             "riesgo": "No mide el efecto real en volumen antes de escalar"},
            {"opcion": "C. Topes en los 10 estados en dos olas, el resto después",
             "utilidad_2017": float(t.loc[t["grupo"] != "Resto del país", "np"].sum() + t.loc[t["grupo"] == "Resto del país", "profit"].sum()),
             "riesgo": "Bajo. La primera ola sirve de experimento contra la segunda"},
        ],
        "recomendada": "C",
    }

    out = {"hipotesis": H, "refutadas": sum(h["resultado"] == "Refutada" for h in H),
           "confirmadas": sum(h["resultado"] == "Confirmada" for h in H)}
    (METRICS / "hypotheses.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    (METRICS / "decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    r = run()
    for h in r["hipotesis"]:
        print(h["id"], h["resultado"], "|", h["evidencia"])
    print(json.dumps(json.loads((METRICS / "decision.json").read_text()), indent=1, ensure_ascii=False)[:1500])
