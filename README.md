# Rolulabo

Proyecto integrador de Aprendizaje de Máquina (COM194), Facultad de Ingeniería, Universidad Panamericana.

**Equipo.** Gabriel Álvarez Mendoza, Eduardo Gutiérrez, Emiliano Luna y Rodrigo Naranjo Hernández (0250016).

BI con aprendizaje de máquina sobre Rolulabo, una cadena ficticia de artículos de oficina, muebles y tecnología. El proyecto sigue CRISP-DM en tres iteraciones ágiles y termina en una decisión de negocio que toma una persona, no el modelo. Se relaciona con el ODS 8, meta 8.2, productividad económica mediante modernización tecnológica, con una relación indirecta y a nivel empresa.

**Decisión recomendada.** Aplicar topes de descuento por subcategoría en los 10 estados de descuento alto, en dos olas que funcionan como experimento controlado. Con datos de 2017, la utilidad de esos estados pasa de -$36,671 a $44,770 y se captura el 91% del beneficio posible. La decisión final es de Dirección General.

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gabrielalvarezsurexs/rolulabo/blob/main/notebooks/rolulabo_analisis.ipynb)

## Entregables

| Entregable de la rúbrica | Archivo |
|---|---|
| Google Colab | [`notebooks/rolulabo_analisis.ipynb`](notebooks/rolulabo_analisis.ipynb), ejecutado y organizado con los puntos A a E de la rúbrica |
| Dataset | [`data/raw/superstore.csv`](data/raw/superstore.csv), fuente en Kaggle (ver Datos) |
| Reporte ejecutivo, 4 páginas | [`entregables/Reporte_Ejecutivo_Rolulabo.pdf`](entregables/Reporte_Ejecutivo_Rolulabo.pdf) y [`.docx`](entregables/Reporte_Ejecutivo_Rolulabo.docx) |
| Presentación ejecutiva | [`entregables/Presentacion_Rolulabo.pptx`](entregables/Presentacion_Rolulabo.pptx), con transiciones y animaciones, y [`.pdf`](entregables/Presentacion_Rolulabo.pdf) de respaldo |
| Declaración de herramientas | [`entregables/Declaracion_Herramientas_Rolulabo.pdf`](entregables/Declaracion_Herramientas_Rolulabo.pdf) y [`.docx`](entregables/Declaracion_Herramientas_Rolulabo.docx) |
| Anexo, reporte técnico | [`entregables/Reporte_Tecnico_Rolulabo.pdf`](entregables/Reporte_Tecnico_Rolulabo.pdf) y [`.docx`](entregables/Reporte_Tecnico_Rolulabo.docx) |
| Modelos entrenados | [`models/loss_model.joblib`](models/loss_model.joblib) y [`models/segmentation.joblib`](models/segmentation.joblib) |
| Dashboard | [`app/dashboard.py`](app/dashboard.py), Streamlit |

## Resultados clave

| Pregunta | Técnica | Resultado |
|---|---|---|
| Qué líneas van a perder dinero | Clasificación, cuatro modelos contra tres líneas base | Gradient boosting F1 0.889 contra 0.826 de la regla actual, intervalos de 95% sin traslape. Una regla con el costo histórico del producto llega a 0.995 sin ML, así que el modelo sirve donde no hay costo |
| Hasta qué descuento conviene cada subcategoría | Descuento de equilibrio y dependencia parcial del modelo | Tabla de topes, utilidad 2017 de $93K a $183K con volumen constante |
| Qué pedidos llegarán tarde | Chi-cuadrada con Bonferroni y clasificación por modalidad | No predecible (AUC 0.46 a 0.52), se ajusta la promesa |
| Qué grupos de clientes existen | K-Means sobre RFM, margen y descuento | 4 grupos, silueta 0.22 y ARI bootstrap 0.72. Cazadores de descuento generan 62% de las pérdidas |

De 8 hipótesis iniciales del negocio, 7 se refutaron con datos. Cada veredicto sale de un criterio fijado antes de ver el resultado. Ver [`reports/metrics/hypotheses.json`](reports/metrics/hypotheses.json).

## Score, regla y decisión humana

Ningún modelo decide solo.

| Paso | Qué es | Ejemplo en una línea de venta |
|---|---|---|
| Score | Lo que calcula el modelo | Probabilidad de pérdida |
| Regla | Política explícita y auditable | Semáforo rojo, amarillo o verde según tope y umbral |
| Decisión | La toma una persona con puesto | El gerente comercial ajusta, aprueba una excepción o rechaza, y queda en bitácora |

## Cómo correrlo

En Google Colab basta abrir el notebook con el botón de arriba y ejecutar todo. La primera celda clona este repositorio e instala la versión de scikit-learn fijada en `uv.lock`.

