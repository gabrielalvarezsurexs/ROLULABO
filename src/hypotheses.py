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
from config import read_csv

ALPHA = 0.05


def cramers_v(ct: pd.DataFrame) -> float:
    chi2 = stats.chi2_contingency(ct)[0]
    return float(np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1))))


def run() -> dict:
    lines = read_csv(PROCESSED / "lines.csv")
    cust = read_csv(PROCESSED / "customers_clustered.csv")
    loss = json.loads((METRICS / "loss_model.json").read_text(encoding="utf-8"))
    deliv = json.loads((METRICS / "delivery.json").read_text(encoding="utf-8"))
    cross = json.loads((METRICS / "cross.json").read_text(encoding="utf-8"))
    dq = json.loads((METRICS / "data_quality.json").read_text(encoding="utf-8"))

    H = []

    def veredicto(refutada: bool) -> str:
        return "Refutada" if refutada else "Confirmada"

    def fp(p: float) -> str:
        return "p < 0.001" if p < 0.001 else f"p = {p:.2f}"

    # H1. El descuento lo decide cada vendedor.
    uno, tot = dq["combinaciones_con_un_solo_descuento"], dq["combinaciones_estado_subcategoria"]
    H.append({
        "id": "H1", "creencia": "El descuento lo decide cada vendedor en cada venta",
        "prueba": "Valores distintos de descuento por combinación estado y subcategoría",
        "criterio": "Se refuta si al menos 95% de las combinaciones tiene un solo descuento",
        "evidencia": f"{uno} de {tot} combinaciones tienen un solo descuento",
        "resultado": veredicto(uno / tot >= 0.95),
        "implicacion": "El descuento es una política regional. Se corrige cambiando una tabla, no capacitando vendedores.",
    })

    # H2. Más descuento compra más volumen.
    rho, p = stats.spearmanr(lines["discount"], lines["quantity"])
    kw = stats.kruskal(*[g["quantity"] for _, g in lines.groupby("discount")])
    q = lines.groupby("discount")["quantity"].mean()
    H.append({
        "id": "H2", "creencia": "Dar más descuento hace que el cliente compre más unidades",
        "prueba": "Correlación de Spearman entre descuento y cantidad, y Kruskal-Wallis por nivel de descuento",
        "criterio": f"Se refuta si la correlación no es significativa (alfa {ALPHA}) o es menor a 0.10 en valor absoluto",
        "evidencia": f"rho = {rho:.3f} ({fp(p)}), Kruskal-Wallis {fp(kw.pvalue)}. Cantidad promedio de {q.min():.1f} a {q.max():.1f} unidades en todos los niveles",
        "resultado": veredicto(p >= ALPHA or abs(rho) < 0.10),
        "implicacion": "El descuento no compra volumen. Quitarlo donde genera pérdida tiene poco riesgo de perder ventas.",
        "stats": {"rho": float(rho), "p": float(p), "kruskal_p": float(kw.pvalue)},
    })

    # H3. Las pérdidas dependen del tipo de cliente.
    ct = pd.crosstab(lines["segment"], lines["is_loss"])
    p3 = stats.chi2_contingency(ct)[1]
    v3 = cramers_v(ct)
    rate = lines.groupby("segment")["is_loss"].mean()
    ctr = pd.crosstab(lines["region"], lines["is_loss"])
    rate_r = lines.groupby("region")["is_loss"].mean()
    H.append({
        "id": "H3", "creencia": "Las pérdidas vienen de cierto tipo de cliente (Consumer, Corporate, Home Office)",
        "prueba": "Chi-cuadrada de independencia entre segmento y pérdida, con V de Cramér",
        "criterio": f"Se refuta si la prueba no es significativa (alfa {ALPHA}) o la V de Cramér es menor a 0.10",
        "evidencia": f"Pérdida de {rate.min():.1%} a {rate.max():.1%} por segmento, {fp(p3)}, V = {v3:.2f}. Por región va de {rate_r.min():.0%} a {rate_r.max():.0%} (V = {cramers_v(ctr):.2f})",
        "resultado": veredicto(p3 >= ALPHA or v3 < 0.10),
        "implicacion": "La pérdida depende de dónde se vende y con qué descuento, no de quién compra.",
        "stats": {"p": float(p3), "v": float(v3), "v_region": float(cramers_v(ctr)),
                  "min": float(rate.min()), "max": float(rate.max())},
    })

    # H4. Las pérdidas se concentran en temporada alta.
    lines["quarter"] = (lines["month"] - 1) // 3 + 1
    ctq = pd.crosstab(lines["quarter"], lines["is_loss"])
    p4 = stats.chi2_contingency(ctq)[1]
    rq = lines.groupby("quarter")["is_loss"].mean()
    H.append({
        "id": "H4", "creencia": "Las pérdidas se concentran en el cuarto trimestre por promociones de temporada",
        "prueba": "Chi-cuadrada entre trimestre y pérdida",
        "criterio": f"Se refuta si la prueba no es significativa (alfa {ALPHA})",
        "evidencia": f"Pérdida de {rq.min():.1%} a {rq.max():.1%} por trimestre, {fp(p4)}",
        "resultado": veredicto(p4 >= ALPHA),
        "implicacion": "No hay un problema estacional. La política de descuento pierde dinero todo el año.",
        "stats": {"p": float(p4), "min": float(rq.min()), "max": float(rq.max())},
    })

    # H5. El retraso depende de región o temporada. Las modalidades con menos
    # de 30 pedidos tarde en prueba no tienen AUC interpretable.
    aucs = [m["auc_prueba"] for m in deliv["modelos"]
            if m["positivos_prueba"] >= 30 and not m["modalidad"].startswith("Todas")]
    H.append({
        "id": "H5", "creencia": "Los retrasos se concentran en ciertas regiones, categorías o meses",
        "prueba": f"{len(deliv['pruebas_chi2'])} pruebas chi-cuadrada por modalidad con corrección de Bonferroni y modelos de clasificación",
        "criterio": "Se refuta si ninguna prueba es significativa con Bonferroni y ningún modelo llega a AUC 0.65 en 2017",
        "evidencia": f"{deliv['pruebas_significativas']} de {len(deliv['pruebas_chi2'])} pruebas significativas, AUC de {min(aucs):.2f} a {max(aucs):.2f}",
        "resultado": veredicto(deliv["pruebas_significativas"] == 0 and max(aucs) < 0.65),
        "implicacion": "Con los datos actuales no hay a quién priorizar. El ajuste es en la promesa.",
        "stats": {"auc_min": float(min(aucs)), "auc_max": float(max(aucs))},
    })

    # H6. Los clientes se van por los retrasos. La creencia es direccional,
    # así que la prueba es de una cola, inactivos con más retraso que activos.
    cust["inactivo"] = cust["recency"] > 365
    a, b = cust.loc[cust["inactivo"], "late_rate"], cust.loc[~cust["inactivo"], "late_rate"]
    p6 = stats.mannwhitneyu(a, b, alternative="greater").pvalue
    sentido = "en sentido contrario a la creencia" if a.mean() < b.mean() else "en el sentido de la creencia"
    H.append({
        "id": "H6", "creencia": "Los clientes que dejaron de comprar se fueron por entregas tardías",
        "prueba": "Mann-Whitney de una cola, tasa de retraso de clientes inactivos (más de un año sin comprar) mayor que la de activos",
        "criterio": f"Se refuta si la prueba de una cola no es significativa (alfa {ALPHA})",
        "evidencia": f"Inactivos {a.mean():.0%} de pedidos tarde contra {b.mean():.0%} de los activos, {sentido} ({fp(p6)})",
        "resultado": veredicto(p6 >= ALPHA),
        "implicacion": "El abandono no se explica por logística. Reactivar a los inactivos no pasa por mejorar envíos.",
        "stats": {"p_una_cola": float(p6), "inactivos": float(a.mean()), "activos": float(b.mean())},
    })

    # H7. El cliente que más compra es el más rentable.
    rm, pm = stats.spearmanr(cust["monetary"], cust["margin"])
    rd, pd_ = stats.spearmanr(cust["avg_discount"], cust["margin"])
    H.append({
        "id": "H7", "creencia": "Los clientes que más compran son los más rentables",
        "prueba": "Correlación de Spearman entre ventas del cliente y su margen",
        "criterio": f"Se refuta si la correlación no es positiva, significativa (alfa {ALPHA}) y de al menos 0.10",
        "evidencia": f"Ventas contra margen rho = {rm:.2f} ({fp(pm)}). Descuento contra margen rho = {rd:.2f} ({fp(pd_)})",
        "resultado": veredicto(not (rm >= 0.10 and pm < ALPHA)),
        "implicacion": "Vender mucho no es ser rentable. El margen del cliente lo decide el descuento que recibe.",
        "stats": {"rho_ventas": float(rm), "p_ventas": float(pm), "rho_descuento": float(rd), "p_descuento": float(pd_)},
    })

    # H8. Un modelo supera a una regla simple.
    best = loss["modelo_elegido"]
    gb, rule = loss["modelos"][best], loss["modelos"]["Regla descuento > 20%"]
    cost = loss["modelos"]["Regla costo histórico"]
    ci_m, ci_r = loss["ic95_modelo_elegido"]["f1_ic95"], loss["ic95_regla"]["f1_ic95"]
    sin_traslape = ci_m[0] > ci_r[1]
    d20 = loss["descuento_20"]
    H.append({
        "id": "H8", "creencia": "Un modelo de aprendizaje de máquina detecta pérdidas mejor que una regla de negocio simple",
        "prueba": "F1 y PR-AUC en 2017 con intervalos bootstrap de 95%",
        "criterio": "Se confirma si el intervalo de F1 del modelo queda completo por encima del de la regla actual",
        "evidencia": f"F1 {gb['f1']:.3f} contra {rule['f1']:.3f}, intervalos {'sin traslape' if sin_traslape else 'con traslape'}. Detecta {d20['modelo_detecta']} de {d20['perdidas']} pérdidas con 20% de descuento que la regla no ve",
        "resultado": veredicto(not sin_traslape),
        "implicacion": f"El modelo supera a la regla actual. Pero si el sistema conoce el costo de cada producto, una regla de costo histórico llega a F1 {cost['f1']:.3f} sin aprendizaje de máquina.",
    })

    # Decisión. Impacto de los topes por grupo de estados en 2017.
    caps = read_csv(METRICS / "topes_descuento.csv").set_index("sub_category")["tope_recomendado"]
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
