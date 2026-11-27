# -*- coding: utf-8 -*-
"""
Script de Web Scraping Ético y Curación Automática — Entrega 4.
Asignatura: Introducción a la Visión Artificial (Grupo 190202024-4)

Funcionalidades:
1. Verificación automática de robots.txt antes de cualquier descarga.
2. Descarga ética desde la API pública de Wikimedia Commons (sin API Key,
   con User-Agent descriptivo y pausas de >= 0.5 s entre peticiones) y
   respaldo opcional desde Openverse si se requieren más candidatos.
3. Curación automática documentada:
   - Archivos corruptos o ilegibles
   - Resolución mínima (< 150x150 px)
   - Imágenes no RGB / escala de grises inválidas o en blanco
   - Duplicados exactos (SHA-256) y casi-duplicados (dHash 64-bit con PIL/NumPy)
4. Organización en dataset/<clase>/ y generación de dataset/dataset_origen.csv
   y resultados/curacion_log.json.

Uso:
    python scraping_y_curacion.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import robotparser

import cv2
import numpy as np
import requests
from PIL import Image, ImageOps, UnidentifiedImageError

import config

# ==============================================================================
# CONSTANTES DE FUENTES PÚBLICAS
# ==============================================================================
WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_ROBOTS_URL = "https://commons.wikimedia.org/robots.txt"
WIKIMEDIA_UPLOAD_ROBOTS_URL = "https://upload.wikimedia.org/robots.txt"

OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
OPENVERSE_ROBOTS_URL = "https://api.openverse.org/robots.txt"

MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
HTTP_TIMEOUT = 20


# ==============================================================================
# 1. VERIFICACIÓN DE ROBOTS.TXT Y SESIÓN HTTP ÉTICA
# ==============================================================================
def crear_sesion_http() -> requests.Session:
    """Crea una sesión HTTP con User-Agent descriptivo."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json, image/*;q=0.9, */*;q=0.8",
        }
    )
    return session


def verificar_robots_txt(
    session: requests.Session,
    robots_url: str,
    target_url: str,
    user_agent: str,
) -> Dict[str, Any]:
    """Consulta robots.txt y verifica si target_url está permitido para user_agent."""
    resultado: Dict[str, Any] = {
        "robots_url": robots_url,
        "target_url": target_url,
        "http_status": None,
        "permitido": False,
        "crawl_delay": None,
        "nota": "",
    }
    try:
        resp = session.get(robots_url, timeout=HTTP_TIMEOUT)
        resultado["http_status"] = resp.status_code
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)

        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            resultado["permitido"] = bool(rp.can_fetch(user_agent, target_url))
            resultado["crawl_delay"] = rp.crawl_delay(user_agent)
            resultado["nota"] = "robots.txt consultado y validado correctamente."
        elif resp.status_code == 404:
            resultado["permitido"] = True
            resultado["nota"] = "robots.txt no encontrado (404); acceso permitido por estándar RFC 9309."
        else:
            resultado["permitido"] = False
            resultado["nota"] = f"Respuesta HTTP inesperada ({resp.status_code}); se bloquea por precaución."
    except requests.RequestException as exc:
        resultado["permitido"] = False
        resultado["nota"] = f"Error de conexión consultando robots.txt: {exc}"

    return resultado


# ==============================================================================
# 2. UTILIDADES DE HASHING PERCEPTUAL (dHash) Y CURACIÓN DE IMÁGENES
# ==============================================================================
def calcular_sha256(data: bytes) -> str:
    """Calcula el hash SHA-256 para detección de duplicados exactos."""
    return hashlib.sha256(data).hexdigest()


def calcular_dhash(pil_img: Image.Image, hash_size: int = 8) -> np.ndarray:
    """
    Calcula el Difference Hash (dHash) de 64 bits usando PIL y NumPy.
    Redimensiona a (hash_size + 1, hash_size) en escala de grises y compara
    píxeles adyacentes horizontales. Robusto a cambios leves de escala o compresión.
    """
    gris = pil_img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    arr = np.asarray(gris, dtype=np.int16)
    diff = arr[:, 1:] > arr[:, :-1]
    return diff.flatten()