En una computadora las dependencias se manejan con [uv](https://docs.astral.sh/uv/). Las versiones exactas están en `uv.lock` y la versión de Python en `.python-version` (3.12). uv descarga esa versión de Python si no la tienes.

```bash
uv sync                                # crea .venv e instala todo, incluidas pytest y jupyter
uv run python src/run_all.py           # pipeline completo, unos 35 segundos
uv run pytest -q                       # 10 pruebas, incluida la de reproducibilidad
uv run streamlit run app/dashboard.py  # dashboard en http://localhost:8501
```

`src/run_all.py` genera `data/processed/`, que el dashboard necesita, y vuelve a entrenar los modelos con semilla fija.

Para regenerar los documentos desde las métricas:

```bash
uv run python reports/build_entregables.py     # imágenes, Word, PowerPoint y PDF (LibreOffice, o Word y PowerPoint en Windows)
uv run python reports/build_report.py --html   # opcional, HTML del reporte técnico para importar como Google Doc
```

Para agregar o quitar una dependencia se usa `uv add paquete` o `uv remove paquete`, nunca pip, para que `pyproject.toml` y `uv.lock` queden al día.

Los documentos usan Montserrat y Roboto Mono. Si no están instaladas, Word y PowerPoint las sustituyen.

## Reproducibilidad

Con las versiones de `uv.lock` el pipeline da siempre los mismos números, y la prueba `test_resultados_reproducibles` los compara contra [`tests/referencia.json`](tests/referencia.json). Dos detalles lo hacen posible.

- El umbral de decisión se elige en una rejilla de 0.05. El F1 es casi plano cerca del óptimo, así que el máximo exacto de la curva brincaba entre 0.37 y 0.45 con cambios mínimos de entorno sin que el F1 cambiara.
- Los CSV se leen con flotantes exactos (`config.read_csv`). pandas 2 y pandas 3 leían distinto el último dígito y eso cambiaba el modelo.

Con otra versión de scikit-learn el umbral puede moverse aunque las conclusiones no cambien. Si un cambio de código mueve los números a propósito, se regenera `tests/referencia.json` y los entregables.

## Estructura

```
rolulabo/
├── app/dashboard.py             Dashboard Streamlit, una pestaña por área
├── data/raw/superstore.csv      Datos originales, no se modifican
├── entregables/                 Reportes, presentación y declaración en Word, PowerPoint y PDF
├── models/                      Modelos entrenados
├── notebooks/                   Notebook ejecutado, listo para Google Colab
├── reports/
│   ├── build_entregables.py     Regenera todos los entregables
│   ├── build_executive.py       Reporte ejecutivo de 4 páginas
│   ├── build_report.py          Reporte técnico
│   ├── build_declaracion.py     Declaración de herramientas
│   ├── build_presentation.py    Presentación
│   ├── build_assets.py          Mapa de estados e imagen de portada
│   ├── pptx_motion.py           Transiciones y animaciones de la presentación
│   ├── assets/                  Logo, íconos (Lucide, ISC), ilustraciones (unDraw, MIT) e imágenes generadas
│   ├── figures/                 Gráficas del reporte
│   └── metrics/                 Métricas y tablas en JSON y CSV
├── src/
│   ├── config.py                Rutas, semilla, partición, supuestos de negocio y lectura exacta de CSV
│   ├── etl.py                   Extracción, validación, limpieza, atípicos, sesgos y modelo estrella
│   ├── hypotheses.py            Prueba de las 8 hipótesis y opciones de decisión
│   ├── loss_model.py            Modelo de pérdida, líneas base, errores, robustez, topes y simulación
│   ├── delivery.py              Análisis de entregas
│   ├── segmentation.py          Segmentación de clientes
│   ├── cross.py                 Lectura cruzada
│   ├── decision_rules.py        Score, regla y decisión humana
│   ├── viz.py                   Estilo de gráficas
│   └── run_all.py               Ejecuta todo en orden
├── tests/                       Pruebas de calidad, fuga, partición, hipótesis y reproducibilidad
└── .github/workflows/           Integración continua en cada push
```

## Metodología

CRISP-DM en tres iteraciones. Cada una cierra con un entregable que funciona y con la revisión de hipótesis.

1. Negocio y datos. ETL validado, atípicos y sesgos, EDA y prueba de hipótesis. La caída de H1 cambió el problema de capacitar vendedores a corregir una tabla de descuentos.
2. Modelos. Cuatro modelos con partición temporal (2014 a 2016 entrenamiento, 2017 prueba) contra la regla actual, la proporción de la clase y una regla con costo histórico. Análisis de errores y de sensibilidad del umbral. La caída de H5 replanteó la historia de Operaciones.
3. Decisión y despliegue. Simulación de política con sensibilidad al volumen, score y reglas, dashboard y decisión con criterios de éxito.

## Datos

Sample Superstore, versión completa con Discount, Quantity y Profit. https://www.kaggle.com/datasets/vivek468/superstore-dataset-final

## Uso de herramientas de IA

Se usó Claude (Anthropic) como asistente para estructurar el código, revisar la metodología, auditar el proyecto contra la rúbrica y redactar borradores. El equipo revisó, ejecutó y validó cada resultado. Las decisiones de planteamiento, alcance e interpretación son del equipo. El detalle de herramientas y verificaciones está en la [Declaración de herramientas](entregables/Declaracion_Herramientas_Rolulabo.pdf).

---

Elaborado por Gabriel Álvarez Mendoza, Eduardo Gutiérrez, Emiliano Luna y Rodrigo Naranjo Hernández
