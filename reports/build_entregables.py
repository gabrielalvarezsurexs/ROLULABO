"""Regenera todos los entregables en entregables/ a partir de las métricas.

    uv run python reports/build_entregables.py

Corre en orden las imágenes, el reporte ejecutivo, el reporte técnico, la
declaración de herramientas y la presentación. Después exporta todo a PDF
con LibreOffice (comando soffice) o, en Windows, con Word y PowerPoint
instalados (requiere pywin32). Si no hay ninguno, omite los PDF.
Requiere haber corrido antes uv run python src/run_all.py.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "entregables"
PASOS = ["build_assets.py", "build_executive.py", "build_report.py", "build_declaracion.py", "build_presentation.py"]
DOCS = [OUT / "Reporte_Ejecutivo_Rolulabo.docx", OUT / "Reporte_Tecnico_Rolulabo.docx", OUT / "Declaracion_Herramientas_Rolulabo.docx"]
PPTX = OUT / "Presentacion_Rolulabo.pptx"


def pdf_libreoffice(soffice):
    for path in DOCS + [PPTX]:
        print(f"> PDF de {path.name} con LibreOffice")
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(path)],
                       check=True, capture_output=True)


def pdf_office():
    """Exporta con Word y PowerPoint por COM. Regresa False si no están disponibles."""
    try:
        import win32com.client
    except ImportError:
        return False
    try:
        word = win32com.client.DispatchEx("Word.Application")
    except Exception:
        return False
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        for path in DOCS:
            print(f"> PDF de {path.name} con Word")
            doc = word.Documents.Open(str(path), ReadOnly=True)
            doc.ExportAsFixedFormat(str(path.with_suffix(".pdf")), 17)  # 17 = PDF
            doc.Close(False)
    finally:
        word.Quit()

    ppt = win32com.client.DispatchEx("PowerPoint.Application")
    try:
        print(f"> PDF de {PPTX.name} con PowerPoint")
        pres = ppt.Presentations.Open(str(PPTX), ReadOnly=True, WithWindow=False)
        pres.SaveAs(str(PPTX.with_suffix(".pdf")), 32)  # 32 = PDF
        pres.Close()
    finally:
        ppt.Quit()
    return True


def main():
    if not (ROOT / "reports" / "metrics" / "decision.json").exists():
        sys.exit("Faltan métricas. Corre primero uv run python src/run_all.py")
    OUT.mkdir(exist_ok=True)
    for script in PASOS:
        print(f"> {script}")
        subprocess.run([sys.executable, str(HERE / script)], check=True, cwd=ROOT)

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        pdf_libreoffice(soffice)
    elif not (sys.platform == "win32" and pdf_office()):
        print("No hay LibreOffice ni Word/PowerPoint, se omiten los PDF.")
        return
    print("Entregables listos en", OUT)


if __name__ == "__main__":
    main()
