# -*- coding: utf-8 -*-
"""
Script de empaquetado de la Entrega 4 — Introducción a la Visión Artificial.

Arma el archivo .zip con todos los entregables exigidos por la guía:
  - Informe_Entrega4.pdf
  - entrega4_vision_artificial.ipynb (verificando que tenga salidas visibles)
  - scraping_y_curacion.py (y config.py, generar_informe.py, requirements.txt)
  - dataset/dataset_origen.csv
  - resultados/caracteristicas.csv (y metricas.json / curacion_log.json)
  - dataset/<CLASE_0>/ y dataset/<CLASE_1>/

Además verifica el tamaño final en MB:
  - Si supera los 20 MB (límite del correo institucional), emite un aviso claro
    para subir la carpeta dataset/ a OneDrive con permiso para la docente y
    crea automáticamente un segundo .zip liviano listo para adjuntar al correo.

Uso:
    python empaquetar_entrega.py
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import List, Tuple

import config

LIMITE_CORREO_MB = 20.0
ZIP_COMPLETO = config.BASE_DIR / "Entrega4_VisionArtificial.zip"
ZIP_SIN_IMAGENES = config.BASE_DIR / "Entrega4_ParaCorreo_SinImagenes.zip"


def verificar_notebook_ejecutado(nb_path: Path) -> bool:
    """Verifica si el notebook tiene celdas de código ejecutadas con salidas visibles."""
    if not nb_path.exists():
        return False
    try:
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
        code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
        con_salida = [c for c in code_cells if c.get("execution_count") is not None]
        return len(code_cells) > 0 and len(con_salida) == len(code_cells)
    except (OSError, ValueError):
        return False


def agregar_archivo_si_existe(zf: zipfile.ZipFile, ruta: Path, faltantes: List[str]) -> None:
    if ruta.exists() and ruta.is_file():
        zf.write(ruta, arcname=ruta.relative_to(config.BASE_DIR))
    else:
        faltantes.append(str(ruta.relative_to(config.BASE_DIR)))


def empaquetar(destino_zip: Path, incluir_imagenes_dataset: bool) -> Tuple[int, float, List[str]]:
    faltantes: List[str] = []
    archivos_principales = [
        config.INFORME_PDF,
        config.NOTEBOOK_PATH,
        config.BASE_DIR / "scraping_y_curacion.py",
        config.BASE_DIR / "config.py",
        config.BASE_DIR / "generar_informe.py",
        config.BASE_DIR / "requirements.txt",
        config.DATASET_CSV,
        config.CARACTERISTICAS_CSV,
    ]
    archivos_opcionales = [
        config.METRICAS_JSON,
        config.CURACION_LOG_JSON,
    ]

    total_archivos = 0
    with zipfile.ZipFile(destino_zip, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for ruta in archivos_principales:
            antes = len(faltantes)
            agregar_archivo_si_existe(zf, ruta, faltantes)
            if len(faltantes) == antes:
                total_archivos += 1

        for ruta in archivos_opcionales:
            if ruta.exists() and ruta.is_file():
                zf.write(ruta, arcname=ruta.relative_to(config.BASE_DIR))
                total_archivos += 1

        if incluir_imagenes_dataset:
            for clase in config.CLASES:
                carpeta = config.DATASET_DIR / clase
                if not carpeta.exists():
                    faltantes.append(f"dataset/{clase}/")
                    continue
                imgs = sorted(p for p in carpeta.iterdir() if p.is_file())
                if not imgs:
                    faltantes.append(f"dataset/{clase}/ (vacía)")
                for img in imgs:
                    zf.write(img, arcname=img.relative_to(config.BASE_DIR))
                    total_archivos += 1

    size_mb = destino_zip.stat().st_size / (1024 * 1024)
    return total_archivos, size_mb, faltantes


def main() -> None:
    print("=" * 74)
    print("EMPAQUETADO DE ENTREGA 4 — INTRODUCCIÓN A LA VISIÓN ARTIFICIAL")
    print("=" * 74)

    if not verificar_notebook_ejecutado(config.NOTEBOOK_PATH):
        print(
            "[ADVERTENCIA] El notebook 'entrega4_vision_artificial.ipynb' no parece estar "
            "ejecutado completamente con salidas visibles.\n"
            "  Ejecútelo antes de enviar con:\n"
            "  jupyter nbconvert --to notebook --execute --inplace entrega4_vision_artificial.ipynb\n"
        )

    n_files, size_mb, faltantes = empaquetar(ZIP_COMPLETO, incluir_imagenes_dataset=True)
    print(f"ZIP completo creado : {ZIP_COMPLETO.name}")
    print(f"Archivos incluidos  : {n_files}")
    print(f"Tamaño total        : {size_mb:.2f} MB")

    if faltantes:
        print("\n[AVISO] Faltaron los siguientes elementos esperados:")
        for item in faltantes:
            print(f"  - {item}")

    print("-" * 74)
    if size_mb > LIMITE_CORREO_MB:
        print(
            f"[ATENCIÓN] El archivo completo supera los {LIMITE_CORREO_MB:.0f} MB "
            f"({size_mb:.2f} MB).\n"
            f"Según la Sección 10 de la guía:\n"
            f"  1. Suba la carpeta 'dataset/' (o {ZIP_COMPLETO.name}) a OneDrive con "
            f"permiso de lectura para {config.CORREO_DOCENTE}.\n"
            f"  2. Pegue el enlace de OneDrive en el cuerpo del correo.\n"
            f"  3. Adjunte el archivo liviano que se generará a continuación:"
        )
        n_lite, mb_lite, _ = empaquetar(ZIP_SIN_IMAGENES, incluir_imagenes_dataset=False)
        print(f"  -> ZIP liviano para correo: {ZIP_SIN_IMAGENES.name} ({mb_lite:.2f} MB, {n_lite} archivos)")
    else:
        print(
            f"[OK] El archivo completo ({size_mb:.2f} MB) NO supera los {LIMITE_CORREO_MB:.0f} MB. "
            f"Puede adjuntarlo directamente al correo dirigido a {config.CORREO_DOCENTE}."
        )
    print("=" * 74)


if __name__ == "__main__":
    main()
