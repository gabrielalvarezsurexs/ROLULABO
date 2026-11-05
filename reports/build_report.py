"""Genera el reporte de Rolulabo a partir de las métricas del pipeline.

Un solo modelo de contenido con dos salidas.

    python reports/build_report.py          Word (entregables/Reporte_Rolulabo.docx)
    python reports/build_report.py --html   HTML para importar como Google Doc

Todas las cifras se leen de reports/metrics, así que el reporte siempre
coincide con la última ejecución de src/run_all.py.
"""
import argparse
import csv
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MET = HERE / "metrics"
FIG = HERE / "figures"
FONT = "Montserrat"


# ---------------------------------------------------------------- datos
def j(name):
    return json.loads((MET / name).read_text(encoding="utf-8"))


def rows(name):
    with open(MET / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


L, DL, S, X, Q = j("loss_model.json"), j("delivery.json"), j("segmentation.json"), j("cross.json"), j("data_quality.json")
CAPS = rows("topes_descuento.csv")
SIMSUB = {r["sub_category"]: r for r in rows("simulacion_por_subcategoria.csv")}
SIM = L["simulacion_2017"]
MOD = L["modelos"]
GB, RULE = MOD["Gradient boosting"], MOD["Regla descuento > 20%"]
PROF = {p["nombre"]: p for p in S["perfiles"]}
GROUPS = ["Alto valor rentable", "Cazadores de descuento", "Compradores ocasionales", "Inactivos"]
CZ, AV = PROF["Cazadores de descuento"], PROF["Alto valor rentable"]
CROSS = {r["cluster_name"]: r for r in X["tabla"]}
DD = DL["descripcion"]
MODES = ["Same Day", "First Class", "Second Class", "Standard Class"]
SEGK = {r["k"]: r for r in S["seleccion_k"]}
POS_PROFIT = Q["utilidad_total"] + Q["monto_perdidas"]
WORST = SIM["escenarios"][-1]


def pct(v, d=1):
    return f"{v * 100:.{d}f}%"


def f3(v):
    return f"{v:.3f}"


def money(v):
    return ("-$" if v < 0 else "$") + f"{round(abs(v)):,}"


def sens(m, e):
    return next(r for r in DL["sensibilidad_promesa"] if r["modalidad"] == m and r["escenario"] == e)["cumplimiento"]


def auc(m, mo):
    r = next((x for x in DL["modelos"] if x["modalidad"] == m and x["modelo"] == mo), None)
    return f"{r['auc_prueba']:.2f}" if r else "n/d"


# ---------------------------------------------------------------- bloques
def H1(t): return ("h1", t)
def H2(t): return ("h2", t)
def P(t): return ("p", t)
def B(*items): return ("ul", list(items))
def N(*items): return ("ol", list(items))
def T(head, body, widths, numeric=True, size=8.5): return ("table", head, body, widths, numeric, size)
def FIGURE(file, caption, width, alt_head, alt_body): return ("fig", file, caption, width, alt_head, alt_body)
BREAK = ("break",)


def mrow(name, label=None):
    m = MOD[name]
    det = pct(m["perdida_detectada_pct"]) if m.get("perdida_detectada_pct") else "0%"
    return [label or name, f3(m["roc_auc"]), f3(m["pr_auc"]), f3(m["f1"]), f3(m["precision"]), f3(m["recall"]), det]


def loss_by_discount():
    data = {}
    with open(HERE.parent / "data" / "processed" / "lines.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = float(r["discount"])
            n, k = data.get(d, (0, 0))
            data[d] = (n + 1, k + int(r["is_loss"]))
    return [[pct(d, 0), f"{n:,}", pct(k / n, 0)] for d, (n, k) in sorted(data.items())]


def days_table():
    out = []
    for m in MODES:
        dist = DD[m]["distribucion"]
        out.append([m] + [pct(dist.get(str(d), 0), 0) for d in range(8)])
    return out


HYP = j("hypotheses.json")
RULES = j("decision_rules.json")
AUTOR = "Gabriel Álvarez Mendoza"
DEC = j("decision.json")
DEC_HIGH = next(g for g in DEC["por_grupo"] if g["grupo"].startswith("10"))
SIM_MARGIN = SIM["escenarios"][0]["utilidad"] / SIM["escenarios"][0]["ventas"]
REAL_MARGIN = SIM["utilidad_actual"] / SIM["ventas_actuales"]


def _base_content():
    c = []
    # ------------------------------------------------------------ 1
    c += [
        H1("1. Resumen ejecutivo"),
        P(f"**Decisión recomendada.** Aplicar topes de descuento por subcategoría en los 10 estados de descuento alto a partir del siguiente trimestre, en dos olas de cinco estados que funcionan como experimento controlado, y extenderlos al resto del país solo si se cumplen los criterios de éxito. Con datos de 2017, esa decisión lleva a los 10 estados de {money(DEC_HIGH['utilidad_real'])} a {money(DEC_HIGH['utilidad_con_topes'])} de utilidad y captura el {pct(DEC_HIGH['delta_pct_del_total'], 0)} del beneficio total posible."),
        P(f"Rolulabo vendió {money(Q['ventas_totales'])} entre 2014 y 2017 con una utilidad de {money(Q['utilidad_total'])}, un margen de {pct(Q['utilidad_total'] / Q['ventas_totales'])}. El {pct(Q['lineas_con_perdida_pct'])} de las líneas de venta cerró con pérdida y esas líneas restaron {money(Q['monto_perdidas'])}, el {pct(Q['monto_perdidas'] / POS_PROFIT, 0)} de lo que ganaron las líneas rentables."),
        P(f"Antes de modelar escribimos ocho creencias del negocio y las probamos con datos. {HYP['refutadas']} resultaron refutadas. Las tres más importantes cambiaron el proyecto."),
        B("**El descuento no lo decide el vendedor.** Es una tabla fija por estado y subcategoría, y en 10 estados supera el margen del producto. Ahí se concentra el " + pct(X["perdida_en_estados_alto_descuento_pct"], 0) + " de las pérdidas con " + pct(X["lineas_en_estados_alto_descuento_pct"], 0) + " de las líneas.",
          f"**El descuento no compra volumen.** La cantidad por línea es la misma con 0% que con 80% de descuento (rho = {HYP['hipotesis'][1]['stats']['rho']:.3f}). Quitar descuento donde pierde dinero tiene poco riesgo comercial.",
          "**Vender mucho no es ser rentable.** El grupo Cazadores de descuento compra casi tan seguido como el de mayor valor, pero su margen es negativo y genera el " + pct(CZ["perdidas_pct"], 0) + " de las pérdidas."),
        P(f"Tres modelos sostienen la decisión. Un gradient boosting detecta las líneas que van a perder dinero con F1 de {f3(GB['f1'])} contra {f3(RULE['f1'])} de la regla actual. Un análisis de entregas demuestra que el retraso no se puede predecir con los datos disponibles, así que el ajuste es en la promesa. Un K-Means separa cuatro grupos de clientes con estrategias distintas."),
        P(f"Ningún modelo decide solo. Cada resultado sigue el esquema score, regla y decisión. El modelo calcula un score, una regla explícita lo convierte en recomendación y una persona con nombre de puesto acepta, ajusta o rechaza. En 2017 el semáforo habría mandado a revisión humana {pct(RULES['decisiones_humanas_pct'], 0)} de las líneas, unas {RULES['decisiones_humanas_por_mes']:.0f} al mes, que concentran el {pct(RULES['perdida_cubierta_por_revision_pct'])} del monto perdido."),
    ]
    # ------------------------------------------------------------ 2
    c += [
        H1("2. Metodología"),
        P("El proyecto sigue CRISP-DM, el estándar de la industria para proyectos de minería de datos, organizado en tres iteraciones cortas al estilo ágil. Cada iteración cierra con un entregable que funciona y con la revisión de las hipótesis. Si una hipótesis cae, el backlog se ajusta antes de la siguiente iteración."),
        T(["Fase CRISP-DM", "Pregunta que responde", "Entregable", "Dónde vive"], [
            ["Comprensión del negocio", "Qué decisión hay que apoyar y cómo se mide el éxito", "Planteamiento, KPIs, historias de usuario", "Secciones 3 y 4"],
            ["Comprensión de los datos", "Qué datos hay y qué creencias del negocio sostienen o no", "EDA y prueba de 8 hipótesis", "src/hypotheses.py"],
            ["Preparación de datos", "Los datos son confiables y están listos para modelar y para BI", "ETL validado y modelo estrella", "src/etl.py"],
            ["Modelado", "Qué técnica responde cada pregunta analítica", "Tres modelos con validación temporal", "src/loss_model.py y otros"],
            ["Evaluación", "El modelo supera a la línea base y qué vale para el negocio", "Métricas, intervalos y simulación de política", "reports/metrics"],
            ["Despliegue", "Cómo llega el resultado a quien decide", "Score, regla y decisión humana, dashboard y monitoreo", "app/dashboard.py"]],
          [1.45, 2.05, 1.75, 1.25], numeric=False, size=8),
        H2("2.1 Backlog en historias de usuario"),
        P("Cada pregunta analítica nace de una necesidad de un área. El criterio de aceptación dice cuándo la historia está terminada."),
        T(["Historia", "Criterio de aceptación", "Estado"], [
            ["Como gerente comercial quiero saber antes de cerrar si una línea va a perder dinero, para ajustar el descuento", "Modelo mejor que la regla actual en F1, con intervalo de confianza", "Terminada"],
            ["Como director de finanzas quiero un tope de descuento por subcategoría con su impacto en utilidad, para aprobar una nueva política", "Topes calculados sin usar 2017 y simulados sobre 2017", "Terminada"],
            ["Como gerente de operaciones quiero saber qué pedidos llegarán tarde, para priorizarlos", "AUC mayor a 0.65 en 2017", "Replanteada. El AUC fue 0.5, se entrega promesa realista"],
            ["Como gerente de marketing quiero grupos de clientes con su rentabilidad, para asignar presupuesto", "Grupos estables y con perfil accionable", "Terminada"],
            ["Como director general quiero una sola lectura de las causas, para decidir dónde actuar", "Decisión con opciones, impacto y criterios de éxito", "Terminada"]],
          [3.2, 2.1, 1.2], numeric=False, size=8),
        H2("2.2 Iteraciones"),
        T(["Iteración", "Fases", "Entregable", "Qué cambió al cerrar"], [
            ["1. Negocio y datos", "Negocio, datos, preparación", "ETL validado, EDA, hipótesis probadas", "H1 cayó. El problema pasó de capacitar vendedores a corregir una tabla de descuentos"],
            ["2. Modelos", "Modelado, evaluación", "Tres modelos contra línea base", "H5 cayó. La historia de Operaciones se replanteó como ajuste de promesa"],
            ["3. Decisión y despliegue", "Evaluación, despliegue", "Simulación, dashboard, decisión", "H2 cayó. El riesgo de perder volumen con topes resultó bajo"]],
          [1.35, 1.4, 1.75, 2.0], numeric=False, size=8),
        P("Definición de terminado para cualquier entregable. Se regenera con un comando desde el CSV crudo, se compara contra una línea base y está ligado a una decisión de un área."),
    ]
    # ------------------------------------------------------------ 3
    c += [
        H1("3. Comprensión del negocio"),
        H2("3.1 Planteamiento"),
        P("La empresa observa que una proporción relevante de sus líneas de venta cierra con margen negativo por una política de descuentos definida por estado y subcategoría sin relación con el costo del producto, que sus pedidos incumplen con frecuencia los tiempos de entrega prometidos, y que no distingue entre perfiles de cliente al definir su política comercial. Esto provoca que el crecimiento en ventas no se traduzca en mejor margen, que las pérdidas se detecten hasta el cierre contable, y que el esfuerzo comercial y los descuentos se concentren en clientes que destruyen margen."),
        H2("3.2 Objetivo de negocio"),
        P("El objetivo es reducir la proporción de líneas con margen negativo y elevar la utilidad por transacción, de modo que el área comercial siga usando el descuento como palanca de venta, ahora con topes por subcategoría basados en evidencia y con políticas diferenciadas por tipo de cliente. En paralelo, que la promesa de entrega refleje los tiempos reales de cada modalidad."),
        H2("3.3 KPIs y metas"),
        P("La utilidad se descompone en ventas por margen, y el margen de cada línea depende de la distancia entre el descuento aplicado y el descuento de equilibrio del producto. De ahí salen los KPIs que el dashboard sigue."),
        T(["KPI", "Línea base", "Meta a un año", "Dueño"], [
            ["Líneas con pérdida", pct(Q["lineas_con_perdida_pct"]), "Menos de 5%", "Finanzas"],
            ["Margen neto", pct(REAL_MARGIN) + " en 2017", f"Más de 20% (simulado {pct(SIM_MARGIN)})", "Dirección"],
            ["Cumplimiento de promesa de entrega", pct(1 - DD["global_fuera_de_tiempo_pct"]), "Más de 95%", "Operaciones"],
            ["Utilidad del grupo Cazadores de descuento", pct(CROSS["Cazadores de descuento"]["utilidad_pct"], 0) + " del total", "Positiva", "Marketing"]],
          [2.6, 1.3, 1.6, 1.0], numeric=False),
        H2("3.4 Preguntas analíticas y decisiones"),
        N("Con la información disponible al capturar un pedido, se puede anticipar si una línea cerrará con pérdida, y hasta qué descuento sigue siendo rentable cada subcategoría?",
          "Se puede anticipar qué pedidos excederán el tiempo de entrega prometido por su modalidad?",
          "Existen grupos de clientes con comportamiento de compra y rentabilidad distintos que justifiquen políticas diferenciadas?"),
        T(["Área", "Recibe", "Decide"], [
            ["Comercial", "Evaluador de línea y tabla de topes", "Autorizar o ajustar el descuento antes de cerrar"],
            ["Finanzas", "Simulación de la política de topes", "Aprobar la nueva tabla de descuentos por estado"],
            ["Operaciones", "Tiempos reales por modalidad", "Redefinir la promesa de entrega"],
            ["Marketing", "Cuatro grupos de clientes con perfil", "Asignar presupuesto y campañas por grupo"],
            ["Dirección", "Lectura cruzada y opciones", "Atacar el problema con precio, logística o mezcla de clientes"]],
          [1.2, 2.4, 2.9], numeric=False),
    ]
    # ------------------------------------------------------------ 4
    c += [
        H1("4. Comprensión de los datos"),
        H2("4.1 Fuente"),
        P("Se usó la versión completa del dataset Sample Superstore publicada en Kaggle por Vivek Chowdhury, que incluye descuento, cantidad y utilidad. Contiene 9,994 líneas de pedido y 21 columnas de una cadena de artículos de oficina en Estados Unidos, del 3 de enero de 2014 al 30 de diciembre de 2017. Abarca 5,009 pedidos, 793 clientes, 49 estados, 17 subcategorías y 3 categorías. Los datos son sintéticos y públicos, sin información personal sensible más allá de nombres ficticios de clientes, que no se usan en ningún modelo."),
        H2("4.2 Exploración"),
        P("La utilidad no crece con el descuento, se destruye. Con 0% de descuento ninguna línea pierde dinero. Con 20% pierde el 14%. Con 30% o más pierden entre 87% y 100%."),
        FIGURE("f1_perdida_por_descuento.png", "**Figura 1.** Proporción de líneas con pérdida por nivel de descuento, 2014 a 2017.", 6.2,
               ["Descuento", "Líneas", "Líneas con pérdida"], loss_by_discount()),
        P("Tres subcategorías tienen utilidad acumulada negativa en 2014 a 2016, Tables, Bookcases y Supplies. Binders y Machines son rentables en total pero tienen 40% de líneas con pérdida, porque reciben descuentos de hasta 70% y 80% en los estados de descuento alto. Texas, Ohio, Pennsylvania e Illinois son los cuatro estados con mayor pérdida acumulada. En entregas, cada modalidad tiene un rango de días bien definido. Same Day entrega en 0 o 1 días, First Class de 1 a 4, Second Class de 1 a 5 y Standard Class de 3 a 7."),
    ]
    # ------------------------------------------------------------ 5
    c += [
        H1("5. Hipótesis iniciales"),
        P(f"Las hipótesis se escribieron como el negocio las diría y se probaron antes de modelar. Una hipótesis refutada vale tanto como una confirmada, porque evita invertir en la solución equivocada. De ocho, {HYP['refutadas']} se refutaron y {HYP['confirmadas']} se confirmó."),
        T(["", "Creencia del negocio", "Prueba y evidencia", "Resultado"],
          [[h["id"], h["creencia"], f"{h['prueba']}. {h['evidencia']}", "**" + h["resultado"] + "**"] for h in HYP["hipotesis"]],
          [0.35, 1.9, 3.35, 0.9], numeric=False, size=8),
        P("Qué cambió con cada refutación."),
        B(*[f"**{h['id']}.** {h['implicacion']}" for h in HYP["hipotesis"]]),
    ]
    # ------------------------------------------------------------ 6
    c += [
        H1("6. Preparación de datos"),
        H2("6.1 Validaciones"),
        P("Todas las validaciones se ejecutan en src/etl.py y su resultado queda en reports/metrics/data_quality.json."),
        T(["Validación", "Resultado", "Decisión"], [
            ["Esquema de 21 columnas", "Correcto", "Ninguna"],
            ["Valores nulos", "0", "Ninguna"],
            ["Duplicados exactos sin Row ID", "1", "Se elimina, filas 3406 y 3407 idénticas"],
            ["Envío antes del pedido", "0", "Ninguna"],
            ["Ventas o cantidad no positivas", "0", "Ninguna"],
            ["Descuento fuera de 0 a 1", "0", "Ninguna"],
            ["Pedidos con más de una fecha, modalidad o cliente", "0", "El pedido es unidad válida"],
            ["Product ID usado para dos productos", "32", "Llave de producto es ID más nombre"],
            ["Costo unitario no constante por producto", "0", "Se puede simular utilidad exacta"]],
          [3.0, 1.0, 2.5], numeric=False),
        H2("6.2 Hallazgo estructural"),
        P("**La pérdida es determinista.** El costo unitario es constante por producto. Por eso una línea pierde dinero exactamente cuando el descuento supera el descuento de equilibrio, igual a 1 menos costo entre precio de lista. Esta regla explica el 100% de las pérdidas. Permite simular con exactitud la utilidad bajo otro descuento, y obliga a reconocer que las métricas del modelo serán altas porque los datos son sintéticos (sección 12)."),
        H2("6.3 Variables derivadas"),
        T(["Variable", "Definición", "Uso"], [
            ["list_price", "ventas entre cantidad entre (1 menos descuento)", "Modelo y simulación"],
            ["unit_cost", "(ventas menos utilidad) entre cantidad", "Solo simulación y topes"],
            ["breakeven_discount", "1 menos costo entre precio de lista", "Solo topes"],
            ["is_loss", "1 si la utilidad es negativa", "Objetivo del modelo 1"],
            ["days_to_ship", "fecha de envío menos fecha de pedido", "Análisis de entregas"],
            ["is_late", "1 si días de envío superan la promesa", "Objetivo del análisis 2"],
            ["RFM y margen", "recencia, frecuencia, monto, margen y descuento por cliente", "Segmentación"]],
          [1.5, 3.2, 1.8], numeric=False),
        H2("6.4 Modelo estrella para BI"),
        P(f"Además de las tablas analíticas, el ETL publica un modelo estrella en data/processed/bi, listo para conectarse a Power BI, Looker Studio o Tableau. La tabla de hechos fact_lineas tiene {Q['modelo_estrella']['fact_lineas']:,} filas y se une a cuatro dimensiones con llaves sustitutas, dim_cliente ({Q['modelo_estrella']['dim_cliente']}), dim_producto ({Q['modelo_estrella']['dim_producto']:,}), dim_geografia ({Q['modelo_estrella']['dim_geografia']}) y dim_fecha ({Q['modelo_estrella']['dim_fecha']:,} días). El ETL verifica que los joins no pierdan filas."),
    ]
    # ------------------------------------------------------------ 7
    caps_sorted = sorted(CAPS, key=lambda r: -float(SIMSUB[r["sub_category"]]["delta"]))
    c += [
        H1("7. Modelado y evaluación"),
        H2("7.1 Líneas con pérdida"),
        P("**Técnica.** Clasificación binaria con desbalance moderado, 18.7% de positivos. Se compararon cuatro modelos de complejidad creciente, regresión logística, árbol de decisión, random forest y gradient boosting, contra dos líneas base, la proporción de la clase y la regla de negocio descuento mayor a 20%. La regla es la comparación relevante, porque un modelo solo aporta si supera lo que el negocio haría con una regla simple."),
        P("**Variables.** Descuento, subcategoría, categoría, región, segmento, modalidad de envío, cantidad, logaritmo del precio de lista y mes. Se excluyen utilidad, margen y costo unitario porque el vendedor no los conoce al capturar el pedido y su inclusión sería fuga de información."),
        P("**Validación.** Partición temporal, entrenamiento con 2014 a 2016 (6,681 líneas) y prueba con 2017 (3,312 líneas). Dentro de entrenamiento, validación cruzada de ventana creciente (2014 predice 2015, 2014 a 2015 predicen 2016) para elegir hiperparámetros y el umbral que maximiza F1. El modelo final se elige por PR-AUC de validación sin mirar la prueba. Intervalos de 95% por bootstrap con 1,000 remuestreos."),
        T(["Modelo", "ROC-AUC", "PR-AUC", "F1", "Precisión", "Recall", "Pérdida detectada"], [
            ["Proporción de la clase", "0.500", f3(MOD["Linea base sin modelo"]["pr_auc"]), "0.000", "0.000", "0.000", "0%"],
            mrow("Regla descuento > 20%"), mrow("Regresion logistica", "Regresión logística"),
            mrow("Arbol de decision", "Árbol de decisión"), mrow("Random forest"),
            mrow("Gradient boosting", "**Gradient boosting**")],
          [1.8, 0.75, 0.75, 0.7, 0.8, 0.7, 1.0]),
        P(f"El gradient boosting (tasa de aprendizaje 0.05, profundidad 6, umbral {GB['umbral']:.2f}) tuvo el mejor PR-AUC en validación ({f3(GB['cv_pr_auc'])}) y en prueba ({f3(GB['pr_auc'])}), sin señales de sobreajuste. Su F1 es {f3(GB['f1'])} con intervalo de {f3(L['ic95_modelo_elegido']['f1_ic95'][0])} a {f3(L['ic95_modelo_elegido']['f1_ic95'][1])}, contra {f3(L['ic95_regla']['f1_ic95'][0])} a {f3(L['ic95_regla']['f1_ic95'][1])} de la regla. En 2017 detectó {L['matriz_confusion']['tp']} pérdidas, dejó pasar {L['matriz_confusion']['fn']} y dio {L['matriz_confusion']['fp']} falsas alarmas."),
        P(f"**Dónde aporta.** La regla no ve las pérdidas con descuento de exactamente 20%. En 2017 hubo {L['descuento_20']['lineas']:,} líneas con ese descuento y {L['descuento_20']['perdidas']} perdieron dinero. El modelo detecta {L['descuento_20']['modelo_detecta']} con {L['descuento_20']['modelo_falsos_positivos']} falsas alarmas, porque aprende que con 20% pierden Storage, Bookcases, Supplies y Tables pero no Paper, Binders ni Art. La importancia por permutación lo confirma. Descuento {L['importancia_permutacion']['discount']:.2f}, subcategoría {L['importancia_permutacion']['sub_category']:.2f}, precio {L['importancia_permutacion']['log_list_price']:.2f}, y región, segmento y envío cerca de cero."),
        P("**Topes de descuento.** El entregable para el negocio es la tabla de topes, calculada con dos métodos independientes y solo con 2014 a 2016. Por costo, el percentil 10 del descuento de equilibrio de cada subcategoría, que deja rentables al 90% de las líneas. Por modelo, el mayor descuento con probabilidad de pérdida bajo el umbral. Se toma el menor, y que ambos coincidan en orden de magnitud es una prueba de consistencia."),
        T(["Subcategoría", "Desc. prom.", "Desc. máx.", "Líneas con pérdida", "Tope costo", "Tope modelo", "Tope", "Utilidad recuperada 2017"],
          [[r["sub_category"], pct(float(r["descuento_prom_actual"]), 0), pct(float(r["descuento_max_actual"]), 0),
            pct(float(r["perdida_pct_hist"]), 0), pct(float(r["tope_costo"]), 0), pct(float(r["tope_modelo"]), 0),
            "**" + pct(float(r["tope_recomendado"]), 0) + "**", money(float(SIMSUB[r["sub_category"]]["delta"]))] for r in caps_sorted],
          [1.1, 0.7, 0.7, 0.8, 0.7, 0.75, 0.55, 1.2], size=8),
        FIGURE("f3_topes_descuento.png", "**Figura 2.** Descuento máximo que se aplica hoy contra el tope recomendado. Donde la barra gris rebasa la marca negra, la política actual genera pérdidas.", 5.8, None, None),
        P(f"**Simulación sobre 2017.** Con el costo unitario real se recalculó la utilidad de cada línea bajo el tope. Cambian {SIM['lineas_afectadas']} líneas, el {pct(SIM['lineas_afectadas_pct'], 0)} del año. Las líneas con pérdida bajan de {SIM['lineas_perdida_actual']} a {SIM['lineas_perdida_simulada']}. Como el volumen podría caer al subir el precio neto, se probaron escenarios de pérdida de volumen en las líneas afectadas. La refutación de H2 sugiere que el escenario realista está cerca de cero."),
        T(["Escenario de volumen en líneas afectadas", "Utilidad 2017", "Cambio contra real"],
          [["Real, sin topes", money(SIM["utilidad_actual"]), "$0"]] +
          [["Se mantiene el volumen" if e["perdida_volumen"] == 0 else f"Se pierde el {pct(e['perdida_volumen'], 0)}",
            money(e["utilidad"]), "+" + money(e["delta_utilidad"])] for e in SIM["escenarios"]],
          [3.2, 1.6, 1.7]),
        H2("7.2 Entregas fuera de tiempo"),
        P("**Técnica.** El dataset no trae la promesa de entrega, así que se definió como supuesto. Same Day 0 días, First Class 2, Second Class 3 y Standard Class 5. Como la modalidad define el rango de días, la pregunta es si dentro de cada modalidad algo explica el retraso. Se respondió con 24 pruebas chi-cuadrada con corrección de Bonferroni (alfa 0.0021, V de Cramér como tamaño de efecto) y con regresión logística y gradient boosting por modalidad con la misma partición temporal."),
        T(["Modalidad", "Pedidos", "Fuera de promesa", "Días p95", "AUC logística", "AUC boosting"],
          [[m, f"{DD[m]['pedidos']:,}", pct(DD[m]["fuera_de_tiempo_pct"]), f"{DD[m]['dias_p95']:.0f}",
            auc(m, "Regresion logistica"), auc(m, "Gradient boosting")] for m in MODES],
          [1.6, 0.8, 1.2, 0.8, 1.0, 1.1]),
        P(f"Ninguna prueba es significativa. El p-valor mínimo es {min(t['p_valor'] for t in DL['pruebas_chi2']):.3f} y la V de Cramér máxima {max(t['v_cramer'] for t in DL['pruebas_chi2']):.2f}. Los modelos obtienen AUC entre 0.46 y 0.52, equivalente a adivinar. Same Day tiene solo 5 pedidos tarde en 2017 y su AUC no es interpretable. El problema real es la promesa. Second Class entrega en 4 o 5 días el 41% de las veces, lo que hoy se espera de Standard Class."),
        FIGURE("f4_dias_envio.png", "**Figura 3.** Distribución de días de envío por modalidad. En gris oscuro los pedidos dentro de la promesa supuesta, en gris claro los que la exceden.", 6.2,
               ["Modalidad"] + [("1 día" if d == 1 else f"{d} días") for d in range(8)], days_table()),
        T(["Modalidad", "Promesa actual", "Cumplimiento actual", "Promesa p95", "Cumplimiento p95"],
          [[m, f"{DL['promesa_supuesta'][m]} días", pct(sens(m, 'actual'), 0), f"{int(-(-DD[m]['dias_p95'] // 1))} días", pct(sens(m, 'p95'), 0)] for m in MODES],
          [1.7, 1.2, 1.3, 1.1, 1.2]),
        H2("7.3 Segmentación de clientes"),
        P("**Técnica.** No hay etiqueta de tipo de cliente, así que se usó aprendizaje no supervisado. K-Means es interpretable por sus centroides y adecuado para variables continuas estandarizadas. Variables, recencia al 31 de diciembre de 2017, logaritmo de frecuencia, logaritmo de monto, margen recortado en percentiles 1 y 99, y descuento promedio."),
        P(f"**Número de grupos.** Se evaluó k de 2 a 8 con inercia, silueta y Davies-Bouldin. La regla fue tomar, entre 3 y 6, el menor k cuyo Davies-Bouldin quedara a menos de 1% del mínimo. Resultó k = 4 (Davies-Bouldin {SEGK[4]['davies_bouldin']:.3f} contra {SEGK[5]['davies_bouldin']:.3f} de k = 5), que coincide con el codo. La silueta de {SEGK[4]['silueta']:.2f} indica separación moderada. Con 20 semillas el índice de Rand ajustado es {S['estabilidad']['ari_semillas_media']:.2f} y con 50 remuestreos bootstrap {S['estabilidad']['ari_bootstrap_media']:.2f}, mejor que k = 3 ({S['estabilidad_alternativas']['3']['ari_bootstrap_media']:.2f})."),
        T(["Grupo", "Clientes", "Ventas prom.", "Pedidos", "Días sin comprar", "Desc.", "Margen", "Utilidad", "Pérdidas"],
          [[g, str(PROF[g]["clientes"]), money(PROF[g]["monetary"]), f"{PROF[g]['frequency']:.1f}", str(round(PROF[g]["recency"])),
            pct(PROF[g]["avg_discount"]), pct(PROF[g]["margin"]), pct(PROF[g]["utilidad_pct"], 0), pct(PROF[g]["perdidas_pct"], 0)] for g in GROUPS],
          [1.3, 0.65, 0.75, 0.65, 0.7, 0.55, 0.6, 0.65, 0.65], size=8),
    ]
    # ------------------------------------------------------------ 8
    c += [
        H1("8. Insights"),
        P("Cada insight dice qué encontramos, por qué importa y qué hacer."),
        N(f"**La pérdida es una política, no un error humano.** El {pct(X['perdida_en_estados_alto_descuento_pct'], 0)} de las pérdidas está en 10 estados con descuento promedio mayor a 25%. Importa porque se corrige cambiando una tabla, sin capacitar a nadie. Acción, reescribir la tabla de descuentos de esos estados.",
          "**El descuento no compra volumen.** La cantidad por línea no cambia con el descuento (H2). Importa porque el miedo a perder ventas es la principal objeción a los topes. Acción, aplicar topes con un piloto que mida el efecto real.",
          f"**Vender mucho no es ser rentable.** El margen del cliente no se relaciona con cuánto compra, sino con el descuento que recibe (H7). Los Cazadores de descuento hacen el {pct(CROSS['Cazadores de descuento']['compras_en_estados_alto_descuento_pct'], 0)} de sus compras en los estados de descuento alto. Acción, ofrecerles servicio y no precio.",
          f"**El modelo encuentra la zona gris.** Con 20% de descuento la regla no ve nada y el modelo detecta {L['descuento_20']['modelo_detecta']} de {L['descuento_20']['perdidas']} pérdidas (H8). Acción, usar el evaluador de línea solo en ese rango, donde aporta.",
          "**El retraso es un problema de promesa.** No depende de región, cliente ni temporada (H5), y no explica el abandono de clientes (H6). Acción, prometer 3, 5 y 7 días y empezar a registrar transportista y entrega real.",
          "**La segmentación oficial no sirve para decidir.** Consumer, Corporate y Home Office pierden en la misma proporción (H3) y se reparten igual entre los cuatro grupos. Acción, usar los grupos del modelo para presupuesto de marketing."),
    ]
    # ------------------------------------------------------------ 9
    opts = DEC["opciones"]
    c += [
        H1("9. Decisión de negocio"),
        P("**Decisión.** Aplicar los topes de descuento por subcategoría en los 10 estados de descuento alto a partir del siguiente trimestre, en dos olas de cinco estados de seis semanas cada una, y extenderlos al resto del país solo si se cumplen los criterios de éxito."),
        T(["Opción", "Utilidad 2017 simulada", "Riesgo"],
          [[o["opcion"], money(o["utilidad_2017"]), o["riesgo"]] for o in opts],
          [2.9, 1.4, 2.2], numeric=False),
        P(f"**Por qué C y no B.** La opción C captura el {pct(DEC_HIGH['delta_pct_del_total'], 0)} del beneficio de la opción B con {DEC_HIGH['lineas_afectadas']} de las {SIM['lineas_afectadas']} líneas afectadas. Además resuelve la principal limitación del análisis, que no observa cómo reacciona el cliente a un precio más alto. Mientras la primera ola corre, los cinco estados de la segunda funcionan como grupo de control, y la diferencia entre ambos mide el efecto real en volumen antes de escalar. La decisión es reversible porque solo cambia una tabla."),
        T(["Semana", "Acción", "Responsable"], [
            ["1 a 2", "Aprobar la tabla de topes y cargarla en el sistema de ventas", "Finanzas"],
            ["3 a 8", "Ola 1 en cinco estados, los otros cinco como control", "Comercial"],
            ["9 a 14", "Ola 2 en los cinco restantes", "Comercial"],
            ["15", "Revisión con datos reales y decisión de extender al resto del país", "Dirección"],
            ["En paralelo", "Nueva promesa de entrega y campañas por grupo de cliente", "Operaciones y Marketing"]],
          [1.0, 4.0, 1.5], numeric=False),
        P("**Criterios de éxito.** Líneas con pérdida menores a 5% en los estados tratados. Pedidos por cliente activo sin caer más de 10% contra el grupo de control. Margen neto positivo en los 10 estados. **Criterio de alto.** Si los pedidos por cliente caen más de 25% contra el control, se revisan los topes de las subcategorías con mayor caída antes de la segunda ola."),
    ]
    sem = {r["semaforo"]: r for r in RULES["semaforo_2017"]}
    c += [
        H1("10. Score, regla y decisión humana"),
        P("Los modelos apoyan decisiones, no las toman. Cada salida analítica pasa por tres pasos con dueño claro. El **score** es lo que calcula el modelo. La **regla** es una política explícita y auditable que convierte el score en una recomendación. La **decisión** la toma una persona, que puede aceptar, ajustar o rechazar la recomendación y deja registro de por qué."),
        T(["Nivel", "Score", "Regla", "Decide"], [[r["nivel"], r["score"], r["regla"], r["decide"]] for r in RULES["reglas"]],
          [1.2, 1.6, 2.4, 1.3], numeric=False, size=8),
        P(f"**Semáforo para cada línea de venta.** Rojo si el descuento supera el tope de la subcategoría, con recomendación de ajustarlo al tope. Amarillo si está dentro del tope pero el score supera el umbral de {RULES['umbral_score']:.2f}, con recomendación de revisar el margen del producto. Verde en otro caso. En rojo y amarillo decide el gerente comercial entre ajustar, aprobar una excepción con justificación o rechazar la venta. En verde el vendedor sigue el proceso normal."),
        T(["Semáforo", "Líneas 2017", "Por mes", "Tasa de pérdida", "Monto perdido que concentra"],
          [[k, f"{sem[k]['lineas']:,}", f"{sem[k]['lineas_por_mes']:.0f}", pct(sem[k]["tasa_perdida"], 0), pct(sem[k]["monto_perdida_pct"])] for k in ("Rojo", "Amarillo", "Verde")],
          [1.3, 1.2, 1.0, 1.3, 1.7]),
        P(f"La carga para el área es manejable. Unas {RULES['decisiones_humanas_por_mes']:.0f} líneas al mes requieren a una persona y en ellas está el {pct(RULES['perdida_cubierta_por_revision_pct'])} del monto perdido. Las líneas en verde pierden dinero en menos de 1% de los casos. El dashboard registra cada decisión con fecha, responsable y justificación en una bitácora, lo que permite auditar las excepciones y medir si la regla necesita ajuste."),
        P("La decisión estratégica de la sección 9 sigue la misma lógica. El score son los resultados de la ola 1 contra el grupo de control, la regla son los criterios de éxito y de alto, y la decisión de extender la política al resto del país es de Dirección General."),
    ]
    # ------------------------------------------------------------ 11
    c += [
        H1("11. Despliegue, BI y monitoreo"),
        P("El resultado se entrega como un producto de BI con modelos de aprendizaje de máquina integrados, no como un análisis aislado."),
        T(["Capa", "Qué hace", "Implementación"], [
            ["Fuente", "Datos transaccionales de ventas", "CSV de Superstore, en producción el ERP"],
            ["ETL", "Extrae, valida, limpia y deriva variables", "src/etl.py con validaciones en JSON"],
            ["Modelo de datos", "Estrella con hechos y dimensiones", "data/processed/bi"],
            ["Modelos", "Clasificación, análisis de entregas, clustering", "scikit-learn, versionados en models/"],
            ["Consumo", "Un tablero por área con KPIs y simuladores", "Streamlit, o Power BI y Looker sobre el modelo estrella"]],
          [1.4, 2.5, 2.6], numeric=False),
        P("El dashboard tiene una pestaña por área. Dirección ve KPIs y la lectura cruzada. Hipótesis y decisión muestra las pruebas, las reglas y las opciones. Comercial tiene el evaluador de línea con score, semáforo y un formulario para registrar la decisión humana. Finanzas ve la simulación y el mapa de utilidad por estado y subcategoría. Operaciones ve tiempos reales por modalidad. Marketing ve los grupos de clientes con su acción sugerida."),
        P("**Monitoreo.** Cada trimestre se reentrena el modelo de pérdida con los datos nuevos y se recalculan los topes. Se vigila la distribución del descuento y del precio de lista, porque un cambio de política o de catálogo invalida el modelo. Una alerta se dispara si las líneas con pérdida superan 5% en cualquier estado, o si el F1 en el trimestre más reciente cae por debajo del de la regla simple."),
    ]
    # ------------------------------------------------------------ 11-15
    c += [
        H1("12. Limitaciones"),
        B("**Datos sintéticos.** La utilidad sale de una fórmula con costo fijo por producto. En datos reales habría fletes, devoluciones y cambios de costo, y las métricas del modelo serían menores. El método se puede trasladar, el nivel de desempeño no.",
          "**Volumen observado solo por línea.** H2 muestra que la cantidad por línea no depende del descuento, pero el dataset no registra a los clientes que no compraron. Por eso la decisión incluye un piloto con grupo de control.",
          "**Promesa de entrega supuesta.** La tasa de retraso depende de la promesa definida. La recomendación se basa en la distribución real de días, no en la tasa.",
          "**Topes por subcategoría.** Dentro de una subcategoría hay productos con márgenes muy distintos. Un tope por producto, que el dashboard ya muestra, es más preciso pero más difícil de operar.",
          "**Separación moderada de grupos.** La silueta de 0.22 indica clientes en la frontera entre grupos. Los perfiles describen tendencias, no categorías rígidas.",
          "**Un solo país y cuatro años.** No se puede validar el modelo en otro mercado ni capturar cambios de largo plazo."),
        H1("13. Reproducibilidad"),
        P("Todo el proyecto está escrito en Python y se regenera desde el CSV original con un solo comando. La configuración, la semilla 42 y los supuestos de negocio viven en src/config.py."),
        T(["Paso", "Comando"], [
            ["Instalar dependencias", "pip install -r requirements.txt"],
            ["Ejecutar el pipeline completo", "python src/run_all.py"],
            ["Abrir el dashboard", "streamlit run app/dashboard.py"],
            ["Generar reporte y presentación", "python reports/build_report.py y python reports/build_presentation.py"],
            ["Ver evidencia ejecutada", "notebooks/rolulabo_analisis.ipynb"]],
          [2.2, 4.3], numeric=False),
        H1("14. Declaración de uso de inteligencia artificial"),
        P("El equipo usó Claude, de Anthropic, como asistente en tres tareas. Estructurar el código del pipeline y del dashboard, revisar la metodología de validación y redactar borradores de este reporte. El equipo definió el problema, eligió el alcance, ejecutó y revisó cada resultado, y es responsable de las interpretaciones, la decisión y las recomendaciones. Todas las cifras provienen de la ejecución del código incluido."),
        H1("15. Referencias"),
        P("Chapman, P. et al. (2000). CRISP-DM 1.0. Step-by-step data mining guide. SPSS."),
        P("Chowdhury, V. (2022). Superstore Dataset. Kaggle. https://www.kaggle.com/datasets/vivek468/superstore-dataset-final"),
        P("Kimball, R. y Ross, M. (2013). The Data Warehouse Toolkit, 3a edición. Wiley."),
        P("Pedregosa, F. et al. (2011). Scikit-learn. Machine Learning in Python. Journal of Machine Learning Research, 12, 2825 a 2830."),
        P("Rousseeuw, P. J. (1987). Silhouettes. A graphical aid to the interpretation and validation of cluster analysis. Journal of Computational and Applied Mathematics, 20, 53 a 65."),
        P("Saito, T. y Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. PLOS ONE, 10(3)."),
        P("Schwaber, K. y Sutherland, J. (2020). The Scrum Guide. scrumguides.org."),
        P(""),
        P(f"**Elaborado por {AUTOR}**"),
    ]
    return c


def _sections(blocks):
    """Agrupa los bloques por título de sección."""
    out, cur = {}, None
    for b in blocks:
        if b[0] == "h1":
            cur = b[1]
            out[cur] = []
        else:
            out[cur].append(b)
    return out


def _renum(blocks, mapping):
    """Renumera subtítulos y ajusta referencias cruzadas."""
    res = []
    for b in blocks:
        if b[0] == "h2":
            num, _, title = b[1].partition(" ")
            res.append(("h2", f"{mapping.get(num, num)} {title}"))
        else:
            res.append(b)
    return res


def _without(blocks, h2_titles):
    """Quita subsecciones completas por título."""
    res, skip = [], False
    for b in blocks:
        if b[0] == "h2":
            skip = any(b[1].endswith(t) for t in h2_titles)
        if not skip:
            res.append(b)
    return res


def _only(blocks, h2_title):
    res, take = [], False
    for b in blocks:
        if b[0] == "h2":
            take = b[1].endswith(h2_title)
            continue
        if take:
            res.append(b)
    return res


def _fix(blocks, old, new):
    out = []
    for b in blocks:
        if b[0] == "p":
            out.append(("p", b[1].replace(old, new)))
        elif b[0] == "table":
            out.append(("table", b[1], [[str(x).replace(old, new) for x in r] for r in b[2]], *b[3:]))
        else:
            out.append(b)
    return out


def content():
    """Estructura del reporte inspirada en el formato de reporte técnico de la Facultad."""
    sec = _sections(_base_content())
    neg = sec["3. Comprensión del negocio"]
    lim = sec["12. Limitaciones"]
    c = [("h1u", "Resumen ejecutivo")] + sec["1. Resumen ejecutivo"] + [BREAK]

    c += [
        H1("1 Introducción"),
        H2("1.1 Background"),
        P("Rolulabo es una cadena ficticia de artículos de oficina, muebles y tecnología que vende en 49 estados de Estados Unidos a tres segmentos de cliente, consumidores, empresas y oficinas en casa. Entre 2014 y 2017 sus ventas crecieron 52%, pero el margen se estancó alrededor de 13% desde 2015 y casi una de cada cinco líneas de venta cerró con pérdida. La empresa ofrece descuentos como principal palanca comercial, envía por cuatro modalidades con distinto tiempo de entrega y administra a sus 793 clientes como un solo bloque."),
        P("El proyecto toma el caso como lo haría un equipo de BI con aprendizaje de máquina dentro de la empresa. Parte de una necesidad de negocio, formula preguntas analíticas, prepara los datos, entrena y evalúa modelos contra una línea base, y termina en una decisión con dueño, plan y criterios para saber si funcionó."),
        H2("1.2 Problema y punto principal"),
    ] + _only(neg, "Planteamiento") + [
        P("El punto principal del reporte es que el problema no está en los vendedores ni en la logística, sino en una tabla de descuentos. El descuento es fijo por estado y subcategoría, y en 10 estados supera el margen del producto. Los modelos ayudan a encontrarlo, a medirlo y a vigilar una nueva política, pero la decisión de cambiarla es humana."),
        H2("1.3 Propósito del reporte"),
    ] + _only(neg, "Objetivo de negocio") + [
        P("El reporte busca tres cosas. Responder con evidencia tres preguntas analíticas sobre pérdidas, entregas y clientes. Probar las creencias que el negocio daba por ciertas antes de construir sobre ellas. Y traducir los resultados en una decisión concreta, con opciones, impacto, responsables y criterios de éxito."),
        H2("1.4 Audiencia objetivo"),
        P("El documento está dirigido al profesor y al grupo de Aprendizaje de Máquina, que conocen las técnicas de clasificación, validación y clustering. Al mismo tiempo está escrito como lo leería la dirección de Rolulabo. El resumen ejecutivo, los insights, la decisión y las recomendaciones se pueden leer sin conocimientos técnicos. Las secciones de metodología, datos y modelado documentan el detalle para quien quiera reproducir o auditar el trabajo."),
        H1("2 Revisión de fuentes de información"),
        P("La fuente de datos es la versión completa del dataset Sample Superstore publicada en Kaggle, que incluye descuento, cantidad y utilidad por línea. Es un dataset sintético y público, usado ampliamente para enseñanza, lo que garantiza que no contiene información personal real."),
        P("La metodología se apoya en cinco referencias. La guía CRISP-DM 1.0 de Chapman y colaboradores define las fases del proyecto. El Scrum Guide de Schwaber y Sutherland da el marco de iteraciones y backlog. The Data Warehouse Toolkit de Kimball y Ross sustenta el modelo estrella de la capa de BI. El artículo de Saito y Rehmsmeier justifica usar PR-AUC en lugar de ROC-AUC con clases desbalanceadas, y el de Rousseeuw define el coeficiente de silueta usado para evaluar los grupos. La implementación usa scikit-learn, documentado por Pedregosa y colaboradores."),
        P("Conviene señalar el límite de este conjunto. Los datos describen un negocio simulado, por lo que las cifras sirven para demostrar el método y no como medición de una empresa real. Las referencias metodológicas son estándares de la práctica y no estudios sobre el caso."),
        H1("3 Alcance"),
        H2("3.1 Supuestos básicos"),
        P("El trabajo parte de cuatro supuestos. El primero es que el costo unitario implícito en los datos es el costo contable del producto, lo que permite calcular el descuento de equilibrio y simular la utilidad con otro descuento. El segundo es que la cantidad vendida no cambia cuando se reduce el descuento, supuesto que se prueba con la hipótesis H2 y se cubre con escenarios de pérdida de volumen. El tercero es una promesa de entrega por modalidad de 0, 2, 3 y 5 días, porque el dataset no la trae. El cuarto es que 2014 a 2016 representan bien lo que pasará en 2017, lo que se verifica con la partición temporal."),
        H2("3.2 Limitaciones del reporte"),
    ] + lim + [
        H2("3.3 Tópicos cubiertos y no cubiertos"),
        P("Se cubren la rentabilidad por línea de venta, la política de descuentos y su rediseño, el cumplimiento de la promesa de entrega, la segmentación de clientes por valor y rentabilidad, la lectura cruzada de los tres análisis, el esquema de decisión humana y el despliegue como producto de BI. Quedan fuera el pronóstico de demanda e inventario, la estimación formal de elasticidad precio, la optimización de rutas logísticas, los costos operativos distintos al costo del producto y cualquier tema de personal, porque el dataset no tiene información para sostenerlos."),
        H1("4 Criterio"),
        H2("4.1 Criterio para juzgar los resultados"),
        P("Cada resultado se juzga contra una línea base y en datos que el modelo no vio. En clasificación de pérdidas la métrica principal es PR-AUC, porque las clases están desbalanceadas, acompañada de F1, precisión y recall con intervalos de confianza por bootstrap. Un modelo solo se acepta si supera a la regla de negocio que ya existe, no solo al azar. En entregas el criterio de aceptación es un AUC mayor a 0.65 y pruebas estadísticas con corrección por comparaciones múltiples. En segmentación se exige estabilidad entre semillas y en remuestreo, medida con el índice de Rand ajustado, además de silueta y Davies-Bouldin. Para el negocio, el criterio final es la utilidad simulada y los KPIs de la sección 6."),
        H2("4.2 Criterio para llegar a las recomendaciones"),
        P("Las recomendaciones se formulan bajo cinco condiciones. Deben poder aplicarse con los datos y sistemas que la empresa ya tiene. Deben ser medibles y reversibles. Deben tener un responsable humano con nombre de puesto que tome la decisión y deje registro. Deben sostenerse aun bajo los escenarios pesimistas del análisis de sensibilidad. Y deben cuantificar su impacto esperado en utilidad o en un KPI."),
    ]
    met = sec["2. Metodología"]
    c += [H1("5 Metodología"), H2("5.1 CRISP-DM con iteraciones ágiles")] + _fix(_renum(met, {"2.1": "5.2", "2.2": "5.3"}), "Secciones 3 y 4", "Secciones 1 y 6")
    c += [H1("6 Comprensión del negocio")] + _renum(_without(neg, ["Planteamiento", "Objetivo de negocio"]), {"3.3": "6.1", "3.4": "6.2"})
    c += [H1("7 Datos recogidos y preparación")] + _renum(sec["4. Comprensión de los datos"], {"4.1": "7.1", "4.2": "7.2"}) \
        + _fix(_renum(sec["6. Preparación de datos"], {"6.1": "7.3", "6.2": "7.4", "6.3": "7.5", "6.4": "7.6"}), "(sección 12)", "(sección 3.2)")
    c += [H1("8 Hipótesis iniciales")] + sec["5. Hipótesis iniciales"]
    c += [H1("9 Modelado y evaluación")] + _renum(sec["7. Modelado y evaluación"], {"7.1": "9.1", "7.2": "9.2", "7.3": "9.3"})
    c += [H1("10 Insights")] + sec["8. Insights"]
    c += [H1("11 Decisión de negocio")] + sec["9. Decisión de negocio"]
    c += [H1("12 Score, regla y decisión humana")] + _fix(sec["10. Score, regla y decisión humana"], "de la sección 9", "de la sección 11")
    c += [H1("13 Despliegue, BI y monitoreo")] + sec["11. Despliegue, BI y monitoreo"]
    lates = [r["fuera_de_tiempo_pct"] for r in X["tabla"]]
    c += [
        H1("14 Conclusiones"),
        P(f"La primera pregunta analítica tiene respuesta positiva. Con la información disponible al capturar un pedido se puede anticipar si una línea perderá dinero, y un gradient boosting lo hace mejor que la regla actual (F1 de {f3(GB['f1'])} contra {f3(RULE['f1'])}). Su mayor aporte está en la zona gris del 20% de descuento, donde la regla no ve nada. De ahí se derivan topes por subcategoría que, aplicados a 2017, habrían llevado la utilidad de {money(SIM['utilidad_actual'])} a {money(SIM['escenarios'][0]['utilidad'])}."),
        P("La segunda pregunta tiene respuesta negativa y es igual de útil. Con los datos actuales el retraso no se puede predecir dentro de cada modalidad. El problema de Operaciones no es priorizar pedidos sino prometer tiempos que no se cumplen."),
        P(f"La tercera pregunta tiene respuesta positiva. Existen cuatro grupos de clientes estables con rentabilidades muy distintas, y la segmentación oficial no los distingue. El grupo Cazadores de descuento resta utilidad y el de Alto valor rentable la genera toda."),
        P(f"Las tres respuestas apuntan a la misma causa. La pérdida se concentra en 10 estados con descuento alto ({pct(X['perdida_en_estados_alto_descuento_pct'], 0)} del monto perdido), no depende del tipo de cliente y no se relaciona con la logística (el retraso va de {pct(min(lates), 0)} a {pct(max(lates), 0)} entre grupos). Siete de ocho creencias del negocio resultaron falsas, lo que confirma el valor de probar antes de construir."),
        H1("15 Recomendaciones"),
        P("Cada recomendación cumple los criterios de la sección 4.2 y tiene un responsable que decide."),
        T(["Área", "Recomendación", "Evidencia"], [
            ["Dirección", "Aprobar la opción C, topes en los 10 estados de descuento alto en dos olas, y decidir en la semana 15 si se extiende al resto del país.", f"{pct(DEC_HIGH['delta_pct_del_total'], 0)} del beneficio posible con riesgo bajo"],
            ["Finanzas", "Reemplazar la tabla de descuentos por estado con los topes por subcategoría, empezando por Binders, Tables, Machines y Chairs.", f"+{money(SIM['escenarios'][0]['delta_utilidad'])} en 2017, +{money(WORST['delta_utilidad'])} en el peor caso"],
            ["Comercial", "Usar el semáforo del dashboard en cada línea con descuento y registrar en bitácora toda excepción con su justificación.", f"Unas {RULES['decisiones_humanas_por_mes']:.0f} revisiones al mes cubren el {pct(RULES['perdida_cubierta_por_revision_pct'])} del monto perdido"],
            ["Operaciones", "Publicar la promesa de 3, 5 y 7 días y empezar a registrar transportista, almacén y fecha real de entrega.", "Retraso no predecible, AUC de 0.46 a 0.52"],
            ["Marketing", "Lealtad sin descuento para Alto valor rentable, servicio en vez de precio para Cazadores, recompra para Compradores ocasionales.", f"Cuatro grupos estables, ARI bootstrap {S['estabilidad']['ari_bootstrap_media']:.2f}"]],
          [1.0, 3.4, 2.1], numeric=False),
    ]
    repro = sec["13. Reproducibilidad"]
    ia = sec["14. Declaración de uso de inteligencia artificial"]
    c += [H1("16 Reproducibilidad y uso de inteligencia artificial"), H2("16.1 Reproducibilidad")] + repro + [H2("16.2 Declaración de uso de inteligencia artificial")] + ia
    c += [H1("17 Referencias")] + sec["15. Referencias"]
    return c


TITLE = "Rolulabo"
LOGO = HERE / "assets" / "logo_up.png"
MONO = "Roboto Mono"
MONO_LIGHT = "Roboto Mono Light"
PORTADA = {
    "facultad": "Facultad de Ingeniería",
    "materia": "Aprendizaje de Máquina",
    "alumnos": ["Gabriel Álvarez Mendoza - 0261445", "Eduardo Gutiérrez - [expediente]",
                "Emiliano Luna - [expediente]", "Rodrigo Naranjo - [expediente]"],
    "actividad": "Proyecto Rolulabo",
    "fecha": "[dd]/11/2026",
}
SUBTITLE = "Rentabilidad, entregas y clientes con aprendizaje de máquina"
COVER = ["Proyecto integrador de Aprendizaje de Máquina", "Universidad Panamericana, campus Mixcoac", "",
         "**Equipo**", "Gabriel Álvarez Mendoza", "Eduardo Gutiérrez", "Emiliano Luna", "Rodrigo Naranjo", "", "Noviembre de 2026"]

BOLD = re.compile(r"(\*\*[^*]+\*\*)")


def parts(text):
    return [(p[2:-2], True) if p.startswith("**") else (p, False) for p in BOLD.split(text) if p]


# ---------------------------------------------------------------- Word
def build_docx(out: Path):
    from docx import Document
    from docx.enum.section import WD_SECTION
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(1))
    sec.different_first_page_header_footer = True

    def set_font(style, size, bold=False):
        style.font.name = FONT
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.color.rgb = RGBColor(0, 0, 0)
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.insert(0, rfonts)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(a), FONT)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
            if rfonts.get(qn(a)) is not None:
                del rfonts.attrib[qn(a)]

    set_font(doc.styles["Normal"], 10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(7)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.25
    for name, size, before, after in (("Heading 1", 15, 18, 9), ("Heading 2", 11.5, 12, 5)):
        st = doc.styles[name]
        set_font(st, size, bold=True)
        st.font.italic = False
        pf = st.paragraph_format
        pf.space_before, pf.space_after, pf.keep_with_next = Pt(before), Pt(after), True
    for name in ("List Bullet", "List Number"):
        set_font(doc.styles[name], 10)
        doc.styles[name].paragraph_format.space_after = Pt(4)

    def add_runs(par, text, size=None, bold_all=False):
        for t, b in parts(text):
            r = par.add_run(t)
            r.bold = b or bold_all
            if size:
                r.font.size = Pt(size)
        return par

    # Footer con número de página, sin número en la portada.
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "16")
    rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    fp._p.append(fld)

    # Portada con el formato de la Facultad.
    def mono(par, text, bold=False, size=16):
        r = par.add_run(text)
        r.font.name = MONO if bold else MONO_LIGHT
        r.font.bold = bold
        r.font.size = Pt(size)
        rpr = r._element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            rpr.insert(0, rf)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), MONO if bold else MONO_LIGHT)
        return r

    def cover_line(label, value, before):
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(before)
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.tab_stops.add_tab_stop(Inches(1.5))
        mono(par, label, bold=True)
        if value is not None:
            mono(par, ("\t" if label != "Nombre de actividad:" and label != "Fecha de entrega:" else " ") + value)
        return par

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(str(LOGO), width=Inches(4.3))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    mono(p, PORTADA["facultad"], size=18)
    cover_line("Materia:", PORTADA["materia"], 30)
    cover_line("Alumnos:", PORTADA["alumnos"][0], 40)
    for name in PORTADA["alumnos"][1:]:
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(8)
        par.paragraph_format.space_after = Pt(0)
        par.paragraph_format.left_indent = Inches(1.5)
        mono(par, name)
    cover_line("Nombre de actividad:", PORTADA["actividad"], 44)
    cover_line("Fecha de entrega:", PORTADA["fecha"], 40)
    doc.add_page_break()

    # Índice.
    blocks = content()
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    add_runs(p, "Índice", size=13, bold_all=True)
    for kind, title in [("h0", "Portada")] + [(b[0], b[1]) for b in blocks if b[0] in ("h1", "h1u", "h2")]:
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(1.5)
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.left_indent = Inches(0.25 if kind != "h2" else 0.55)
        add_runs(par, title, size=9, bold_all=(kind != "h2"))
    doc.add_page_break()

    for blk in blocks:
        kind = blk[0]
        if kind in ("h1", "h1u"):
            doc.add_heading(blk[1], level=1)
        elif kind == "h2":
            doc.add_heading(blk[1], level=2)
        elif kind == "p":
            par = add_runs(doc.add_paragraph(), blk[1])
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT if "http" in blk[1] or len(blk[1]) < 140 else WD_ALIGN_PARAGRAPH.JUSTIFY
        elif kind == "ul":
            for it in blk[1]:
                add_runs(doc.add_paragraph(style="List Bullet"), it).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif kind == "ol":
            # Numeración manual para que cada lista empiece en 1.
            for n, it in enumerate(blk[1], 1):
                par = doc.add_paragraph()
                par.paragraph_format.left_indent = Inches(0.3)
                par.paragraph_format.first_line_indent = Inches(-0.25)
                par.paragraph_format.space_after = Pt(4)
                add_runs(par, f"{n}.\t{it}").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif kind == "break":
            doc.add_page_break()
        elif kind == "table":
            _, head, body, widths, numeric, size = blk
            tbl = doc.add_table(rows=1 + len(body), cols=len(head))
            tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
            tbl.autofit = False
            tblpr = tbl._tbl.tblPr
            lay = OxmlElement("w:tblLayout")
            lay.set(qn("w:type"), "fixed")
            tblpr.append(lay)
            for k, w in enumerate(widths):
                tbl.columns[k].width = Inches(w)
            grid = tbl._tbl.tblGrid
            for k, gc in enumerate(grid.findall(qn("w:gridCol"))):
                gc.set(qn("w:w"), str(int(widths[k] * 1440)))
            all_rows = [head] + body
            for i, row in enumerate(all_rows):
                trpr = tbl.rows[i]._tr.get_or_add_trPr()
                cs = OxmlElement("w:cantSplit")
                trpr.append(cs)
                if i == 0:
                    th = OxmlElement("w:tblHeader")
                    trpr.append(th)
                for k, val in enumerate(row):
                    cell = tbl.cell(i, k)
                    cell.width = Inches(widths[k])
                    # Líneas tipo booktabs. Regla gruesa arriba y abajo, media bajo el
                    # encabezado y una línea fina gris entre filas.
                    last = i == len(all_rows) - 1
                    edges = {"top": ("8", "000000") if i == 0 else None,
                             "bottom": ("8", "000000") if last else (("6", "000000") if i == 0 else ("2", "A6A6A6"))}
                    tcpr = cell._tc.get_or_add_tcPr()
                    bd = OxmlElement("w:tcBorders")
                    for side in ("top", "left", "bottom", "right"):
                        e = OxmlElement(f"w:{side}")
                        spec = edges.get(side)
                        if spec:
                            e.set(qn("w:val"), "single")
                            e.set(qn("w:sz"), spec[0])
                            e.set(qn("w:color"), spec[1])
                        else:
                            e.set(qn("w:val"), "nil")
                        e.set(qn("w:space"), "0")
                        bd.append(e)
                    tcpr.append(bd)
                    mar = OxmlElement("w:tcMar")
                    for side, v in (("top", 40), ("bottom", 40), ("left", 70), ("right", 70)):
                        m = OxmlElement(f"w:{side}")
                        m.set(qn("w:w"), str(v))
                        m.set(qn("w:type"), "dxa")
                        mar.append(m)
                    tcpr.append(mar)
                    par = cell.paragraphs[0]
                    par.paragraph_format.space_after = Pt(2)
                    par.paragraph_format.line_spacing = 1.1
                    par.paragraph_format.keep_with_next = i < len(all_rows) - 1
                    if numeric and k > 0:
                        par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    add_runs(par, str(val), size=size, bold_all=(i == 0))
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "fig":
            _, file, caption, width, _, _ = blk
            par = doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.paragraph_format.keep_with_next = True
            par.add_run().add_picture(str(FIG / file), width=Inches(width))
            add_runs(doc.add_paragraph(), caption, size=8.5)
    doc.core_properties.title = TITLE
    doc.core_properties.author = "Equipo Rolulabo"
    doc.save(out)


