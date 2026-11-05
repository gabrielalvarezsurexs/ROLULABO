"""Regenera todos los entregables en entregables/ a partir de las métricas.

    python reports/build_entregables.py

Corre en orden las imágenes, el reporte y la presentación. Si LibreOffice
está instalado (comando soffice), también exporta ambos a PDF.
Requiere haber corrido antes python src/run_all.py.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "entregables"
PASOS = ["build_assets.py", "build_report.py", "build_presentation.py"]


def main():
    if not (ROOT / "reports" / "metrics" / "decision.json").exists():
        sys.exit("Faltan métricas. Corre primero python src/run_all.py")
    OUT.mkdir(exist_ok=True)
    for script in PASOS:
        print(f"> {script}")
        subprocess.run([sys.executable, str(HERE / script)], check=True, cwd=ROOT)

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("LibreOffice no está instalado, se omiten los PDF.")
        return
    for name in ["Reporte_Rolulabo.docx", "Presentacion_Rolulabo.pptx"]:
        print(f"> PDF de {name}")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(OUT / name)],
                       check=True, capture_output=True)
    print("Entregables listos en", OUT)


if __name__ == "__main__":
    main()