def distancia_hamming(hash_a: np.ndarray, hash_b: np.ndarray) -> int:
    """Distancia de Hamming entre dos vectores booleanos dHash."""
    return int(np.count_nonzero(hash_a != hash_b))


def es_casi_duplicado(
    dhash: np.ndarray,
    dhashes_existentes: List[np.ndarray],
    umbral: int = config.DHASH_DISTANCIA_MAX,
) -> bool:
    """Verifica si dhash está a distancia de Hamming <= umbral de algún hash ya visto."""
    for h in dhashes_existentes:
        if distancia_hamming(dhash, h) <= umbral:
            return True
    return False


def validar_y_normalizar_imagen(
    raw_bytes: bytes,
    min_res: int = config.MIN_RESOLUCION_PX,
) -> Tuple[Optional[Image.Image], Optional[str]]:
    """
    Valida una imagen en memoria y la normaliza a RGB si es válida.

    Retorna:
        (imagen_rgb_pil, None) si es válida.
        (None, motivo) si debe descartarse, donde motivo es uno de:
            - "corrupta"
            - "resolucion"
            - "no_rgb_gris"
    """
    try:
        # 1. Verificación estructural con PIL
        with Image.open(io.BytesIO(raw_bytes)) as img_verify:
            img_verify.verify()

        with Image.open(io.BytesIO(raw_bytes)) as img_loaded:
            img = ImageOps.exif_transpose(img_loaded)
            img.load()
            modo_original = img.mode
            ancho, alto = img.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        return None, "corrupta"

    # 2. Verificación de resolución mínima
    if ancho < min_res or alto < min_res:
        return None, "resolucion"

    # 3. Verificación de modo de color válido (rechazar escala de grises o modos inválidos)
    if modo_original in {"1", "L", "LA", "I", "F", "I;16", "P"}:
        # Las imágenes en paleta ('P') pueden tener transparencia/color o ser grises;
        # solo rechazamos si al convertir a RGB resultan monocromáticas.
        if modo_original != "P":
            return None, "no_rgb_gris"

    try:
        if img.mode == "RGBA":
            fondo = Image.new("RGB", img.size, (255, 255, 255))
            fondo.paste(img, mask=img.split()[3])
            img_rgb = fondo
        elif img.mode in {"RGB", "CMYK", "YCbCr", "P"}:
            img_rgb = img.convert("RGB")
        else:
            return None, "no_rgb_gris"
    except Exception:
        return None, "no_rgb_gris"

    arr_rgb = np.asarray(img_rgb, dtype=np.uint8)
    if arr_rgb.ndim != 3 or arr_rgb.shape[2] != 3:
        return None, "no_rgb_gris"

    # Rechazar imágenes falsamente RGB (canales idénticos = escala de grises) o casi vacías
    diff_rg = np.abs(arr_rgb[:, :, 0].astype(np.int16) - arr_rgb[:, :, 1].astype(np.int16))
    diff_rb = np.abs(arr_rgb[:, :, 0].astype(np.int16) - arr_rgb[:, :, 2].astype(np.int16))
    if float(np.max(diff_rg)) < 3.0 and float(np.max(diff_rb)) < 3.0:
        return None, "no_rgb_gris"

    if float(np.std(arr_rgb)) < 3.0:
        return None, "no_rgb_gris"

    # 4. Validación cruzada con OpenCV para garantizar lectura limpia en el notebook
    arr_bgr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
    ok_enc, buf = cv2.imencode(".jpg", arr_bgr)
    if not ok_enc or buf is None:
        return None, "corrupta"

    return img_rgb, None


