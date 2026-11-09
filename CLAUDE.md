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

Paquetes y entorno con **uv**, nunca pip ni `python -m venv`. Dependencias en `pyproject.toml` (pytest y jupyter en el grupo `dev`), versiones fijas en `uv.lock`, Python 3.12 en `.python-version`. No hay `requirements.txt`.

```bash
uv sync                                       # crea o actualiza .venv
uv add paquete / uv remove paquete            # cambiar dependencias (actualiza pyproject y uv.lock)
uv run python src/run_all.py                  # pipeline completo, 7 pasos, unos 35 s
uv run pytest -q                              # 10 pruebas, necesitan data/processed (correr run_all antes)
uv run streamlit run app/dashboard.py         # http://localhost:8501
uv run python reports/build_entregables.py    # imágenes, Word, PowerPoint y PDF de los 4 documentos
uv run python reports/build_report.py --html  # opcional, HTML del reporte técnico para Google Doc
```

Para herramientas de un solo uso que no son del proyecto: `uv run --no-project --with paquete python script.py`. CI (`.github/workflows/pipeline.yml`) usa `uv sync --locked`, así que si cambia `pyproject.toml` hay que commitear también `uv.lock`.

Los PDF salen con LibreOffice si existe `soffice`. Si no, en Windows se exportan con Word y PowerPoint por COM (pywin32). Las fuentes Montserrat y Roboto Mono deben estar instaladas, si no Word las sustituye y el mapa de `build_assets.py` sale con otra letra.

## Arquitectura

Flujo: `data/raw/superstore.csv` → `src/run_all.py` → `data/processed/`, `models/`, `reports/metrics/`, `reports/figures/` → `reports/build_*.py` → `entregables/`.

- `src/config.py` concentra rutas, `SEED=42`, `TEST_YEAR=2017`, `SLA_DAYS`, `DISCOUNT_GRID`, `CAP_PERCENTILE=0.10` y `K_RANGE`. Cualquier supuesto de negocio nuevo va aquí. También tiene `read_csv`, que lee flotantes exactos y es la única forma de leer CSV en `src/`.
- `src/run_all.py` corre en orden etl, loss_model, delivery, segmentation, cross, hypotheses y decision_rules. Los módulos se importan como top-level (`import etl`), así que los scripts y las pruebas agregan `src/` al path.
- `src/etl.py` valida, limpia (quita 1 duplicado), crea features y el modelo estrella en `data/processed/bi/`.
- `src/loss_model.py` entrena el clasificador de pérdida (gradient boosting elegido), lo compara contra tres líneas base (proporción, regla de 20% y regla de costo histórico), calcula análisis de errores y sensibilidad del umbral, topes por subcategoría y simula la política. El umbral se elige en una rejilla de 0.05.
- `src/hypotheses.py` prueba H1 a H8 con un `criterio` explícito por hipótesis, el veredicto sale del estadístico, y arma las opciones A, B y C de la decisión.
- `src/decision_rules.py` define el semáforo (`semaforo()`) y `REGLAS_NEGOCIO`. Usa el umbral de `modelo_elegido`, nunca un nombre de modelo fijo.
- Los generadores de entregables (`build_executive.py`, `build_report.py`, `build_declaracion.py`, `build_presentation.py`) leen de `reports/metrics/`, nunca recalculan. El ejecutivo y la declaración reutilizan `build_docx` de `build_report.py`. Si cambia una métrica, se corre `build_entregables.py` y los textos se actualizan solos, salvo frases escritas a mano dentro de esos scripts (revisarlas con grep si cambian los números).
- `reports/pptx_motion.py` inyecta transiciones y animaciones en el XML del pptx después de que python-pptx lo genera.
- La portada del reporte se edita en el dict `PORTADA` de `reports/build_report.py`.

## Reglas que no se rompen

- **Sin fuga de información.** Las features del modelo (`FEATURES` en `loss_model.py`) excluyen profit, margen, costo y descuento de equilibrio. Hay prueba que lo verifica.
- **Partición temporal.** Entrenamiento 2014 a 2016, prueba 2017. No mezclar años.
- **El modelo no decide.** Toda salida de modelo pasa por score, regla y una persona con puesto.
- **Resultados de referencia.** Con las versiones de `uv.lock` el pipeline es determinista y `tests/test_resultados_reproducibles` lo compara contra `tests/referencia.json`. El umbral era frágil por dos causas que ya se corrigieron. El máximo exacto de F1 brincaba entre 0.37 y 0.45 (ahora se busca en rejilla de 0.05) y pandas 2 leía distinto el último dígito de los flotantes que pandas 3 (ahora todo pasa por `config.read_csv`). Solo scikit-learn mueve los números. Si un cambio mueve la referencia a propósito, se regenera `tests/referencia.json`, se corre `build_entregables.py`, se vuelve a ejecutar el notebook y se revisan con grep las frases escritas a mano.
- `data/processed/` y `data/decisiones/` no se versionan.

## Números clave (referencia)

- Gradient boosting en 2017: F1 0.889, PR-AUC 0.967, umbral 0.45. Regla actual (descuento > 20%): F1 0.826. Regla de costo histórico, sin ML: F1 0.995 (96.8% de las líneas de 2017 tienen historial).
- Topes de descuento: utilidad 2017 de $93,439 a $182,660 con volumen constante.
- Decisión recomendada (opción C): topes en 10 estados en dos olas, utilidad $174,880, 91% del beneficio posible.
- Semáforo 2017: 925 rojo, 4 amarillo, 2,383 verde. Revisión humana en 28% de las líneas, 99.3% del monto perdido.
- Errores del modelo: 78 falsos negativos (96% con 20% de descuento, 3.7% del monto perdido), 57 falsos positivos. F1 de 0.884 a 0.890 con umbral ±0.10.
- 7 de 8 hipótesis refutadas, H8 confirmada.

## Entregables

La rúbrica pide notebook en Colab, dataset, reporte ejecutivo de 2 a 4 páginas, presentación y declaración de herramientas, todos identificados con proyecto e integrantes.

- `entregables/Reporte_Ejecutivo_Rolulabo.docx` y `.pdf` (A4, portada UP más 3 páginas, no debe pasar de 4).
- `entregables/Reporte_Tecnico_Rolulabo.docx` y `.pdf` (anexo, A4, unas 22 páginas, portada con formato UP en Roboto Mono).
- `entregables/Declaracion_Herramientas_Rolulabo.docx` y `.pdf`.
- `entregables/Presentacion_Rolulabo.pptx` (25 láminas con transiciones y animaciones) y `.pdf` de respaldo sin animaciones.
- `app/dashboard.py`, 7 pestañas, con bitácora de decisiones humanas en `data/decisiones/decisiones_log.csv`.
- `notebooks/rolulabo_analisis.ipynb`, ejecutado, con secciones A a E de la rúbrica. En Colab la primera celda clona el repo e instala scikit-learn y scipy de `uv.lock`. Se reconstruye ejecutándolo con `uv run jupyter nbconvert --to notebook --execute --inplace notebooks/rolulabo_analisis.ipynb`.

---

Elaborado por Gabriel Álvarez Mendoza
