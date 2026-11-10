"""Dashboard de Rolulabo.

Ejecutar desde la raiz del proyecto, despues de correr el pipeline.

    uv run python src/run_all.py
    uv run streamlit run app/dashboard.py
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import DISCOUNT_GRID, METRICS, MODELS, PROCESSED, ROOT as PROJ, SLA_DAYS, read_csv  # noqa: E402
from decision_rules import semaforo  # noqa: E402

LOG = PROJ / "data" / "decisiones" / "decisiones_log.csv"
AUTOR = "Gabriel Álvarez Mendoza, Eduardo Gutiérrez, Emiliano Luna y Rodrigo Naranjo Hernández"

st.set_page_config(page_title="Rolulabo", layout="wide")

INK, GREY, LIGHT, YELLOW = "#111111", "#7a7a7a", "#d6d6d6", "#F5C400"
ACCENT = YELLOW
CLUSTER_COLORS = {"Alto valor rentable": INK, "Cazadores de descuento": YELLOW,
                  "Compradores ocasionales": GREY, "Inactivos": LIGHT}
SEM = {"Rojo": ("#111111", "#F5C400"), "Amarillo": ("#F5C400", "#111111"), "Verde": ("#E9E9E9", "#111111")}

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
  html, body, [class*="css"], .stMarkdown, .stMetric { font-family: 'Montserrat', sans-serif; }
  [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
  .nota { color: #555; font-size: 0.88rem; }
  .paso { padding: 14px 18px; border-radius: 4px; margin-bottom: 8px; }
  .paso h4 { margin: 0 0 6px 0; font-size: 0.8rem; letter-spacing: 2px; }
  .paso p { margin: 0; font-size: 1.05rem; font-weight: 600; }
  .stTabs [aria-selected="true"] { border-bottom-color: #F5C400 !important; }
</style>
""", unsafe_allow_html=True)


def fmt_money(v):
    return f"-${-v:,.0f}" if v < 0 and round(-v) > 0 else f"${abs(v):,.0f}"


def kpi(col, label, value, sub=None):
    col.metric(label, value)
    if sub:
        col.caption(sub)


def layout(fig, h=360):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), font_family="Montserrat",
                      plot_bgcolor="white", paper_bgcolor="white", legend_title_text="")
    fig.update_xaxes(showgrid=False, linecolor=INK)
    fig.update_yaxes(showgrid=False, linecolor=INK)
    return fig


@st.cache_data
def load_data():
    j = lambda n: json.loads((METRICS / n).read_text(encoding="utf-8"))
    return {
        "q": j("data_quality.json"), "loss": j("loss_model.json"), "deliv": j("delivery.json"),
        "seg": j("segmentation.json"), "cross": j("cross.json"),
        "caps": read_csv(METRICS / "topes_descuento.csv"),
        "sim_sub": read_csv(METRICS / "simulacion_por_subcategoria.csv"),
        "heat": read_csv(METRICS / "estado_subcategoria.csv"),
        "lines": read_csv(PROCESSED / "lines.csv", parse_dates=["order_date"]),
        "orders": read_csv(PROCESSED / "orders.csv", parse_dates=["order_date"]),
        "cust": read_csv(PROCESSED / "customers_clustered.csv"),
        "cruce": read_csv(METRICS / "cruce_clusters.csv"),
        "hyp": j("hypotheses.json"), "dec": j("decision.json"), "rules": j("decision_rules.json"),
    }


@st.cache_resource
def load_model():
    return joblib.load(MODELS / "loss_model.joblib")


missing = [p for p in [METRICS / "loss_model.json", MODELS / "loss_model.joblib"] if not p.exists()]
if missing:
    st.error("Faltan resultados. Corre primero  uv run python src/run_all.py  desde la raiz del proyecto.")
    st.stop()

D = load_data()
M = load_model()
sim = D["loss"]["simulacion_2017"]

st.title("Rolulabo")
st.caption("Rentabilidad, entregas y clientes. Datos 2014 a 2017, evaluación sobre 2017.")

tabs = st.tabs(["Dirección", "Hipótesis y decisión", "Comercial", "Finanzas", "Operaciones", "Marketing", "Datos y modelo"])

