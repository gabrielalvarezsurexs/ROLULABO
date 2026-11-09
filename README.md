# Rolulabo

Proyecto integrador de Aprendizaje de Máquina, Facultad de Ingeniería, Universidad Panamericana.

BI con aprendizaje de máquina sobre Rolulabo, una cadena ficticia de artículos de oficina, muebles y tecnología. El proyecto sigue CRISP-DM en tres iteraciones ágiles y termina en una decisión de negocio que toma una persona, no el modelo.

**Decisión recomendada.** Aplicar topes de descuento por subcategoría en los 10 estados de descuento alto, en dos olas que funcionan como experimento controlado. Con datos de 2017, la utilidad de esos estados pasa de -$36,671 a $44,770 y se captura el 91% del beneficio posible. La decisión final es de Dirección General.

## Entregables

| Entregable | Archivo |
|---|---|
| Reporte | [`entregables/Reporte_Rolulabo.pdf`](entregables/Reporte_Rolulabo.pdf) y [`.docx`](entregables/Reporte_Rolulabo.docx) |
| Presentación | [`entregables/Presentacion_Rolulabo.pptx`](entregables/Presentacion_Rolulabo.pptx), con transiciones y animaciones, y [`.pdf`](entregables/Presentacion_Rolulabo.pdf) de respaldo |
| Modelos entrenados | [`models/loss_model.joblib`](models/loss_model.joblib) y [`models/segmentation.joblib`](models/segmentation.joblib) |
| Dashboard | [`app/dashboard.py`](app/dashboard.py), Streamlit |
| Notebook de evidencia | [`notebooks/rolulabo_analisis.ipynb`](notebooks/rolulabo_analisis.ipynb), ya ejecutado |

## Resultados clave

| Pregunta | Técnica | Resultado |
|---|---|---|
| Qué líneas van a perder dinero | Clasificación, gradient boosting contra regla de negocio | F1 0.890 contra 0.826, intervalos de 95% sin traslape |
| Hasta qué descuento conviene cada subcategoría | Descuento de equilibrio y dependencia parcial del modelo | Tabla de topes, utilidad 2017 de $93K a $183K con volumen constante |
| Qué pedidos llegarán tarde | Chi-cuadrada con Bonferroni y clasificación por modalidad | No predecible (AUC 0.46 a 0.52), se ajusta la promesa |
| Qué grupos de clientes existen | K-Means sobre RFM, margen y descuento | 4 grupos estables, Cazadores de descuento generan 62% de las pérdidas |

De 8 hipótesis iniciales del negocio, 7 se refutaron con datos. Ver [`reports/metrics/hypotheses.json`](reports/metrics/hypotheses.json).

## Score, regla y decisión humana

Ningún modelo decide solo.

| Paso | Qué es | Ejemplo en una línea de venta |
|---|---|---|
| Score | Lo que calcula el modelo | Probabilidad de pérdida |
| Regla | Política explícita y auditable | Semáforo rojo, amarillo o verde según tope y umbral |
| Decisión | La toma una persona con puesto | El gerente comercial ajusta, aprueba una excepción o rechaza, y queda en bitácora |

## Cómo correrlo

Las dependencias se manejan con [uv](https://docs.astral.sh/uv/). Las versiones exactas están en `uv.lock` y la versión de Python en `.python-version` (3.12). uv descarga esa versión de Python si no la tienes.

```bash
uv sync                                # crea .venv e instala todo, incluidas pytest y jupyter
uv run python src/run_all.py           # pipeline completo, de 30 a 50 segundos
uv run pytest -q                       # pruebas
uv run streamlit run app/dashboard.py  # dashboard en http://localhost:8501
```

`src/run_all.py` genera `data/processed/`, que el dashboard necesita, y vuelve a entrenar los modelos con semilla fija.

Para regenerar el reporte y la presentación desde las métricas:

```bash
uv run python reports/build_entregables.py     # imágenes, Word, PowerPoint y PDF (LibreOffice, o Word y PowerPoint en Windows)
uv run python reports/build_report.py --html   # opcional, HTML para importar como Google Doc
```

Para agregar o quitar una dependencia se usa `uv add paquete` o `uv remove paquete`, nunca pip, para que `pyproject.toml` y `uv.lock` queden al día.

Los documentos usan Montserrat y Roboto Mono. Si no están instaladas, Word y PowerPoint las sustituyen.

Los modelos y métricas versionados salieron de una corrida en Linux. En Windows el gradient boosting puede salir ligeramente distinto por diferencias de punto flotante (F1 0.891 en vez de 0.890). Las conclusiones no cambian, pero los entregables citan la corrida de referencia.

## Estructura

```
rolulabo/
├── app/dashboard.py             Dashboard Streamlit, una pestaña por área
├── data/raw/superstore.csv      Datos originales, no se modifican
├── entregables/                 Reporte y presentación en Word, PowerPoint y PDF
├── models/                      Modelos entrenados
├── notebooks/                   Notebook de evidencia ejecutado
├── reports/
│   ├── build_entregables.py     Regenera todos los entregables
│   ├── build_report.py          Genera el reporte
│   ├── build_presentation.py    Genera la presentación
│   ├── build_assets.py          Genera el mapa de estados y la imagen de portada
│   ├── pptx_motion.py           Transiciones y animaciones de la presentación
│   ├── assets/                  Logo, íconos (Lucide, ISC), ilustraciones (unDraw, MIT) e imágenes generadas
│   ├── figures/                 Gráficas del reporte
│   └── metrics/                 Métricas y tablas en JSON y CSV
├── src/
│   ├── config.py                Rutas, semilla, partición y supuestos de negocio
│   ├── etl.py                   Extracción, validación, limpieza y modelo estrella
│   ├── hypotheses.py            Prueba de las 8 hipótesis y opciones de decisión
│   ├── loss_model.py            Modelo de pérdida, topes y simulación
│   ├── delivery.py              Análisis de entregas
│   ├── segmentation.py          Segmentación de clientes
│   ├── cross.py                 Lectura cruzada
│   ├── decision_rules.py        Score, regla y decisión humana
│   ├── viz.py                   Estilo de gráficas
│   └── run_all.py               Ejecuta todo en orden
├── tests/test_pipeline.py       Pruebas de calidad, fuga de información y reglas
└── .github/workflows/           Integración continua en cada push
```

## Metodología

CRISP-DM en tres iteraciones. Cada una cierra con un entregable que funciona y con la revisión de hipótesis.

1. Negocio y datos. ETL validado, EDA y prueba de hipótesis. La caída de H1 cambió el problema de capacitar vendedores a corregir una tabla de descuentos.
2. Modelos. Cuatro modelos con partición temporal (2014 a 2016 entrenamiento, 2017 prueba) contra la regla actual y una línea base. La caída de H5 replanteó la historia de Operaciones.
3. Decisión y despliegue. Simulación de política, score y reglas, dashboard y decisión con criterios de éxito.

## Datos

Sample Superstore, versión completa con Discount, Quantity y Profit. https://www.kaggle.com/datasets/vivek468/superstore-dataset-final

## Equipo

- Gabriel Álvarez Mendoza
- Eduardo Gutiérrez
- Emiliano Luna
- Rodrigo Naranjo

## Uso de herramientas de IA

Se usó Claude (Anthropic) como asistente para estructurar el código, revisar la metodología y redactar borradores. El equipo revisó, ejecutó y validó cada resultado. Las decisiones de planteamiento, alcance e interpretación son del equipo.

---

Elaborado por Gabriel Álvarez Mendoza
