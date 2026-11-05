"""Lectura cruzada para Direccion General.

Une los tres analisis. Para cada grupo de clientes se calcula cuanto vende,
cuanto gana, cuanto pierde por descuentos, que tan seguido le llega tarde
el pedido y en que estados compra. Responde si el problema se ataca con
precio, con logistica o con mezcla de clientes.
"""
import json

import pandas as pd
from scipy.stats import chi2_contingency

from config import METRICS, PROCESSED


def run() -> dict:
    lines = pd.read_csv(PROCESSED / "lines.csv")
    orders = pd.read_csv(PROCESSED / "orders.csv")
    cust = pd.read_csv(PROCESSED / "customers_clustered.csv")[["customer_id", "cluster", "cluster_name"]]

    state_disc = lines.groupby("state")["discount"].mean()
    high_states = state_disc[state_disc > 0.25].index.tolist()
    lines["estado_alto_descuento"] = lines["state"].isin(high_states)

    l = lines.merge(cust, on="customer_id")
    o = orders.merge(cust, on="customer_id")

    tab = l.groupby("cluster_name").agg(
        lineas=("row_id", "size"),
        ventas=("sales", "sum"),
        utilidad=("profit", "sum"),
        perdidas=("profit", lambda s: -s[s < 0].sum()),
        lineas_perdida_pct=("is_loss", "mean"),
        descuento_prom=("discount", "mean"),
        compras_en_estados_alto_descuento_pct=("estado_alto_descuento", "mean"),
    )
    tab["fuera_de_tiempo_pct"] = o.groupby("cluster_name")["is_late"].mean()
    tab["ventas_pct"] = tab["ventas"] / tab["ventas"].sum()
    tab["utilidad_pct"] = tab["utilidad"] / tab["utilidad"].sum()
    tab["perdidas_pct"] = tab["perdidas"] / tab["perdidas"].sum()

    # Que tanto de la perdida total viene de estados con descuento alto.
    loss = lines[lines["profit"] < 0]
    share_high = float(-loss.loc[loss["estado_alto_descuento"], "profit"].sum() / -loss["profit"].sum())
    lines_high = float(lines["estado_alto_descuento"].mean())

    # Diferencia en tasa de retraso entre grupos, para mostrar que no hay
    # relacion entre tipo de cliente y retraso.
    late_spread = float(tab["fuera_de_tiempo_pct"].max() - tab["fuera_de_tiempo_pct"].min())
    late_p = float(chi2_contingency(pd.crosstab(o["cluster_name"], o["is_late"]))[1])

    out = {
        "estados_alto_descuento": high_states,
        "lineas_en_estados_alto_descuento_pct": lines_high,
        "perdida_en_estados_alto_descuento_pct": share_high,
        "diferencia_retraso_entre_grupos_pp": late_spread,
        "chi2_retraso_vs_grupo_p": late_p,
        "tabla": tab.reset_index().to_dict(orient="records"),
    }
    tab.reset_index().to_csv(METRICS / "cruce_clusters.csv", index=False)
    with open(METRICS / "cross.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    r = run()
    pd.set_option("display.width", 250)
    print(r["estados_alto_descuento"])
    print("lineas en estados alto desc", r["lineas_en_estados_alto_descuento_pct"],
          "perdida ahi", r["perdida_en_estados_alto_descuento_pct"], "spread retraso", r["diferencia_retraso_entre_grupos_pp"])
    print(pd.DataFrame(r["tabla"]).round(3))