# ---------------------------------------------------------------- Direccion
with tabs[0]:
    q = D["q"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas 2014 a 2017", fmt_money(q["ventas_totales"]))
    kpi(c2, "Utilidad", fmt_money(q["utilidad_total"]), f"{q['utilidad_total']/q['ventas_totales']:.1%} margen")
    kpi(c3, "Pérdidas en líneas negativas", fmt_money(q["monto_perdidas"]), f"{q['lineas_con_perdida_pct']:.1%} de las líneas")
    c4.metric("Utilidad 2017 con topes", fmt_money(sim["escenarios"][0]["utilidad"]),
              f"+{fmt_money(sim['escenarios'][0]['delta_utilidad'])} vs real", delta_color="normal")

    cr = D["cross"]
    st.subheader("Dónde está el problema")
    a, b, c = st.columns(3)
    a.markdown(f"**Precio.** {len(cr['estados_alto_descuento'])} estados con descuento promedio mayor a 25% concentran "
               f"**{cr['perdida_en_estados_alto_descuento_pct']:.0%}** de las pérdidas con solo "
               f"{cr['lineas_en_estados_alto_descuento_pct']:.0%} de las líneas.")
    seg_cz = next(r for r in cr["tabla"] if r["cluster_name"] == "Cazadores de descuento")
    b.markdown(f"**Clientes.** El grupo Cazadores de descuento genera **{seg_cz['perdidas_pct']:.0%}** de las pérdidas "
               f"y su utilidad neta es {fmt_money(seg_cz['utilidad'])}.")
    c.markdown(f"**Logística.** El retraso no depende del cliente, la región ni el producto. Entre grupos de clientes "
               f"la tasa varía {cr['diferencia_retraso_entre_grupos_pp']*100:.1f} puntos (p = {cr['chi2_retraso_vs_grupo_p']:.2f}). "
               "Es un problema de promesa, no de priorización.")

    cruce = D["cruce"].copy()
    fig = go.Figure()
    fig.add_bar(x=cruce["cluster_name"], y=cruce["ventas_pct"], name="% ventas", marker_color=LIGHT)
    fig.add_bar(x=cruce["cluster_name"], y=cruce["utilidad_pct"], name="% utilidad", marker_color=INK)
    fig.add_bar(x=cruce["cluster_name"], y=cruce["perdidas_pct"], name="% pérdidas", marker_color=ACCENT)
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(layout(fig.update_layout(barmode="group", title="Peso de cada grupo de clientes")), width="stretch")

    show = cruce[["cluster_name", "ventas", "utilidad", "perdidas", "descuento_prom", "lineas_perdida_pct",
                  "compras_en_estados_alto_descuento_pct", "fuera_de_tiempo_pct"]].rename(columns={
        "cluster_name": "Grupo", "ventas": "Ventas", "utilidad": "Utilidad", "perdidas": "Pérdidas",
        "descuento_prom": "Descuento prom.", "lineas_perdida_pct": "Líneas con pérdida",
        "compras_en_estados_alto_descuento_pct": "Compras en estados de alto descuento",
        "fuera_de_tiempo_pct": "Pedidos fuera de tiempo"})
    st.dataframe(show.style.format({"Ventas": fmt_money, "Utilidad": fmt_money, "Pérdidas": fmt_money,
                                    "Descuento prom.": "{:.1%}", "Líneas con pérdida": "{:.1%}",
                                    "Compras en estados de alto descuento": "{:.1%}", "Pedidos fuera de tiempo": "{:.1%}"}),
                 hide_index=True, width="stretch")

# ---------------------------------------------------------------- Hipótesis y decisión
with tabs[1]:
    hyp = D["hyp"]
    st.subheader(f"{hyp['refutadas']} de 8 creencias del negocio resultaron falsas")
    ht = pd.DataFrame(hyp["hipotesis"])[["id", "creencia", "evidencia", "resultado", "implicacion"]].rename(columns={
        "id": "", "creencia": "Creencia", "evidencia": "Evidencia", "resultado": "Resultado", "implicacion": "Qué cambia"})
    st.dataframe(ht, hide_index=True, width="stretch")

    st.subheader("Score, regla y decisión humana")
    st.markdown('<p class="nota">El modelo calcula, la regla recomienda y una persona decide. Ninguna decisión se toma de forma automática.</p>', unsafe_allow_html=True)
    rr = pd.DataFrame(D["rules"]["reglas"]).rename(columns={"nivel": "Nivel", "score": "Score", "regla": "Regla", "decide": "Decide"})
    st.dataframe(rr, hide_index=True, width="stretch")
    sem = pd.DataFrame(D["rules"]["semaforo_2017"])
    c1, c2, c3 = st.columns(3)
    for col, (_, r) in zip((c1, c2, c3), sem.iterrows()):
        bg, fg = SEM[r["semaforo"]]
        col.markdown(f'<div class="paso" style="background:{bg};color:{fg}"><h4>{r["semaforo"].upper()}</h4>'
                     f'<p>{int(r["lineas"]):,} líneas en 2017, {r["lineas_por_mes"]:.0f} al mes</p>'
                     f'<span>{r["monto_perdida_pct"]:.1%} del monto perdido, tasa de pérdida {r["tasa_perdida"]:.0%}</span></div>',
                     unsafe_allow_html=True)
    st.caption(f"Revisión humana en {D['rules']['decisiones_humanas_pct']:.0%} de las líneas, unas {D['rules']['decisiones_humanas_por_mes']:.0f} al mes, "
               f"que cubren el {D['rules']['perdida_cubierta_por_revision_pct']:.1%} del monto perdido.")

    st.subheader("Opciones para Dirección")
    op = pd.DataFrame(D["dec"]["opciones"]).rename(columns={"opcion": "Opción", "utilidad_2017": "Utilidad 2017 simulada", "riesgo": "Riesgo"})
    st.dataframe(op.style.format({"Utilidad 2017 simulada": fmt_money}).apply(
        lambda r: [f"background-color:{YELLOW};font-weight:700" if r["Opción"].startswith("C") else "" for _ in r], axis=1),
        hide_index=True, width="stretch")
    st.markdown("**Recomendación del equipo, opción C.** La decisión final es de Dirección General.")

# ---------------------------------------------------------------- Comercial
with tabs[2]:
    st.subheader("Evaluador de línea antes de cerrar el pedido")
    st.markdown('<p class="nota">El modelo usa solo información disponible al capturar el pedido. No usa costo ni utilidad.</p>',
                unsafe_allow_html=True)
    L = D["lines"]
    col_in, col_out = st.columns([1, 1.3])
    with col_in:
        sub = st.selectbox("Subcategoría", sorted(L["sub_category"].unique()), index=sorted(L["sub_category"].unique()).index("Tables"))
        cat = L.loc[L["sub_category"] == sub, "category"].iloc[0]
        region = st.selectbox("Región", sorted(L["region"].unique()))
        segment = st.selectbox("Segmento", sorted(L["segment"].unique()))
        ship = st.selectbox("Modalidad de envío", list(SLA_DAYS.keys()), index=3)
        qty = st.slider("Cantidad", 1, 14, 3)
        med_price = float(L.loc[L["sub_category"] == sub, "list_price"].median())
        price = st.number_input("Precio de lista unitario (USD)", min_value=1.0, value=round(med_price, 2), step=5.0)
        disc = st.select_slider("Descuento propuesto", options=DISCOUNT_GRID, value=0.20, format_func=lambda v: f"{v:.0%}")
        month = st.slider("Mes", 1, 12, 11)

    def frame(d):
        return pd.DataFrame([{"sub_category": sub, "category": cat, "region": region, "segment": segment,
                              "ship_mode": ship, "discount": d, "quantity": qty,
                              "log_list_price": np.log1p(price), "month": month}])[M["features"]]

    p = float(M["model"].predict_proba(frame(disc))[:, 1][0])
    cap_row = D["caps"].set_index("sub_category").loc[sub]
    cap = float(cap_row["tope_recomendado"])
    with col_out:
        rule = semaforo(disc, p, cap, M["threshold"])
        bg, fg = SEM[rule["semaforo"]]
        s1, s2, s3 = st.columns(3)
        s1.markdown(f'<div class="paso" style="background:#F2F2F2"><h4>1 · SCORE</h4><p>{p:.0%} de probabilidad de pérdida</p>'
                    f'<span>Umbral {M["threshold"]:.2f}</span></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="paso" style="background:{bg};color:{fg}"><h4>2 · REGLA · {rule["semaforo"].upper()}</h4>'
                    f'<p>{rule["recomendacion"]}</p><span>Tope de {sub}, {cap:.0%}</span></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="paso" style="background:#F2F2F2"><h4>3 · DECIDE</h4><p>{rule["decide"]}</p>'
                    f'<span>La recomendación no se aplica sola</span></div>', unsafe_allow_html=True)
        with st.form("decision"):
            st.markdown("**Registrar la decisión humana**")
            choice = st.radio("Decisión", rule["opciones"], horizontal=True)
            who = st.text_input("Quién decide (nombre y puesto)")
            why = st.text_input("Justificación", placeholder="Obligatoria si se aprueba una excepción")
            if st.form_submit_button("Registrar"):
                if not who.strip():
                    st.warning("Escribe quién toma la decisión.")
                elif "excepción" in choice and not why.strip():
                    st.warning("Una excepción necesita justificación.")
                else:
                    LOG.parent.mkdir(parents=True, exist_ok=True)
                    row = pd.DataFrame([{"fecha": pd.Timestamp.now().isoformat(timespec="seconds"), "subcategoria": sub,
                                         "region": region, "descuento": disc, "score": round(p, 3), "semaforo": rule["semaforo"],
                                         "recomendacion": rule["recomendacion"], "decision": choice, "decide": who, "justificacion": why}])
                    row.to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
                    st.success("Decisión registrada.")
        curve = pd.DataFrame({"Descuento": DISCOUNT_GRID,
                              "Probabilidad": [float(M["model"].predict_proba(frame(d))[:, 1][0]) for d in DISCOUNT_GRID]})
        fig = px.line(curve, x="Descuento", y="Probabilidad", markers=True, color_discrete_sequence=[INK])
        fig.add_vline(x=cap, line_dash="dash", line_color=INK, line_width=2, annotation_text="tope")
        fig.add_hline(y=M["threshold"], line_dash="dot", line_color=GREY, annotation_text="umbral")
        fig.update_xaxes(tickformat=".0%"); fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
        st.plotly_chart(layout(fig.update_layout(title="Probabilidad de pérdida según descuento"), 320), width="stretch")

    st.subheader("Tabla de topes por subcategoría")
    caps = D["caps"][["sub_category", "category", "descuento_prom_actual", "descuento_max_actual", "perdida_pct_hist",
                      "utilidad_hist", "tope_costo", "tope_modelo", "tope_recomendado"]].rename(columns={
        "sub_category": "Subcategoría", "category": "Categoría", "descuento_prom_actual": "Desc. prom. actual",
        "descuento_max_actual": "Desc. máx. actual", "perdida_pct_hist": "Líneas con pérdida",
        "utilidad_hist": "Utilidad 2014 a 2016", "tope_costo": "Tope por costo", "tope_modelo": "Tope por modelo",
        "tope_recomendado": "Tope recomendado"})
    pct = {c: "{:.0%}" for c in ["Desc. prom. actual", "Desc. máx. actual", "Líneas con pérdida", "Tope por costo",
                                  "Tope por modelo", "Tope recomendado"]}
    st.dataframe(caps.style.format({**pct, "Utilidad 2014 a 2016": fmt_money}), hide_index=True, width="stretch")

    with st.expander("Descuento de equilibrio por producto"):
        st.markdown('<p class="nota">Con el costo unitario, el descuento a partir del cual un producto pierde dinero es 1 menos costo entre precio de lista.</p>',
                    unsafe_allow_html=True)
        prod = (L[L["sub_category"] == sub].groupby("product_name")
                .agg(precio_lista=("list_price", "first"), costo=("unit_cost", "first"),
                     equilibrio=("breakeven_discount", "first"), lineas=("row_id", "size"))
                .sort_values("equilibrio").reset_index())
        st.dataframe(prod.style.format({"precio_lista": "${:,.2f}", "costo": "${:,.2f}", "equilibrio": "{:.0%}"}),
                     hide_index=True, width="stretch", height=300)

    with st.expander("Bitácora de decisiones"):
        if LOG.exists():
            st.dataframe(pd.read_csv(LOG).iloc[::-1], hide_index=True, width="stretch")
        else:
            st.caption("Todavía no hay decisiones registradas.")

# ---------------------------------------------------------------- Finanzas
with tabs[3]:
    st.subheader("Simulación de la política de topes sobre 2017")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Utilidad real 2017", fmt_money(sim["utilidad_actual"]))
    c2.metric("Utilidad simulada", fmt_money(sim["escenarios"][0]["utilidad"]))
    c3.metric("Líneas con pérdida", f"{sim['lineas_perdida_simulada']}", f"{sim['lineas_perdida_simulada']-sim['lineas_perdida_actual']} vs {sim['lineas_perdida_actual']}", delta_color="inverse")
    c4.metric("Líneas afectadas por el tope", f"{sim['lineas_afectadas_pct']:.0%}")
    st.markdown(f'<p class="nota">Supuesto principal. El volumen no cambia al subir el precio neto. Las líneas afectadas en conjunto '
                f'perdían {fmt_money(-sim["utilidad_afectadas_antes"])} en 2017, así que la política conviene incluso si se pierde todo ese volumen.</p>',
                unsafe_allow_html=True)

    esc = pd.DataFrame(sim["escenarios"])
    esc["Escenario"] = esc["perdida_volumen"].map(lambda v: f"Pierde {v:.0%} del volumen afectado")
    fig = go.Figure(go.Bar(x=esc["Escenario"], y=esc["delta_utilidad"], marker_color=INK,
                           text=[fmt_money(v) for v in esc["delta_utilidad"]], textposition="outside"))
    st.plotly_chart(layout(fig.update_layout(title="Utilidad adicional en 2017 según pérdida de volumen")), width="stretch")

    left, right = st.columns(2)
    with left:
        ss = D["sim_sub"].sort_values("delta")
        fig = px.bar(ss, x="delta", y="sub_category", orientation="h", color_discrete_sequence=[INK],
                     labels={"delta": "Utilidad recuperada (USD)", "sub_category": ""})
        st.plotly_chart(layout(fig.update_layout(title="Recuperación por subcategoría"), 460), width="stretch")
    with right:
        H = D["heat"].pivot(index="state", columns="sub_category", values="utilidad")
        H = H.loc[H.sum(axis=1).sort_values().index[:15]]
        fig = px.imshow(H, color_continuous_scale=[[0, YELLOW], [0.5, "white"], [1, INK]], color_continuous_midpoint=0,
                        aspect="auto", labels={"color": "Utilidad", "x": "", "y": ""})
        st.plotly_chart(layout(fig.update_layout(title="Utilidad por estado y subcategoría, 15 estados con menor utilidad"), 460),
                        width="stretch")

# ---------------------------------------------------------------- Operaciones
with tabs[4]:
    dv = D["deliv"]
    st.subheader("Cumplimiento de la promesa de entrega")
    cols = st.columns(4)
    for col, m in zip(cols, SLA_DAYS):
        d = dv["descripcion"][m]
        kpi(col, m, f"{1-d['fuera_de_tiempo_pct']:.0%} a tiempo", f"promesa {d['promesa_dias']} días, p95 {d['dias_p95']:.0f}")

    O = D["orders"]
    dist = O.groupby(["ship_mode", "days_to_ship"]).size().reset_index(name="pedidos")
    dist["share"] = dist["pedidos"] / dist.groupby("ship_mode")["pedidos"].transform("sum")
    dist["estado"] = np.where(dist["days_to_ship"] <= dist["ship_mode"].map(SLA_DAYS), "A tiempo", "Fuera de tiempo")
    fig = px.bar(dist, x="days_to_ship", y="share", color="estado", facet_col="ship_mode",
                 category_orders={"ship_mode": list(SLA_DAYS)}, color_discrete_map={"A tiempo": INK, "Fuera de tiempo": ACCENT},
                 labels={"days_to_ship": "Días", "share": "Pedidos"})
    fig.update_yaxes(tickformat=".0%")
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(layout(fig, 330), width="stretch")

    a, b = st.columns(2)
    with a:
        st.markdown("**Se puede predecir el retraso?**")
        mdl = pd.DataFrame(dv["modelos"]).rename(columns={"modalidad": "Modalidad", "modelo": "Modelo", "auc_prueba": "AUC 2017",
                                                         "pedidos_prueba": "Pedidos", "positivos_prueba": "Tarde"})
        st.dataframe(mdl.style.format({"AUC 2017": "{:.2f}"}), hide_index=True, width="stretch")
        st.markdown(f'<p class="nota">AUC cercano a 0.5 equivale a adivinar. Same Day tiene solo 5 pedidos tarde en 2017, su AUC no es confiable. {dv["pruebas_significativas"]} de '
                    f'{len(dv["pruebas_chi2"])} pruebas chi-cuadrada resultan significativas con corrección de Bonferroni.</p>',
                    unsafe_allow_html=True)
    with b:
        st.markdown("**Qué pasa si se ajusta la promesa**")
        sens = pd.DataFrame(dv["sensibilidad_promesa"]).pivot(index="modalidad", columns="escenario", values="cumplimiento")
        sens = sens.loc[list(SLA_DAYS)][["actual", "actual + 1", "p95"]]
        st.dataframe(sens.style.format("{:.0%}"), width="stretch")

# ---------------------------------------------------------------- Marketing
with tabs[5]:
    seg = D["seg"]
    prof = pd.DataFrame(seg["perfiles"])
    st.subheader(f"{seg['k_elegido']} grupos de clientes")
    cols = st.columns(len(prof))
    for col, (_, r) in zip(cols, prof.iterrows()):
        col.markdown(f"**{r['nombre']}**")
        kpi(col, "Clientes", f"{int(r['clientes'])}", f"{r['clientes_pct']:.0%} del total")
        col.markdown(f"Ventas prom. {fmt_money(r['monetary'])}  \nMargen {r['margin']:.1%}  \nDescuento {r['avg_discount']:.1%}  \n"
                     f"Pedidos {r['frequency']:.1f}  \nDías sin comprar {r['recency']:.0f}")

    C = D["cust"]
    fig = px.scatter(C, x="monetary", y="margin", color="cluster_name", size="frequency", log_x=True,
                     color_discrete_map=CLUSTER_COLORS, hover_data=["customer_id", "segment", "recency", "avg_discount"],
                     labels={"monetary": "Ventas totales (escala log)", "margin": "Margen", "cluster_name": ""})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(layout(fig.update_layout(title="Clientes por ventas y margen"), 420), width="stretch")

    st.markdown("**Acción sugerida por grupo**")
    acciones = {
        "Alto valor rentable": "Proteger. Programa de lealtad sin descuento adicional, atención prioritaria.",
        "Cazadores de descuento": "Corregir. Aplicar topes de descuento, ofrecer volumen o envío en lugar de precio.",
        "Compradores ocasionales": "Crecer. Campañas de recompra y venta cruzada, el margen ya es sano.",
        "Inactivos": "Reactivar con bajo costo. Una campaña de recuperación, sin descuentos profundos.",
    }
    st.dataframe(pd.DataFrame({"Grupo": list(acciones), "Acción": list(acciones.values())}), hide_index=True, width="stretch")

    with st.expander("Buscar cliente"):
        cid = st.selectbox("Cliente", sorted(C["customer_id"]))
        st.dataframe(C[C["customer_id"] == cid][["customer_id", "segment", "cluster_name", "frequency", "monetary", "profit",
                                                  "margin", "avg_discount", "recency"]], hide_index=True)

# ---------------------------------------------------------------- Datos y modelo
with tabs[6]:
    lm = D["loss"]
    st.subheader("Comparación de modelos de pérdida, prueba 2017")
    tab = pd.DataFrame(lm["modelos"]).T[["roc_auc", "pr_auc", "f1", "precision", "recall"]].astype(float)
    tab.columns = ["ROC-AUC", "PR-AUC", "F1", "Precisión", "Recall"]
    st.dataframe(tab.style.format("{:.3f}"), width="stretch")
    st.markdown(f"Modelo elegido por validación temporal: **{lm['modelo_elegido']}**. "
                f"IC 95% de F1 por bootstrap {lm['ic95_modelo_elegido']['f1_ic95'][0]:.3f} a {lm['ic95_modelo_elegido']['f1_ic95'][1]:.3f}.")
    ch = lm["costo_historico"]
    st.markdown(f'<p class="nota">La última fila es una referencia sin aprendizaje de máquina. Usa el costo histórico de cada producto y llega a F1 '
                f'{lm["modelos"]["Regla costo histórico"]["f1"]:.3f} porque la pérdida es determinista. El {ch["lineas_con_historial_pct"]:.1%} de las líneas de 2017 '
                f'tiene historial. Si el sistema expone el costo, conviene usar esa regla y dejar el modelo para productos sin costo.</p>', unsafe_allow_html=True)
    sens = pd.DataFrame(lm["sensibilidad_umbral"]["rejilla"])
    fig = px.line(sens, x="umbral", y=["f1", "precision", "recall"], markers=True,
                  color_discrete_sequence=[INK, GREY, YELLOW], labels={"value": "", "umbral": "Umbral", "variable": ""})
    fig.add_vline(x=M["threshold"], line_dash="dot", line_color=INK, annotation_text="umbral elegido")
    st.plotly_chart(layout(fig.update_layout(title="Sensibilidad al umbral, prueba 2017"), 300), width="stretch")
    imp = pd.Series(lm["importancia_permutacion"]).sort_values()
    fig = px.bar(imp, orientation="h", color_discrete_sequence=[INK], labels={"value": "Caída en PR-AUC", "index": ""})
    st.plotly_chart(layout(fig.update_layout(title="Importancia por permutación", showlegend=False), 320), width="stretch")
    st.subheader("Calidad de datos")
    st.json(D["q"])

st.divider()
st.caption(f"Rolulabo · Proyecto integrador de Aprendizaje de Máquina · Equipo {AUTOR}")