def guardar_imagen_rgb_jpeg(img_rgb: Image.Image, destino: Path, max_lado: int = 1024) -> None:
    """
    Guarda la imagen validada en formato JPEG RGB de alta calidad.
    Si una imagen excede max_lado px, se escala proporcionalmente para mantener
    un tamaño de dataset manejable sin perder detalle (el pipeline usa 256x256).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    copia = img_rgb.copy()
    if max(copia.size) > max_lado:
        copia.thumbnail((max_lado, max_lado), Image.Resampling.LANCZOS)
    copia.save(destino, format="JPEG", quality=92, optimize=True)


# ==============================================================================
# 3. CLIENTES DE SCRAPING (WIKIMEDIA COMMONS + RESPALDO OPENVERSE)
# ==============================================================================
def buscar_en_wikimedia_commons(
    session: requests.Session,
    terminos: List[str],
    objetivo_candidatos: int,
    pausa: float = config.SLEEP_ENTRE_PETICIONES,
) -> List[Dict[str, str]]:
    """
    Consulta la API pública de Wikimedia Commons (sin API Key) usando varios
    términos de búsqueda y paginación hasta recolectar objetivo_candidatos URLs únicas.
    """
    candidatos: List[Dict[str, str]] = []
    urls_vistas: set[str] = set()

    for termino in terminos:
        if len(candidatos) >= objetivo_candidatos:
            break

        gsroffset = 0
        paginas_consultadas = 0
        max_paginas_por_termino = 8

        while len(candidatos) < objetivo_candidatos and paginas_consultadas < max_paginas_por_termino:
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6,  # Espacio de nombres File:
                "gsrsearch": f"{termino} filetype:bitmap",
                "gsrlimit": 50,
                "gsroffset": gsroffset,
                "prop": "imageinfo",
                "iiprop": "url|mime|size",
                "iiurlwidth": 800,
            }
            time.sleep(pausa)
            try:
                resp = session.get(WIKIMEDIA_API_URL, params=params, timeout=HTTP_TIMEOUT)
                if resp.status_code == 429:
                    print("  [Aviso] Wikimedia respondió HTTP 429; esperando 3 s antes de continuar...")
                    time.sleep(3.0)
                    continue
                resp.raise_for_status()
                payload = resp.json()
            except (requests.RequestException, ValueError) as exc:
                print(f"  [Aviso] Error consultando Wikimedia Commons ('{termino}'): {exc}")
                break

            pages = payload.get("query", {}).get("pages", {})
            if not pages:
                break

            for page in pages.values():
                info_list = page.get("imageinfo")
                if not info_list:
                    continue
                info = info_list[0]
                mime = str(info.get("mime", "")).lower()
                if mime not in MIME_PERMITIDOS:
                    continue

                width = int(info.get("width") or 0)
                height = int(info.get("height") or 0)
                if width < config.MIN_RESOLUCION_PX or height < config.MIN_RESOLUCION_PX:
                    continue

                url_origen = str(info.get("url") or "").strip()
                url_descarga = str(info.get("thumburl") or url_origen).strip()
                if not url_origen or url_origen in urls_vistas:
                    continue

                urls_vistas.add(url_origen)
                candidatos.append(
                    {
                        "fuente": "Wikimedia Commons",
                        "termino": termino,
                        "url_origen": url_origen,
                        "url_descarga": url_descarga,
                        "titulo": str(page.get("title", "")),
                    }
                )
                if len(candidatos) >= objetivo_candidatos:
                    break

            cont = payload.get("continue", {})
            if "gsroffset" not in cont:
                break
            gsroffset = int(cont["gsroffset"])
            paginas_consultadas += 1

    return candidatos


def buscar_en_openverse(
    session: requests.Session,
    terminos: List[str],
    objetivo_extra: int,
    urls_existentes: set[str],
    pausa: float = config.SLEEP_ENTRE_PETICIONES,
) -> List[Dict[str, str]]:
    """
    Fuente pública de respaldo (Openverse API, licencias abiertas, sin API Key
    para búsquedas anónimas con tasa limitada) usada solo si Wikimedia Commons
    no aporta suficientes candidatos.
    """
    candidatos: List[Dict[str, str]] = []
    for termino in terminos:
        if len(candidatos) >= objetivo_extra:
            break
        for page_num in range(1, 5):
            if len(candidatos) >= objetivo_extra:
                break
            time.sleep(max(pausa, 0.8))
            try:
                resp = session.get(
                    OPENVERSE_API_URL,
                    params={"q": termino, "page_size": 20, "page": page_num},
                    timeout=HTTP_TIMEOUT,
                )
                if resp.status_code == 429:
                    time.sleep(3.0)
                    break
                if resp.status_code != 200:
                    break
                data = resp.json()
            except (requests.RequestException, ValueError):
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                url = str(item.get("url") or "").strip()
                if not url or url in urls_existentes:
                    continue
                urls_existentes.add(url)
                candidatos.append(
                    {
                        "fuente": "Openverse",
                        "termino": termino,
                        "url_origen": url,
                        "url_descarga": url,
                        "titulo": str(item.get("title") or ""),
                    }
                )
                if len(candidatos) >= objetivo_extra:
                    break
    return candidatos


# ==============================================================================
# 4. PROCESAMIENTO DE FOTOS PROPIAS Y DESCARGA + CURACIÓN POR CLASE
# ==============================================================================
def procesar_fotos_propias(
    clase: str,
    carpeta_destino: Path,
    sha256_vistos: set[str],
    dhashes_vistos: List[np.ndarray],
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """Valida, orienta (EXIF) y copia las fotos propias de una clase al dataset."""
    carpeta_propias = config.FOTOS_PROPIAS_DIR / clase
    registros: List[Dict[str, str]] = []
    stats = {
        "propias_encontradas": 0,
        "propias_validas": 0,
        "propias_eliminadas_corruptas": 0,
        "propias_eliminadas_resolucion": 0,
        "propias_eliminadas_no_rgb_gris": 0,
        "propias_eliminadas_duplicados": 0,
    }

    if not carpeta_propias.exists():
        print(f"  [Aviso] No existe la carpeta de fotos propias: {carpeta_propias}")
        return registros, stats

    archivos = sorted(
        [
            p
            for p in carpeta_propias.iterdir()
            if p.is_file() and p.suffix.lower() in config.EXTENSIONES_VALIDAS
        ]
    )
    stats["propias_encontradas"] = len(archivos)

    idx = 1
    for archivo in archivos:
        try:
            raw_bytes = archivo.read_bytes()
        except OSError:
            stats["propias_eliminadas_corruptas"] += 1
            continue

        img_rgb, motivo = validar_y_normalizar_imagen(raw_bytes)
        if motivo is not None or img_rgb is None:
            stats[f"propias_eliminadas_{motivo}"] += 1
            continue

        sha = calcular_sha256(raw_bytes)
        dhash = calcular_dhash(img_rgb)
        # En fotos de estudio sobre fondo blanco uniforme, dHash tolera solo distancia <= 2
        # para no descartar gemas distintas pequeñas sobre el mismo fondo blanco.
        if sha in sha256_vistos or es_casi_duplicado(dhash, dhashes_vistos, umbral=2):
            stats["propias_eliminadas_duplicados"] += 1
            continue

        sha256_vistos.add(sha)
        dhashes_vistos.append(dhash)

        nombre_final = f"{clase}_propia_{idx:03d}.jpg"
        guardar_imagen_rgb_jpeg(img_rgb, carpeta_destino / nombre_final)
        registros.append(
            {
                "filename": f"{clase}/{nombre_final}",
                "clase": clase,
                "origen": "propia",
                "url": "N/A",
            }
        )
        idx += 1

    stats["propias_validas"] = len(registros)
    return registros, stats


def descargar_y_curar_clase(
    session: requests.Session,
    clase: str,
    terminos: List[str],
    carpeta_destino: Path,
    n_propias_validas: int,
    sha256_vistos: set[str],
    dhashes_vistos: List[np.ndarray],
    permitir_openverse: bool,
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """Descarga imágenes por web scraping y aplica curación automática documentada."""
    faltantes_min = max(0, config.MIN_TOTAL_POR_CLASE - n_propias_validas)
    # Margen holgado (al menos ~165-180 descargas o 1.35x lo faltante) para compensar descartes
    objetivo_validas_scraping = max(faltantes_min + 10, 120)
    objetivo_descargas = max(config.OBJETIVO_DESCARGA_POR_CLASE, int(objetivo_validas_scraping * 1.35))

    print(
        f"\n--- Clase '{clase}' ({config.CLASES_NOMBRES[clase]}) ---\n"
        f"  Fotos propias válidas : {n_propias_validas}\n"
        f"  Meta scraping válidas : {objetivo_validas_scraping} "
        f"(total mínimo requerido por guía: {config.MIN_TOTAL_POR_CLASE})\n"
        f"  Candidatos a recolectar: {objetivo_descargas}"
    )

    candidatos = buscar_en_wikimedia_commons(
        session=session,
        terminos=terminos,
        objetivo_candidatos=objetivo_descargas,
    )
    print(f"  Wikimedia Commons devolvió {len(candidatos)} candidatos únicos.")

    if len(candidatos) < objetivo_descargas and permitir_openverse:
        urls_ya = {c["url_origen"] for c in candidatos}
        extra = buscar_en_openverse(
            session=session,
            terminos=terminos,
            objetivo_extra=objetivo_descargas - len(candidatos),
            urls_existentes=urls_ya,
        )
        print(f"  Openverse (respaldo) aportó {len(extra)} candidatos adicionales.")
        candidatos.extend(extra)

    stats = {
        "scraping_candidatos_encontrados": len(candidatos),
        "scraping_descargadas": 0,
        "scraping_errores_http": 0,
        "eliminadas_corruptas": 0,
        "eliminadas_resolucion": 0,
        "eliminadas_no_rgb_gris": 0,
        "eliminadas_duplicados": 0,
        "scraping_validas": 0,
    }
    registros: List[Dict[str, str]] = []
    idx = 1

    for i, cand in enumerate(candidatos, start=1):
        # Detener si ya alcanzamos el objetivo de válidas y al menos 160 intentos si faltara margen
        if len(registros) >= objetivo_validas_scraping and stats["scraping_descargadas"] >= min(
            config.OBJETIVO_DESCARGA_POR_CLASE, len(candidatos)
        ):
            break
        if len(registros) >= objetivo_validas_scraping + 15:
            break

        time.sleep(config.SLEEP_ENTRE_PETICIONES)
        try:
            resp = session.get(cand["url_descarga"], timeout=HTTP_TIMEOUT)
            if resp.status_code == 429:
                print("  [Aviso] HTTP 429 en descarga de imagen; esperando 3 s...")
                time.sleep(3.0)
                resp = session.get(cand["url_descarga"], timeout=HTTP_TIMEOUT)
            if resp.status_code != 200 or not resp.content:
                stats["scraping_errores_http"] += 1
                continue
        except requests.RequestException:
            stats["scraping_errores_http"] += 1
            continue

        raw_bytes = resp.content
        stats["scraping_descargadas"] += 1

        img_rgb, motivo = validar_y_normalizar_imagen(raw_bytes)
        if motivo is not None or img_rgb is None:
            stats[f"eliminadas_{motivo}"] += 1
            continue

        sha = calcular_sha256(raw_bytes)
        dhash = calcular_dhash(img_rgb)
        if sha in sha256_vistos or es_casi_duplicado(dhash, dhashes_vistos):
            stats["eliminadas_duplicados"] += 1
            continue

        sha256_vistos.add(sha)
        dhashes_vistos.append(dhash)

        nombre_final = f"{clase}_scraping_{idx:03d}.jpg"
        guardar_imagen_rgb_jpeg(img_rgb, carpeta_destino / nombre_final)
        registros.append(
            {
                "filename": f"{clase}/{nombre_final}",
                "clase": clase,
                "origen": "scraping",
                "url": cand["url_origen"],
            }
        )
        idx += 1

        if i % 25 == 0 or len(registros) == objetivo_validas_scraping:
            print(
                f"  Progreso [{clase}]: {i}/{len(candidatos)} revisadas | "
                f"descargadas={stats['scraping_descargadas']} | válidas={len(registros)}"
            )

    stats["scraping_validas"] = len(registros)
    return registros, stats


# ==============================================================================
# 5. PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================
def main() -> None:
    print("=" * 78)
    print("WEB SCRAPING ÉTICO Y CURACIÓN AUTOMÁTICA — ENTREGA 4 VISIÓN ARTIFICIAL")
    print("=" * 78)
    print(f"Clases configuradas : {config.CLASE_0} ({config.CLASE_0_NOMBRE}) vs. {config.CLASE_1} ({config.CLASE_1_NOMBRE})")
    print(f"User-Agent          : {config.USER_AGENT}")
    print(f"Pausa entre requests: {config.SLEEP_ENTRE_PETICIONES} s")

    session = crear_sesion_http()

    # 1. Verificación obligatoria de robots.txt
    print("\n[1/4] Verificando robots.txt de las fuentes...")
    robots_wiki_site = verificar_robots_txt(
        session,
        WIKIMEDIA_ROBOTS_URL,
        "https://commons.wikimedia.org/wiki/Category:Emeralds",
        config.USER_AGENT,
    )
    robots_wiki_upload = verificar_robots_txt(
        session,
        WIKIMEDIA_UPLOAD_ROBOTS_URL,
        "https://upload.wikimedia.org/wikipedia/commons/",
        config.USER_AGENT,
    )
    robots_openverse = verificar_robots_txt(
        session, OPENVERSE_ROBOTS_URL, OPENVERSE_API_URL, config.USER_AGENT
    )

    for info_r in [robots_wiki_site, robots_wiki_upload, robots_openverse]:
        estado = "PERMITIDO" if info_r["permitido"] else "BLOQUEADO"
        print(
            f"  - {info_r['robots_url']} ({info_r['target_url']}) -> "
            f"HTTP {info_r['http_status']} | {estado} | {info_r['nota']}"
        )
    print(
        "  [Nota ética] En commons.wikimedia.org/robots.txt el prefijo /w/ se restringe a\n"
        "  rastreadores HTML de buscadores, mientras la política oficial de Wikimedia\n"
        "  (https://www.mediawiki.org/wiki/API:Etiquette) indica el uso de la API pública\n"
        "  /w/api.php con User-Agent descriptivo y pausas secuenciales, descargando los\n"
        "  archivos desde upload.wikimedia.org (permitido por robots.txt)."
    )

    if not (robots_wiki_site["permitido"] and robots_wiki_upload["permitido"]):
        raise RuntimeError(
            "Wikimedia Commons no permitió el acceso según robots.txt o no fue accesible. "
            "Se detiene la ejecución para respetar las políticas del sitio."
        )

    # 2. Preparar directorios limpios de salida
    config.DATASET_DIR.mkdir(parents=True, exist_ok=True)
    config.RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    config.FIGURAS_DIR.mkdir(parents=True, exist_ok=True)

    for clase in config.CLASES:
        carpeta_clase = config.DATASET_DIR / clase
        if carpeta_clase.exists():
            shutil.rmtree(carpeta_clase)
        carpeta_clase.mkdir(parents=True, exist_ok=True)

    # 3. Procesar fotos propias + scraping + curación por clase
    print("\n[2/4] Procesando fotos propias y ejecutando scraping + curación...")
    todos_registros: List[Dict[str, str]] = []
    resumen_clases: Dict[str, Any] = {}

    for clase in config.CLASES:
        carpeta_destino = config.DATASET_DIR / clase
        sha256_vistos: set[str] = set()
        dhashes_vistos: List[np.ndarray] = []

        reg_propias, stats_propias = procesar_fotos_propias(
            clase=clase,
            carpeta_destino=carpeta_destino,
            sha256_vistos=sha256_vistos,
            dhashes_vistos=dhashes_vistos,
        )

        if stats_propias["propias_validas"] < config.MIN_PROPIAS_RECOMENDADAS:
            print(
                f"  [ADVERTENCIA] Clase '{clase}': solo {stats_propias['propias_validas']} "
                f"fotos propias válidas (la guía exige mínimo {config.MIN_PROPIAS_RECOMENDADAS})."
            )

        reg_scraping, stats_scraping = descargar_y_curar_clase(
            session=session,
            clase=clase,
            terminos=config.TERMINOS_SCRAPING[clase],
            carpeta_destino=carpeta_destino,
            n_propias_validas=stats_propias["propias_validas"],
            sha256_vistos=sha256_vistos,
            dhashes_vistos=dhashes_vistos,
            permitir_openverse=bool(robots_openverse["permitido"]),
        )

        total_clase = len(reg_propias) + len(reg_scraping)
        todos_registros.extend(reg_propias)
        todos_registros.extend(reg_scraping)

        eliminadas_scraping_total = (
            stats_scraping["eliminadas_corruptas"]
            + stats_scraping["eliminadas_resolucion"]
            + stats_scraping["eliminadas_no_rgb_gris"]
            + stats_scraping["eliminadas_duplicados"]
        )

        resumen_clases[clase] = {
            "nombre_legible": config.CLASES_NOMBRES[clase],
            "terminos_busqueda": config.TERMINOS_SCRAPING[clase],
            **stats_propias,
            **stats_scraping,
            "eliminadas_scraping_total": eliminadas_scraping_total,
            "total_final": total_clase,
            "cumple_min_150": total_clase >= config.MIN_TOTAL_POR_CLASE,
        }

    # 4. Escribir dataset_origen.csv y curacion_log.json
    print("\n[3/4] Generando dataset/dataset_origen.csv y resultados/curacion_log.json...")
    with config.DATASET_CSV.open("w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=["filename", "clase", "origen", "url"])
        writer.writeheader()
        writer.writerows(todos_registros)

    totales_por_clase = [resumen_clases[c]["total_final"] for c in config.CLASES]
    ratio_balance = (
        round(min(totales_por_clase) / max(totales_por_clase), 4)
        if max(totales_por_clase) > 0
        else 0.0
    )

    log_curacion = {
        "fecha_ejecucion": datetime.now().isoformat(timespec="seconds"),
        "fuente_principal": "Wikimedia Commons API (https://commons.wikimedia.org/w/api.php)",
        "fuente_respaldo": "Openverse API (https://api.openverse.org/v1/images/)",
        "user_agent": config.USER_AGENT,
        "pausa_segundos": config.SLEEP_ENTRE_PETICIONES,
        "criterios_curacion": {
            "resolucion_minima_px": config.MIN_RESOLUCION_PX,
            "dhash_distancia_hamming_max": config.DHASH_DISTANCIA_MAX,
            "rechaza_corruptas": True,
            "rechaza_no_rgb_o_gris": True,
            "rechaza_duplicados_sha256_y_dhash": True,
        },
        "robots_txt": {
            "wikimedia_api": robots_wiki_site,
            "wikimedia_upload": robots_wiki_upload,
            "openverse_api": robots_openverse,
        },
        "clases": resumen_clases,
        "totales": {
            "total_propias": sum(resumen_clases[c]["propias_validas"] for c in config.CLASES),
            "total_scraping_descargadas": sum(resumen_clases[c]["scraping_descargadas"] for c in config.CLASES),
            "total_scraping_validas": sum(resumen_clases[c]["scraping_validas"] for c in config.CLASES),
            "total_scraping_eliminadas": sum(resumen_clases[c]["eliminadas_scraping_total"] for c in config.CLASES),
            "total_final_dataset": len(todos_registros),
            "ratio_balance_clases": ratio_balance,
        },
    }

    with config.CURACION_LOG_JSON.open("w", encoding="utf-8") as f_json:
        json.dump(log_curacion, f_json, ensure_ascii=False, indent=2)

    # 5. Imprimir resumen final tabular
    print("\n[4/4] RESUMEN FINAL DE CURACIÓN:")
    print("-" * 78)
    print(
        f"{'Clase':<14} {'Propias':>8} {'Descarg.':>9} {'Corrupt.':>9} "
        f"{'<150px':>7} {'NoRGB':>7} {'Duplic.':>8} {'ScrapOK':>8} {'TOTAL':>7}"
    )
    print("-" * 78)
    for clase in config.CLASES:
        s = resumen_clases[clase]
        print(
            f"{clase:<14} {s['propias_validas']:>8} {s['scraping_descargadas']:>9} "
            f"{s['eliminadas_corruptas']:>9} {s['eliminadas_resolucion']:>7} "
            f"{s['eliminadas_no_rgb_gris']:>7} {s['eliminadas_duplicados']:>8} "
            f"{s['scraping_validas']:>8} {s['total_final']:>7}"
        )
    print("-" * 78)
    print(f"CSV generado : {config.DATASET_CSV}")
    print(f"Log generado : {config.CURACION_LOG_JSON}")
    print(f"Balance (min/max): {ratio_balance:.3f}")
    print("=" * 78)


if __name__ == "__main__":
    main()