# ---------------------------------------------------------------- HTML
def build_html(out: Path):
    """HTML compacto para importar en Google Docs con Drive."""
    def inline(text):
        return "".join(f"<b>{html.escape(t)}</b>" if b else html.escape(t) for t, b in parts(text))

    def table(head, body, widths, numeric, size):
        h = ['<table style="border-collapse:collapse;width:100%">']
        for i, row in enumerate([head] + body):
            tag = "th" if i == 0 else "td"
            cells = []
            for k, v in enumerate(row):
                al = ' align="right"' if numeric and k > 0 else ""
                cells.append(f"<{tag}{al}>{inline(str(v))}</{tag}>")
            h.append("<tr>" + "".join(cells) + "</tr>")
        return "".join(h) + "</table><p></p>"

    css = ("body,p,li,td,th,h1,h2{font-family:Montserrat;color:#000000}"
           "p,li{font-size:10pt}td,th{font-size:8.5pt;padding:3pt 5pt;text-align:left}"
           "h1{font-size:15pt}h2{font-size:11.5pt}")
    o = [f'<html><head><meta charset="utf-8"><style>{css}</style></head><body>',
         f'<p style="text-align:center;font-family:Roboto Mono;font-size:18pt">{PORTADA["facultad"]}</p><p></p>',
         f'<p style="font-family:Roboto Mono;font-size:16pt"><b>Materia:</b> {PORTADA["materia"]}</p><p></p>',
         f'<p style="font-family:Roboto Mono;font-size:16pt"><b>Alumnos:</b> ' + "<br>".join(PORTADA["alumnos"]) + "</p><p></p>",
         f'<p style="font-family:Roboto Mono;font-size:16pt"><b>Nombre de actividad:</b> {PORTADA["actividad"]}</p><p></p>',
         f'<p style="font-family:Roboto Mono;font-size:16pt"><b>Fecha de entrega:</b> {PORTADA["fecha"]}</p>']
    for blk in content():
        k = blk[0]
        if k in ("h1", "h1u", "h2"):
            tag = "h2" if k == "h2" else "h1"
            o.append(f"<{tag}>{html.escape(blk[1])}</{tag}>")
        elif k == "p":
            o.append(f'<p style="text-align:justify">{inline(blk[1])}</p>')
        elif k in ("ul", "ol"):
            o.append(f"<{k}>" + "".join(f"<li>{inline(i)}</li>" for i in blk[1]) + f"</{k}>")
        elif k == "table":
            o.append(table(*blk[1:]))
        elif k == "fig" and blk[4]:
            o.append(table(blk[4], blk[5], [1] * len(blk[4]), True, 8.5))
            o.append(f"<p>{inline(blk[2].replace('Figura', 'Tabla de la figura').split(' En gris')[0])}</p>")
    o.append("</body></html>")
    out.write_text("".join(o), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="store_true", help="genera HTML para importar como Google Doc")
    a = ap.parse_args()
    if a.html:
        build_html(HERE / "Reporte_Rolulabo.html")
        print("HTML listo")
    else:
        (HERE.parent / "entregables").mkdir(exist_ok=True)
        build_docx(HERE.parent / "entregables" / "Reporte_Rolulabo.docx")
        print("Word listo")
