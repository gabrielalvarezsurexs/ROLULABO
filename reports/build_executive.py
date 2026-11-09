"""Reporte ejecutivo de Rolulabo, portada más tres páginas.

    uv run python reports/build_executive.py

Sale entregables/Reporte_Ejecutivo_Rolulabo.docx con el mismo formato del
reporte técnico (portada de la Facultad, Montserrat, tablas tipo booktabs).
Cubre los puntos A a E de la rúbrica del proyecto integrador. Todas las cifras
se leen de reports/metrics.
"""
from build_report import (ATS, AUC_RANGE, AUTOR, CH, COST, CZ, DD, DEC, DEC_HIGH, DL, ERR, GB, H1, HERE, HY, HYP, L,
                          MOD, ODS_TEXT, P, Q, REAL_MARGIN, REP, RULE, RULES, S, SEGK, SIM, SIM_MARGIN, T, THR_SENS,
                          build_docx, f3, money, pct)


def mrow(name, label):
    m = MOD[name]
    return [label, f3(m["pr_auc"]), f3(m["f1"]), f3(m["precision"]), f3(m["recall"])]


def executive_content():
    sim0 = SIM["escenarios"][0]
    perd_sim = SIM["lineas_perdida_simulada"] / SIM["lineas_prueba"]
    cumple_p95 = min(r["cumplimiento"] for r in DL["sensibilidad_promesa"] if r["escenario"] == "p95")
    ic_m, ic_r = L["ic95_modelo_elegido"]["f1_ic95"], L["ic95_regla"]["f1_ic95"]
    atip = ATS["atipicos_iqr"]
    return [
        ("h1u", "Reporte ejecutivo"),
        H1("1. Problema, objetivo y valor de la decisión"),
        P(f"Rolulabo, una cadena ficticia de artículos de oficina, muebles y tecnología, vendió {money(Q['ventas_totales'])} entre 2014 y 2017 con un margen de {pct(Q['utilidad_total'] / Q['ventas_totales'])}. Sus ventas crecieron 52% pero el margen se estancó. El {pct(Q['lineas_con_perdida_pct'])} de las líneas de venta cerró con pérdida y esas líneas restaron {money(Q['monto_perdidas'])}. Las pérdidas se detectan hasta el cierre contable y la empresa trata igual a todos sus clientes. La solución beneficia a Comercial y Finanzas, que deciden los descuentos, a Operaciones, que define la promesa de entrega, a Marketing, que asigna presupuesto, y a Dirección, que aprueba la política."),
        P(f"**Objetivo medible.** En los estados tratados, bajar las líneas con pérdida de {pct(Q['lineas_con_perdida_pct'])} a menos de 5% y subir el margen neto de {pct(REAL_MARGIN)} a más de 20%, sin que los pedidos por cliente caigan más de 10% contra un grupo de control. En entregas, cumplir la promesa en más de 95% de los pedidos."),
        P(f"**ODS.** {ODS_TEXT}"),

        H1("2. Datos, procedencia y calidad"),
        P(f"Se usó Sample Superstore en su versión completa, publicada en Kaggle (kaggle.com/datasets/vivek468/superstore-dataset-final), incluida en el repositorio como data/raw/superstore.csv. Tiene {Q['filas_crudas']:,} líneas y 21 columnas, {Q['pedidos']:,} pedidos, {Q['clientes']} clientes y 49 estados de Estados Unidos. Las variables del modelo son descuento, subcategoría, categoría, región, segmento, modalidad de envío, cantidad, precio de lista en logaritmo y mes. El objetivo es si la línea pierde dinero. Se derivaron precio de lista, costo unitario y descuento de equilibrio, que solo se usan para fijar topes y simular, nunca como variables del modelo."),
        P(f"**Calidad.** {Q['nulos_totales']} valores faltantes, {Q['duplicados_exactos_eliminados']} duplicado eliminado, {Q['pedidos_inconsistentes']} pedidos inconsistentes y {Q['product_id_reutilizados']} Product ID usados para dos productos, por lo que la llave de producto es ID más nombre. El costo unitario es constante por producto, así que la pérdida es determinista. Una línea pierde cuando su descuento supera el de equilibrio."),
        P(f"**Atípicos y sesgos.** Con la regla de Tukey, {pct(atip['sales']['atipicos_pct'])} de las ventas por línea y {pct(atip['profit']['atipicos_pct'])} de las utilidades son atípicas. No se eliminan porque son ventas reales. Se manejan con el precio en logaritmo, modelos de árboles y el margen recortado en los percentiles 1 y 99 para segmentar. Hay sesgo de representatividad (West {pct(REP['region']['West'], 0)} de las líneas, South {pct(REP['region']['South'], 0)}, 2017 {pct(REP['anio']['2017'], 0)}), confusión entre estado y descuento porque el descuento es fijo por estado y subcategoría, y sesgo de selección porque solo existen ventas cerradas. Los datos son sintéticos."),

        H1("3. Metodología y modelos"),
        P(f"Se siguió CRISP-DM en tres iteraciones. Antes de modelar se probaron ocho creencias del negocio con criterios estadísticos fijados de antemano, y {HYP['refutadas']} se refutaron. Hay tres problemas. Clasificación de líneas con pérdida, clasificación de pedidos fuera de tiempo y agrupamiento de clientes. Se entrena con 2014 a 2016 y se prueba con 2017, para imitar el uso real sobre pedidos futuros. Hiperparámetros y umbral se eligen con validación cruzada temporal dentro de entrenamiento. La métrica principal es PR-AUC por el desbalance de {pct(L['particion']['perdida_pct_prueba'])} de positivos, con F1 e intervalos bootstrap de 95%. Para evitar fuga de información el modelo no usa utilidad, margen ni costo, y una prueba automática lo verifica."),
        P("Se compararon cuatro modelos de complejidad creciente contra tres líneas base. La regresión logística es lineal e interpretable, el árbol da reglas legibles, y random forest y gradient boosting capturan la interacción entre descuento y subcategoría. La regla actual del negocio es la línea base relevante y la regla con costo histórico de cada producto es la referencia de lo que se logra sin aprendizaje de máquina."),
        T(["Modelo, prueba 2017", "PR-AUC", "F1", "Precisión", "Recall"], [
            mrow("Regla descuento > 20%", "Regla actual, descuento mayor a 20%"),
            mrow("Regresion logistica", "Regresión logística"), mrow("Arbol de decision", "Árbol de decisión"),
            mrow("Random forest", "Random forest"), mrow(L["modelo_elegido"], f"**{L['modelo_elegido']}, elegido**"),
            mrow("Regla costo histórico", "Regla con costo histórico, sin ML")],
          [2.9, 0.85, 0.85, 0.95, 0.95], size=8.5),

        H1("4. Resultados, errores y robustez"),
        P(f"**Pérdidas.** El {L['modelo_elegido'].lower()} se eligió por PR-AUC de validación sin ver la prueba. En 2017 logra F1 de {f3(GB['f1'])} (intervalo {f3(ic_m[0])} a {f3(ic_m[1])}) contra {f3(RULE['f1'])} de la regla actual ({f3(ic_r[0])} a {f3(ic_r[1])}). Los intervalos no se traslapan. Aporta en la zona de 20% de descuento, donde la regla no ve nada y el modelo detecta {L['descuento_20']['modelo_detecta']} de {L['descuento_20']['perdidas']} pérdidas."),
        P(f"**Errores.** El modelo deja pasar {ERR['falsos_negativos']} pérdidas, el {pct(ERR['falsos_negativos_en_20_pct'], 0)} con 20% de descuento, que suman {pct(ERR['falsos_negativos_monto_pct'])} del monto perdido. Sus {ERR['falsos_positivos']} falsas alarmas tenían {money(ERR['falsos_positivos_utilidad'])} de utilidad. **Robustez.** El F1 queda entre {f3(THR_SENS['f1_min_umbral_mas_menos_010'])} y {f3(THR_SENS['f1_max_umbral_mas_menos_010'])} si el umbral se mueve 0.10. Los topes siguen dando {money(SIM['escenarios'][-1]['delta_utilidad'])} de utilidad extra aunque se pierda todo el volumen de las líneas afectadas. Una prueba automática confirma que los resultados se reproducen con las versiones fijas."),
        P(f"**Lo que el modelo no resuelve mejor.** La regla con costo histórico llega a F1 de {f3(COST['f1'])}, porque el {pct(CH['lineas_con_historial_pct'])} de las líneas de 2017 son de productos con historial y su pérdida es determinista. Si el sistema expone el costo, esa regla debe usarse. El modelo sirve cuando el costo no está disponible, como segundo método para fijar topes y para confirmar sin costo que la pérdida depende del descuento y la subcategoría."),
        P(f"**Entregas y clientes.** Ninguna de {len(DL['pruebas_chi2'])} pruebas chi-cuadrada es significativa con Bonferroni y los modelos por modalidad tienen AUC de {AUC_RANGE}. El retraso no se puede predecir, el ajuste es en la promesa. K-Means encontró cuatro grupos (silueta {SEGK[4]['silueta']:.2f}, índice de Rand ajustado {S['estabilidad']['ari_semillas_media']:.2f} entre semillas y {S['estabilidad']['ari_bootstrap_media']:.2f} en remuestreo). El grupo Cazadores de descuento genera el {pct(CZ['perdidas_pct'], 0)} de las pérdidas."),

        H1("5. Decisión y recomendaciones"),
        T(["Opción", "Utilidad 2017 simulada", "Riesgo"],
          [[("**" + o["opcion"] + "**") if o["opcion"].startswith("C") else o["opcion"], money(o["utilidad_2017"]), o["riesgo"]] for o in DEC["opciones"]],
          [2.9, 1.3, 2.3], numeric=False, size=8.5),
        P(f"**Recomendación, opción C.** Topes de descuento por subcategoría en los 10 estados de descuento alto, en dos olas de cinco estados que funcionan como experimento controlado. Captura el {pct(DEC_HIGH['delta_pct_del_total'], 0)} del beneficio posible y mide el efecto real en volumen antes de escalar. Ningún modelo decide solo. El semáforo manda a revisión humana el {pct(RULES['decisiones_humanas_pct'], 0)} de las líneas, donde está el {pct(RULES['perdida_cubierta_por_revision_pct'])} del monto perdido, y el gerente comercial decide y deja registro. Operaciones debe publicar la promesa al percentil 95 de cada modalidad y Marketing presupuestar con los cuatro grupos. La decisión final es de Dirección General."),

        H1("6. Conclusiones, limitaciones y confiabilidad"),
        P(f"El objetivo se cumple en simulación sobre 2017. Con topes, las líneas con pérdida bajan de {pct(Q['lineas_con_perdida_pct'])} a {pct(perd_sim)}, el margen sube de {pct(REAL_MARGIN)} a {pct(SIM_MARGIN)} con volumen constante, y con la promesa al percentil 95 el cumplimiento queda arriba de {pct(cumple_p95, 0)} en todas las modalidades. Falta confirmarlo con el piloto, porque el efecto en volumen no se puede observar en estos datos."),
        P("Las limitaciones son claras. Los datos son sintéticos y la utilidad sale de un costo fijo, por eso las métricas son altas. El método se traslada a una empresa real, el nivel de desempeño no. No se observa a quien no compró, la promesa de entrega es un supuesto y hay un solo país. Los resultados son confiables como evidencia de método, reproducibles y validados contra líneas base. La política se debe vigilar con reentrenamiento trimestral y alertas si las líneas con pérdida pasan de 5%."),
        P("**Herramientas.** Python, scikit-learn, uv y Claude de Anthropic como asistente. El detalle y las verificaciones están en la Declaración de herramientas."),
        P(f"**Elaborado por {AUTOR}**"),
    ]


if __name__ == "__main__":
    out = HERE.parent / "entregables" / "Reporte_Ejecutivo_Rolulabo.docx"
    out.parent.mkdir(exist_ok=True)
    build_docx(out, executive_content(), index=False, title="Rolulabo, reporte ejecutivo")
    print("Reporte ejecutivo listo", out)
