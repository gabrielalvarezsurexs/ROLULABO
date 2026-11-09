# CLAUDE.md

Guía para trabajar en este repo con Claude Code.

## Proyecto

Rolulabo es el proyecto integrador de Aprendizaje de Máquina (Facultad de Ingeniería, Universidad Panamericana, entrega semana del 9 de noviembre de 2026). BI con aprendizaje de máquina sobre el dataset Superstore (9,994 filas, 2014 a 2017, EE. UU.), presentado como una cadena ficticia llamada Rolulabo. Sigue CRISP-DM en tres iteraciones ágiles y termina en una decisión de negocio que toma una persona, no el modelo (score, regla y decisión humana).

Equipo: Gabriel Álvarez Mendoza (0261445), Eduardo Gutiérrez, Emiliano Luna y Rodrigo Naranjo.

## Cómo trabajar con Gabriel

- Responder en español casual mexicano, directo y conciso. Sin "nomás" ni modismos nacos. Nada de relleno.
- Programa principalmente en Python.
- Todo documento (reporte, presentación, dashboard, README) cierra con "Elaborado por Gabriel Álvarez Mendoza".

### Estilo de los entregables

- Letra Montserrat. Solo texto negro y negritas en el reporte.
- Sin em dashes. No abusar de dos puntos ni punto y coma.
- Que suene natural, no "gepetico". Lenguaje claro y concreto.
- Pocas gráficas y en escala de grises en el reporte. Tablas estilo booktabs (línea arriba, abajo del encabezado y al final).
- La presentación usa paleta amarillo #F5C400 y negro #111111, 16:9, imágenes literales (mapa, portada generada, ilustraciones unDraw) y no solo íconos.

## Comandos

```bash
python -m venv .venv
.venv\Scripts\activate                 # Windows
pip install -r requirements.txt

python src/run_all.py                  # pipeline completo, 7 pasos, 30 a 50 s
pytest -q                              # 8 pruebas, necesitan data/processed (correr run_all antes)
streamlit run app/dashboard.py         # http://localhost:8501
python reports/build_entregables.py    # imágenes, Word, PowerPoint y PDF
python reports/build_report.py --html  # opcional, HTML para importar como Google Doc
```

Los PDF salen con LibreOffice si existe `soffice`. Si no, en Windows se exportan con Word y PowerPoint por COM (pywin32). Las fuentes Montserrat y Roboto Mono deben estar instaladas, si no Word las sustituye y el mapa de `build_assets.py` sale con otra letra.

## Arquitectura

Flujo: `data/raw/superstore.csv` → `src/run_all.py` → `data/processed/`, `models/`, `reports/metrics/`, `reports/figures/` → `reports/build_*.py` → `entregables/`.

- `src/config.py` concentra rutas, `SEED=42`, `TEST_YEAR=2017`, `SLA_DAYS`, `DISCOUNT_GRID`, `CAP_PERCENTILE=0.10` y `K_RANGE`. Cualquier supuesto de negocio nuevo va aquí.
- `src/run_all.py` corre en orden etl, loss_model, delivery, segmentation, cross, hypotheses y decision_rules. Los módulos se importan como top-level (`import etl`), así que los scripts y las pruebas agregan `src/` al path.
- `src/etl.py` valida, limpia (quita 1 duplicado), crea features y el modelo estrella en `data/processed/bi/`.
- `src/loss_model.py` entrena el clasificador de pérdida (gradient boosting elegido), calcula topes por subcategoría y simula la política.
- `src/hypotheses.py` prueba H1 a H8 y arma las opciones A, B y C de la decisión.
- `src/decision_rules.py` define el semáforo (`semaforo()`) y `REGLAS_NEGOCIO`.
- Los generadores de entregables (`reports/build_report.py`, `build_presentation.py`) leen de `reports/metrics/`, nunca recalculan. Si cambia una métrica, se corre `build_entregables.py` y los textos se actualizan solos, salvo frases escritas a mano dentro de esos scripts (revisarlas con grep si cambian los números).
- `reports/pptx_motion.py` inyecta transiciones y animaciones en el XML del pptx después de que python-pptx lo genera.
- La portada del reporte se edita en el dict `PORTADA` de `reports/build_report.py`.

## Reglas que no se rompen

- **Sin fuga de información.** Las features del modelo (`FEATURES` en `loss_model.py`) excluyen profit, margen, costo y descuento de equilibrio. Hay prueba que lo verifica.
- **Partición temporal.** Entrenamiento 2014 a 2016, prueba 2017. No mezclar años.
- **El modelo no decide.** Toda salida de modelo pasa por score, regla y una persona con puesto.
- **Resultados de referencia.** Los modelos y métricas versionados salieron de una corrida en Linux. En Windows el gradient boosting sale ligeramente distinto por empates de punto flotante (umbral 0.45 en vez de 0.37, F1 0.891 en vez de 0.890). Reporte, presentación y notebook citan los números de referencia, así que no se deben commitear `models/`, `reports/metrics/` ni `reports/figures/` regenerados en Windows. Si se corre `run_all.py` en Windows, regresarlos con `git restore models reports/metrics reports/figures` antes de commitear o de regenerar entregables.
- `data/processed/` y `data/decisiones/` no se versionan.

## Números clave (referencia)

- Gradient boosting en 2017: F1 0.890, PR-AUC 0.967, umbral 0.37. Regla actual (descuento > 20%): F1 0.826.
- Topes de descuento: utilidad 2017 de $93,439 a $182,660 con volumen constante.
- Decisión recomendada (opción C): topes en 10 estados en dos olas, utilidad $174,880, 91% del beneficio posible.
- Semáforo 2017: 925 rojo, 13 amarillo, 2,374 verde. Revisión humana en 28% de las líneas, 99.3% del monto perdido.
- 7 de 8 hipótesis refutadas, H8 confirmada.

## Entregables

- `entregables/Reporte_Rolulabo.docx` y `.pdf` (A4, 20 páginas, portada con formato UP en Roboto Mono).
- `entregables/Presentacion_Rolulabo.pptx` (22 láminas con transiciones y animaciones) y `.pdf` de respaldo sin animaciones.
- `app/dashboard.py`, 7 pestañas, con bitácora de decisiones humanas en `data/decisiones/decisiones_log.csv`.
- `notebooks/rolulabo_analisis.ipynb`, ya ejecutado.

---

Elaborado por Gabriel Álvarez Mendoza
