"""Ejecuta el pipeline completo de Rolulabo en orden.

    python src/run_all.py

Genera datos procesados, modelos, metricas y figuras desde el CSV crudo.
"""
import time

import cross
import decision_rules
import delivery
import etl
import hypotheses
import loss_model
import segmentation

STEPS = [
    ("1. ETL y calidad de datos", etl.run),
    ("2. Modelo de lineas con perdida y topes de descuento", loss_model.run),
    ("3. Analisis de entregas", delivery.run),
    ("4. Segmentacion de clientes", segmentation.run),
    ("5. Lectura cruzada", cross.run),
    ("6. Hipótesis iniciales y decisión", hypotheses.run),
    ("7. Score, regla y decisión humana", decision_rules.run),
]

if __name__ == "__main__":
    t0 = time.time()
    for name, fn in STEPS:
        t = time.time()
        print(f"\n{name}")
        fn()
        print(f"   listo en {time.time() - t:.1f} s")
    print(f"\nPipeline completo en {time.time() - t0:.1f} s. Resultados en reports/ y models/.")
