"""Score, regla y decisión humana.

El modelo no decide. Cada salida analítica sigue tres pasos.

    Score     lo que calcula el modelo (probabilidad de pérdida, grupo del cliente)
    Regla     una política explícita y auditable que convierte el score en una
              recomendación (semáforo)
    Decisión  la toma una persona con nombre de puesto, que puede aceptar,
              ajustar o rechazar la recomendación y deja registro

Este módulo aplica las reglas a las líneas de 2017 y mide cuántas decisiones
humanas genera cada semáforo, para dimensionar la carga de trabajo del área.

Salida. reports/metrics/decision_rules.json
"""
import json

import pandas as pd

from config import METRICS
from config import read_csv


# Reglas del semáforo para una línea de venta. Se usan igual en el dashboard.
def semaforo(discount: float, score: float, tope: float, umbral: float) -> dict:
    if discount > tope + 1e-9:
        return {"semaforo": "Rojo", "recomendacion": f"Ajustar el descuento al tope de {tope:.0%}",
                "decide": "Gerente comercial", "opciones": ["Ajustar al tope", "Aprobar excepción con justificación", "Rechazar la venta"]}
    if score >= umbral:
        return {"semaforo": "Amarillo", "recomendacion": "Revisar el margen del producto antes de cerrar",
                "decide": "Gerente comercial", "opciones": ["Aprobar", "Reducir descuento", "Rechazar la venta"]}
    return {"semaforo": "Verde", "recomendacion": "Sin alerta, proceso normal",
            "decide": "Vendedor", "opciones": ["Cerrar la venta"]}


REGLAS_NEGOCIO = [
    {"nivel": "Línea de venta", "score": "Probabilidad de pérdida del modelo",
     "regla": "Rojo si el descuento supera el tope de la subcategoría. Amarillo si está dentro del tope pero el score supera el umbral. Verde en otro caso",
     "decide": "Gerente comercial en rojo y amarillo, vendedor en verde"},
    {"nivel": "Política de descuento", "score": "Utilidad simulada por subcategoría y estado",
     "regla": "Tope igual al menor entre el percentil 10 del descuento de equilibrio y el tope del modelo",
     "decide": "Director de finanzas aprueba la tabla"},
    {"nivel": "Promesa de entrega", "score": "Percentil 95 de días por modalidad",
     "regla": "La promesa publicada es el percentil 95 redondeado hacia arriba",
     "decide": "Gerente de operaciones"},
    {"nivel": "Cliente", "score": "Grupo asignado por K-Means",
     "regla": "Acción sugerida por grupo (proteger, corregir, crecer, reactivar)",
     "decide": "Gerente de marketing asigna presupuesto"},
    {"nivel": "Estrategia", "score": "Resultados de la ola 1 contra el grupo de control",
     "regla": "Extender si se cumplen los criterios de éxito, revisar si se activa el criterio de alto",
     "decide": "Dirección general"},
]


def run() -> dict:
    loss = json.loads((METRICS / "loss_model.json").read_text(encoding="utf-8"))
    # El umbral es el del modelo elegido por validacion, el mismo que genero
    # los scores de prueba_2017_scores.csv.
    umbral = loss["modelos"][loss["modelo_elegido"]]["umbral"]
    caps = read_csv(METRICS / "topes_descuento.csv").set_index("sub_category")["tope_recomendado"]
    t = read_csv(METRICS / "prueba_2017_scores.csv")
    t["tope"] = t["sub_category"].map(caps)
    t["semaforo"] = [semaforo(d, s, c, umbral)["semaforo"] for d, s, c in zip(t["discount"], t["p_loss"], t["tope"])]
    perd = -t["profit"].where(t["profit"] < 0, 0)

    rows = []
    for sem in ["Rojo", "Amarillo", "Verde"]:
        m = t["semaforo"] == sem
        rows.append({
            "semaforo": sem,
            "lineas": int(m.sum()),
            "lineas_pct": float(m.mean()),
            "lineas_por_mes": float(m.sum() / 12),
            "lineas_con_perdida": int(t.loc[m, "is_loss"].sum()),
            "tasa_perdida": float(t.loc[m, "is_loss"].mean()) if m.any() else 0.0,
            "monto_perdida": float(perd[m].sum()),
            "monto_perdida_pct": float(perd[m].sum() / perd.sum()),
        })
    revisar = t["semaforo"] != "Verde"
    out = {
        "umbral_score": umbral,
        "semaforo_2017": rows,
        "decisiones_humanas_por_mes": float(revisar.sum() / 12),
        "decisiones_humanas_pct": float(revisar.mean()),
        "perdida_cubierta_por_revision_pct": float(perd[revisar].sum() / perd.sum()),
        "reglas": REGLAS_NEGOCIO,
    }
    (METRICS / "decision_rules.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    r = run()
    for x in r["semaforo_2017"]:
        print(x)
    print("decisiones humanas por mes", round(r["decisiones_humanas_por_mes"], 1), "pct", r["decisiones_humanas_pct"],
          "pérdida cubierta", r["perdida_cubierta_por_revision_pct"])
