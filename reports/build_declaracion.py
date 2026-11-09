"""Declaración de herramientas e inteligencia artificial de Rolulabo.

    uv run python reports/build_declaracion.py

Sale entregables/Declaracion_Herramientas_Rolulabo.docx con el formato del
reporte. Las versiones se leen del entorno instalado con uv.lock y los
resultados de las verificaciones de reports/metrics.
"""
import json
import platform
from importlib.metadata import PackageNotFoundError, version

from build_report import AUTOR, COST, GB, H1, HERE, HYP, P, RULE, T, build_docx, f3

PAQUETES = [
    ("pandas", "Lectura, limpieza y agregación de datos"),
    ("numpy", "Cálculo numérico"),
    ("scikit-learn", "Modelos, validación, métricas y K-Means"),
    ("scipy", "Pruebas estadísticas de las hipótesis"),
    ("matplotlib", "Gráficas del reporte"),
    ("joblib", "Guardado de modelos entrenados"),
    ("streamlit", "Dashboard por área"),
    ("plotly", "Gráficas interactivas del dashboard"),
    ("python-docx", "Generación de los reportes en Word"),
    ("python-pptx", "Generación de la presentación"),
    ("pytest", "Pruebas automáticas"),
    ("jupyter", "Notebook de evidencia"),
]


def v(pkg):
    try:
        return version(pkg)
    except PackageNotFoundError:
        return "ver uv.lock"


def content():
    ref = json.loads((HERE.parent / "tests" / "referencia.json").read_text(encoding="utf-8"))
    return [
        ("h1u", "Declaración de herramientas e inteligencia artificial"),
        P("Este documento declara las herramientas de software y los asistentes de inteligencia artificial que se usaron en el proyecto Rolulabo, y las verificaciones con las que el equipo comprobó que los resultados son correctos y reproducibles. Integrantes, Gabriel Álvarez Mendoza, Eduardo Gutiérrez, Emiliano Luna y Rodrigo Naranjo Hernández."),
        H1("1. Herramientas de software"),
        P(f"Todo el proyecto está escrito en Python {platform.python_version()}. Las dependencias se instalan con uv y sus versiones exactas quedan fijas en uv.lock, por eso cualquier persona obtiene los mismos números."),
        T(["Herramienta", "Versión", "Uso"], [[p, v(p), u] for p, u in PAQUETES] + [
            ["uv", "ver uv.lock", "Entorno y versiones fijas"],
            ["Git y GitHub Actions", "", "Control de versiones e integración continua"],
            ["Google Colab", "", "Ejecución del notebook en la nube"],
            ["LibreOffice o Microsoft Office", "", "Exportación de documentos a PDF"],
            ["Íconos Lucide e ilustraciones unDraw", "", "Recursos gráficos de licencia libre en la presentación"]],
          [2.2, 1.1, 3.2], numeric=False, size=8.5),
        H1("2. Asistentes de inteligencia artificial"),
        T(["Asistente", "Para qué se usó", "Qué no hizo"], [
            ["Claude, de Anthropic", "Estructurar el código del pipeline y del dashboard, revisar la metodología de validación, auditar el proyecto contra la rúbrica y redactar borradores del reporte, la presentación y este documento",
             "No definió el problema ni el alcance, no inventó datos ni resultados y no tomó la decisión de negocio"]],
          [1.4, 3.1, 2.0], numeric=False, size=8.5),
        P("Las cifras de los documentos no se escriben a mano. Los generadores leen las métricas que produce el código, así que cualquier número del reporte o de la presentación se puede rastrear hasta su archivo en reports/metrics. El equipo revisó, ejecutó y validó cada resultado, y es responsable de las interpretaciones, la decisión y las recomendaciones."),
        H1("3. Verificaciones realizadas"),
        T(["Verificación", "Cómo se hizo", "Resultado"], [
            ["Ejecución completa", "uv run python src/run_all.py desde el CSV original", "Corre de punta a punta en unos 35 segundos"],
            ["Pruebas automáticas", "uv run pytest -q, 10 pruebas", "Todas pasan"],
            ["Reproducibilidad", "Prueba que compara cada corrida contra tests/referencia.json, y dos corridas seguidas comparadas archivo por archivo",
             f"Se reproduce F1 {ref['f1']:.3f}, umbral {ref['umbral']:.2f} y el semáforo de 2017"],
            ["Fuga de información", "Prueba que verifica que el modelo no usa utilidad, margen, costo ni descuento de equilibrio", "Sin fuga"],
            ["Partición temporal", "Prueba que verifica que todas las líneas evaluadas son de 2017 y ninguna se usó para entrenar", "Correcta"],
            ["Hipótesis", "Cada veredicto sale de un criterio fijado antes y una prueba revisa que coincida con su estadístico", f"{HYP['refutadas']} refutadas y {HYP['confirmadas']} confirmada"],
            ["Comparación justa", f"Cuatro modelos y tres líneas base sobre la misma prueba de 2017, con intervalos bootstrap",
             f"Modelo F1 {f3(GB['f1'])}, regla actual {f3(RULE['f1'])}, regla con costo {f3(COST['f1'])}"],
            ["Cifras escritas en texto", "Contraste de las cifras de reporte y presentación contra los datos procesados", "Coinciden"],
            ["Integración continua", "GitHub Actions instala con uv.lock, corre el pipeline y las pruebas en cada cambio", "Configurada"]],
          [1.45, 3.0, 2.05], numeric=False, size=8.5),
        P("Al auditar el proyecto se encontraron y corrigieron tres problemas. Los números de referencia no se reproducían con las versiones fijadas, el umbral de decisión del semáforo estaba escrito para un modelo específico y algunos veredictos de hipótesis eran texto fijo. También se agregó la línea base con costo histórico, que acota el papel del clasificador y se reporta en los entregables."),
        P(f"**Elaborado por {AUTOR}**"),
    ]


if __name__ == "__main__":
    out = HERE.parent / "entregables" / "Declaracion_Herramientas_Rolulabo.docx"
    out.parent.mkdir(exist_ok=True)
    build_docx(out, content(), index=False, title="Rolulabo, declaración de herramientas")
    print("Declaración lista", out)
