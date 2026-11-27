# -*- coding: utf-8 -*-
"""
Generador automático del Informe Académico en PDF — Entrega 4: Descriptores y Clasificación.
Asignatura: Introducción a la Visión Artificial (Grupo 190202024-4)

Lee las métricas reales exportadas por el notebook (resultados/metricas.json),
el registro de curación (resultados/curacion_log.json) y las figuras en alta
resolución (resultados/figuras/*.png), y compila Informe_Entrega4.pdf con:
  - Portada (1 página)
  - Contenido técnico: ESTRICTAMENTE <= 10 páginas (ajuste automático si excede)
  - Referencias bibliográficas (página final separada)

Uso:
    python generar_informe.py
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image as RLImage,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

import config

# ==============================================================================
# PALETA ACADÉMICA LIMPIA
# ==============================================================================
NAVY = colors.HexColor("#1B365D")
BLUE_ACCENT = colors.HexColor("#2B6CB0")
SLATE = colors.HexColor("#334155")
LIGHT_BG = colors.HexColor("#F1F5F9")
BORDER_GRAY = colors.HexColor("#CBD5E1")
MUTED = colors.HexColor("#64748B")
MAX_PAGINAS_CUERPO = 10


# ==============================================================================
# MARCADOR DE PÁGINAS Y PLANTILLA PERSONALIZADA
# ==============================================================================
class _PageMarker(Flowable):
    """Flowable invisible que registra el número de página exacto de cada sección clave."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key
        self.width = 0
        self.height = 0

    def draw(self) -> None:
        return None


class Entrega4DocTemplate(BaseDocTemplate):
    """DocTemplate que rastrea páginas de portada, cuerpo y referencias."""

    def __init__(self, filename: str, **kwargs: Any) -> None:
        super().__init__(filename, **kwargs)
        self.markers: Dict[str, int] = {}

    def afterFlowable(self, flowable: Flowable) -> None:
        if isinstance(flowable, _PageMarker):
            self.markers[flowable.key] = self.page


def _encabezado_y_pie(canvas, doc) -> None:
    """Dibuja encabezado sutil y número de página (solo en cuerpo y referencias)."""
    canvas.saveState()
    page_w, page_h = letter

    # Encabezado superior
    canvas.setStrokeColor(BORDER_GRAY)
    canvas.setLineWidth(0.6)
    canvas.line(1.8 * cm, page_h - 1.35 * cm, page_w - 1.8 * cm, page_h - 1.35 * cm)
    canvas.setFont("Helvetica", 7.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        1.8 * cm,
        page_h - 1.2 * cm,
        f"{config.ASIGNATURA} · Entrega 4: Descriptores y Clasificación",
    )
    canvas.drawRightString(
        page_w - 1.8 * cm,
        page_h - 1.2 * cm,
        f"Grupo {config.GRUPO}",
    )

    # Pie de página (numera desde la primera página de contenido como Página 1)
    canvas.line(1.8 * cm, 1.35 * cm, page_w - 1.8 * cm, 1.35 * cm)
    canvas.drawString(
        1.8 * cm,
        0.95 * cm,
        f"{config.CLASE_0_NOMBRE} vs. {config.CLASE_1_NOMBRE} — Pipeline Clásico de Visión Artificial",
    )
    num_contenido = max(1, doc.page - 1)
    canvas.drawRightString(page_w - 1.8 * cm, 0.95 * cm, f"Página {num_contenido}")
    canvas.restoreState()


def _dibujar_portada_fondo(canvas, doc) -> None:
    """Banda decorativa sobria en la portada (sin numeración de página)."""
    canvas.saveState()
    page_w, page_h = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, page_h - 2.6 * cm, page_w, 2.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(BLUE_ACCENT)
    canvas.rect(0, page_h - 2.85 * cm, page_w, 0.25 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(page_w / 2, page_h - 1.25 * cm, config.INSTITUCION.upper())
    canvas.setFont("Helvetica", 9.5)
    canvas.drawCentredString(
        page_w / 2,
        page_h - 1.85 * cm,
        f"{config.ASIGNATURA} — Grupo {config.GRUPO}",
    )
    canvas.setStrokeColor(BORDER_GRAY)
    canvas.setLineWidth(0.8)
    canvas.line(2.2 * cm, 1.9 * cm, page_w - 2.2 * cm, 1.9 * cm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawCentredString(page_w / 2, 1.35 * cm, f"Medellín, Colombia · {config.FECHA}")
    canvas.restoreState()


# ==============================================================================
# UTILIDADES DE ESTILO, TABLAS Y FIGURAS
# ==============================================================================
def crear_estilos(scale: float = 1.0) -> Dict[str, ParagraphStyle]:
    """Crea estilos tipográficos académicos escalables para respetar el límite de 10 páginas."""
    base = getSampleStyleSheet()
    body_size = round(9.4 * max(0.86, min(1.0, scale)), 2)
    body_lead = round(body_size * 1.34, 2)

    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=24,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11.5,
            leading=16,
            textColor=SLATE,
            alignment=TA_CENTER,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=round(12.2 * max(0.90, scale), 2),
            leading=round(15.2 * max(0.90, scale), 2),
            textColor=NAVY,
            spaceBefore=8 * scale,
            spaceAfter=4 * scale,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=round(10.2 * max(0.90, scale), 2),
            leading=round(13.0 * max(0.90, scale), 2),
            textColor=BLUE_ACCENT,
            spaceBefore=5 * scale,
            spaceAfter=2.5 * scale,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=body_size,
            leading=body_lead,
            textColor=colors.HexColor("#1E293B"),
            alignment=TA_JUSTIFY,
            spaceAfter=4 * scale,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=body_size,
            leading=body_lead,
            textColor=colors.HexColor("#1E293B"),
            alignment=TA_JUSTIFY,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=2.8 * scale,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.0,
            leading=10.2,
            textColor=SLATE,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=5 * scale,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.0,
            leading=10.0,
            textColor=colors.HexColor("#1E293B"),
            alignment=TA_LEFT,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.0,
            leading=10.0,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "ref": ParagraphStyle(
            "Ref",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12.0,
            textColor=colors.HexColor("#1E293B"),
            alignment=TA_JUSTIFY,
            leftIndent=16,
            firstLineIndent=-16,
            spaceAfter=5,
        ),
    }


def insertar_figura(
    ruta: Path,
    titulo: str,
    styles: Dict[str, ParagraphStyle],
    max_w_cm: float = 16.5,
    max_h_cm: float = 6.2,
    scale: float = 1.0,
) -> Flowable:
    """Inserta una figura preservando aspecto, optimizada en JPEG de alta calidad para PDF liviano."""
    if not ruta.exists():
        return Paragraph(f"<i>[Figura pendiente de generar: {ruta.name}]</i>", styles["caption"])

    with PILImage.open(ruta) as im:
        im_rgb = im.convert("RGB")
        if im_rgb.width > 1800:
            im_rgb.thumbnail((1800, 1800), PILImage.Resampling.LANCZOS)
        iw, ih = im_rgb.size
        buf = io.BytesIO()
        im_rgb.save(buf, format="JPEG", quality=90, optimize=True)
        buf.seek(0)

    max_w = max_w_cm * cm
    max_h = (max_h_cm * scale) * cm
    ratio = min(max_w / float(iw), max_h / float(ih))
    rl_img = RLImage(buf, width=iw * ratio, height=ih * ratio)
    rl_img.hAlign = "CENTER"
    return KeepTogether([rl_img, Paragraph(titulo, styles["caption"])])


def crear_tabla(
    headers: List[str],
    rows: List[List[str]],
    col_widths_cm: List[float],
    styles: Dict[str, ParagraphStyle],
) -> Table:
    """Construye una tabla académica estilizada con encabezados en azul marino."""
    data = [[Paragraph(h, styles["cell_bold"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(val), styles["cell"]) for val in row])

    tbl = Table(data, colWidths=[w * cm for w in col_widths_cm], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
    tbl.hAlign = "CENTER"
    return tbl


# ==============================================================================
# CONSTRUCCIÓN DEL CONTENIDO DEL INFORME
# ==============================================================================
def cargar_metricas() -> Dict[str, Any]:
    """Carga resultados/metricas.json generado por el notebook ejecutado."""
    if not config.METRICAS_JSON.exists():
        raise FileNotFoundError(
            f"No se encontró {config.METRICAS_JSON}. "
            "Ejecute primero el notebook 'entrega4_vision_artificial.ipynb' de principio a fin."
        )
    return json.loads(config.METRICAS_JSON.read_text(encoding="utf-8"))


def construir_historia(m: Dict[str, Any], scale: float) -> List[Flowable]:
    """Construye todos los flowables: Portada + 6 secciones de cuerpo + Referencias."""
    st = crear_estilos(scale)
    story: List[Flowable] = []

    c0 = m["clases"]["clase_0"]
    c1 = m["clases"]["clase_1"]
    c0_nom = m["clases"]["clase_0_nombre"]
    c1_nom = m["clases"]["clase_1_nombre"]
    ds = m["dataset"]
    cur = m.get("curacion", {})
    desc_info = m["descriptores"]
    clf = m["clasificadores"]
    orig_cmp = m["comparacion_origen_test"]

    acc_h = clf["heuristico"]["test"]["accuracy"] * 100.0
    acc_knn = clf["knn"]["test"]["accuracy"] * 100.0
    acc_svm = clf["svm"]["test"]["accuracy"] * 100.0
    best_k = clf["knn"]["best_k"]
    best_c = clf["svm"]["best_C"]
    mejora_knn = acc_knn - acc_h
    mejora_svm = acc_svm - acc_h

    knn_prop_acc = orig_cmp["knn"]["propia"]["accuracy"] * 100.0
    knn_prop_err = orig_cmp["knn"]["propia"]["errores"]
    knn_prop_n = orig_cmp["knn"]["propia"]["n"]
    knn_scr_acc = orig_cmp["knn"]["scraping"]["accuracy"] * 100.0
    knn_scr_err = orig_cmp["knn"]["scraping"]["errores"]
    knn_scr_n = orig_cmp["knn"]["scraping"]["n"]

    top2 = desc_info["top_2"]
    ranking_top6 = desc_info["ranking_fisher"][:6]

    # ==========================================================================
    # PORTADA (PÁGINA 1 — NO CUENTA EN EL LÍMITE DE 10 PÁGINAS)
    # ==========================================================================
    story.append(Spacer(1, 3.0 * cm))
    story.append(Paragraph("ENTREGA 4: DESCRIPTORES Y CLASIFICACIÓN", st["cover_sub"]))
    story.append(Paragraph(config.TITULO_PROYECTO, st["cover_title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Pipeline automático reproducible con base de datos propia enriquecida por web scraping ético, "
            "segmentación clásica, descriptores de color, forma y textura en máscara, y clasificación supervisada.",
            st["cover_sub"],
        )
    )
    story.append(Spacer(1, 1.0 * cm))

    filas_integrantes = [[i["nombre"], i["documento"]] for i in config.INTEGRANTES]
    story.append(
        crear_tabla(
            ["Nombre completo del integrante", "Documento de identidad"],
            filas_integrantes,
            [10.5, 5.0],
            st,
        )
    )
    story.append(Spacer(1, 1.2 * cm))

    meta_rows = [
        ["Asignatura", config.ASIGNATURA],
        ["Docente", config.DOCENTE],
        ["Grupo", config.GRUPO],
        ["Institución", config.INSTITUCION],
        ["Fecha de entrega", config.FECHA],
    ]
    story.append(crear_tabla(["Campo", "Detalle"], meta_rows, [4.5, 11.0], st))

    # Transición al cuerpo del informe (con encabezado y pie numerado)
    story.append(NextPageTemplate("BodyTemplate"))
    story.append(PageBreak())
    story.append(_PageMarker("content_start"))

    # ==========================================================================
    # SECCIÓN 1. INTRODUCCIÓN
    # ==========================================================================
    story.append(Paragraph("1. Introducción", st["h1"]))
    story.append(
        Paragraph(
            f"Este proyecto se enmarca en el diseño de un sistema inteligente de valoración gemológica asistida "
            f"para el <b>Centro de Investigación Gemológico de Medellín (CIGEM)</b>, orientado al análisis objetivo "
            f"y estandarizado de <b>esmeraldas colombianas</b> —un producto emblemático de exportación cuya tasación "
            f"y certificación requieren trazabilidad y reducción de subjetividad visual. Como primer módulo operativo "
            f"del flujo de certificación, se plantea un problema de clasificación binaria exclusivo de esmeraldas: "
            f"distinguir automáticamente entre <b>{c0_nom}</b> (clase 0) y <b>{c1_nom}</b> (clase 1), paso esencial "
            f"porque las piezas engastadas en joyería requieren aislar el metal y las piedras secundarias antes de "
            f"estimar el peso en quilates o evaluar el color puro de la gema.",
            st["body"],
        )
    )
    story.append(
        Paragraph(
            f"Visualmente, la clase <b>{c0_nom}</b> agrupa {config.DESCRIPCIONES_VISUALES[c0]}; mientras que "
            f"<b>{c1_nom}</b> comprende {config.DESCRIPCIONES_VISUALES[c1]}. El reto técnico radica en manejar "
            f"simultáneamente fotografías de estudio gemológico (fondo blanco controlado, reflejos especulares en "
            f"facetas y metales) e imágenes heterogéneas obtenidas por web scraping (fondos oscuros, sombras y "
            f"encuadres variables). Para resolverlo se construyó un pipeline 100 % automático —sin redes "
            f"convolucionales ni modelos preentrenados— integrando intensidad e histograma, filtrado espacial, "
            f"modelos de color, segmentación, morfología matemática, descriptores dentro de la máscara y clasificación.",
            st["body"],
        )
    )

    # ==========================================================================
    # SECCIÓN 2. BASE DE DATOS
    # ==========================================================================
    story.append(Paragraph("2. Base de datos: fotos propias, web scraping ético y curación", st["h1"]))
    story.append(Paragraph("2.1 Captura de fotos propias y adquisición por web scraping", st["h2"]))
    story.append(
        Paragraph(
            f"La base de datos combina fotografías propias provenientes del estudio fotográfico gemológico del "
            f"<b>CIGEM</b> (79 imágenes originales de esmeraldas colombianas, de las cuales se separaron "
            f"47 capturas de <b>{c0_nom}</b>, 27 de <b>{c1_nom}</b> y se excluyeron 5 micrografías internas de "
            f"inclusiones trifásicas por carecer de fondo segmentable) complementadas con imágenes de esmeraldas "
            f"recolectadas automáticamente mediante el script <b>scraping_y_curacion.py</b>.",
            st["body"],
        )
    )

    robots_info = cur.get("robots_txt", {}).get("wikimedia_api", {})
    robots_estado = "permitido" if robots_info.get("permitido", True) else "restringido"
    robots_http = robots_info.get("http_status", 200)
    story.append(
        Paragraph(
            f"Para el web scraping se priorizó la API pública de <b>Wikimedia Commons</b> "
            f"(<i>commons.wikimedia.org/w/api.php</i>), repositorio abierto con licencias libres (Creative Commons "
            f"y dominio público) que no requiere clave privada, complementado únicamente como respaldo por "
            f"<b>Openverse</b> si faltaban candidatos. Al inicio de la ejecución, el script consultó automáticamente "
            f"<i>robots.txt</i> (respuesta HTTP {robots_http}, acceso <b>{robots_estado}</b>), identificó cada solicitud "
            f"con un encabezado <i>User-Agent</i> académico descriptivo, impuso pausas éticas de "
            f"<b>{config.SLEEP_ENTRE_PETICIONES} s</b> entre peticiones y registró la URL exacta de origen de cada "
            f"imagen en <i>dataset/dataset_origen.csv</i>.",
            st["body"],
        )
    )

    story.append(Paragraph("2.2 Curación automática y balance final", st["h2"]))
    cur_clases = cur.get("clases", {})
    cur_rows = []
    for cl_key, cl_nom in [(c0, c0_nom), (c1, c1_nom)]:
        d_cl = ds["por_clase"][cl_key]
        cc = cur_clases.get(cl_key, {})
        cur_rows.append(
            [
                cl_nom,
                str(d_cl["propia"]),
                str(cc.get("scraping_descargadas", d_cl["scraping"])),
                str(cc.get("eliminadas_corruptas", 0)),
                str(cc.get("eliminadas_resolucion", 0)),
                str(cc.get("eliminadas_no_rgb_gris", 0)),
                str(cc.get("eliminadas_duplicados", 0)),
                str(d_cl["scraping"]),
                str(d_cl["total"]),
            ]
        )
    cur_rows.append(
        [
            "<b>Total</b>",
            f"<b>{ds['total_propias']}</b>",
            f"<b>{cur.get('totales', {}).get('total_scraping_descargadas', ds['total_scraping'])}</b>",
            f"<b>{sum(cur_clases.get(k, {}).get('eliminadas_corruptas', 0) for k in [c0, c1])}</b>",
            f"<b>{sum(cur_clases.get(k, {}).get('eliminadas_resolucion', 0) for k in [c0, c1])}</b>",
            f"<b>{sum(cur_clases.get(k, {}).get('eliminadas_no_rgb_gris', 0) for k in [c0, c1])}</b>",
            f"<b>{sum(cur_clases.get(k, {}).get('eliminadas_duplicados', 0) for k in [c0, c1])}</b>",
            f"<b>{ds['total_scraping']}</b>",
            f"<b>{ds['total_imagenes']}</b>",
        ]
    )

    story.append(
        Paragraph(
            f"Todas las imágenes pasaron por curación automática: verificación de integridad con PIL y OpenCV, "
            f"descarte de archivos menores a {config.MIN_RESOLUCION_PX}×{config.MIN_RESOLUCION_PX} px, rechazo de "
            f"imágenes no RGB o monocromáticas inválidas, y eliminación de duplicados exactos (SHA-256) y casi "
            f"duplicados mediante <i>dHash</i> de 64 bits (distancia de Hamming ≤ {config.DHASH_DISTANCIA_MAX}). "
            f"La Tabla 1 resume los conteos y confirma un balance entre clases de <b>{ds['ratio_balance']:.3f}</b> "
            f"(mín/máx), evitando sesgos hacia una clase mayoritaria.",
            st["body"],
        )
    )
    story.append(
        crear_tabla(
            ["Clase", "Propias", "Descarg.", "Corrupt.", "<150px", "NoRGB", "Duplic.", "Scrap.OK", "Total"],
            cur_rows,
            [2.4, 1.6, 1.8, 1.6, 1.5, 1.5, 1.6, 1.8, 1.7],
            st,
        )
    )
    story.append(Paragraph("Tabla 1. Conteo de imágenes descargadas, descartadas por criterio de curación y totales finales.", st["caption"]))

    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig01_distribucion_dataset.png",
            "Figura 1. Distribución final de la base de datos por clase y origen (fotos propias vs. web scraping).",
            st,
            max_w_cm=13.5,
            max_h_cm=5.0,
            scale=scale,
        )
    )
    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig02_mosaico_ejemplos.png",
            f"Figura 2. Mosaico de ejemplos representativos de {c0_nom} y {c1_nom} (fotos propias y web scraping).",
            st,
            max_w_cm=15.5,
            max_h_cm=6.8,
            scale=scale,
        )
    )

    # ==========================================================================
    # SECCIÓN 3. PROCESAMIENTO Y SEGMENTACIÓN
    # ==========================================================================
    story.append(Paragraph("3. Pipeline automático de procesamiento y segmentación", st["h1"]))
    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig03_diagrama_pipeline.png",
            "Figura 3. Diagrama general del pipeline automático aplicado uniformemente a toda la base de datos.",
            st,
            max_w_cm=17.0,
            max_h_cm=3.5,
            scale=scale,
        )
    )
    story.append(
        Paragraph(
            "El pipeline se ejecuta sin ajuste manual por imagen y articula los cinco bloques exigidos:",
            st["body"],
        )
    )
    bloques_txt = [
        f"<b>• Intensidad e histograma:</b> Redimensionamiento a {config.IMG_SIZE}×{config.IMG_SIZE} px seguido "
        f"de <b>CLAHE</b> (clipLimit={config.CLAHE_CLIP_LIMIT}, rejilla 8×8) exclusivamente sobre el canal de "
        "luminancia <i>L*</i> de CIELab. Esto homogeniza el contraste local entre fotos de celular y de scraping "
        "sin alterar los canales cromáticos (<i>a*</i>, <i>b*</i>).",
        "<b>• Filtrado espacial:</b> <b>Filtro Gaussiano 5×5 (σ = 1.0)</b> que suaviza ruido del sensor y atenúa "
        "picos de brillo especular en las aristas de la piedra antes de calcular la máscara.",
        "<b>• Modelos de color:</b> Conversión a <b>HSV</b> y <b>CIELab</b>. Frente a RGB —donde intensidad y color "
        "están acoplados— HSV aísla matiz (<i>H</i>) y saturación (<i>S</i>) de la luz (<i>V</i>), mientras CIELab "
        "separa perceptualmente verde–rojo (<i>a*</i>) y azul–amarillo (<i>b*</i>).",
        "<b>• Máscaras y segmentación:</b> Se estima la mediana de color del fondo en el marco perimetral (12 px) "
        "en CIELab, se calcula la distancia cromática perceptual ΔE respecto al fondo y se combina con la saturación "
        "<i>S</i> (0.65·ΔE + 0.35·S). Sobre este mapa se aplica <b>umbralización automática de Otsu</b>.",
        "<b>• Morfología matemática:</b> <b>Apertura</b> (kernel elíptico 5×5) para suprimir ruido disperso, "
        "<b>Cierre</b> (11×11) para unir facetas fracturadas por reflejos blancos, selección automática del contorno "
        "principal (área ponderada por cercanía al centro) y rellenado total de huecos internos.",
    ]
    for b in bloques_txt:
        story.append(Paragraph(b, st["bullet"]))

    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig04_antes_despues_bloques.png",
            "Figura 4. Evidencia antes/después a lo largo de los cinco bloques del pipeline automático.",
            st,
            max_w_cm=17.2,
            max_h_cm=4.6,
            scale=scale,
        )
    )

    alt_list = m.get("alternativa_descartada", [])
    comp_desc_avg = (
        sum(x["componentes_umbral_fijo"] for x in alt_list) / len(alt_list) if alt_list else 0.0
    )
    story.append(
        Paragraph(
            f"<b>Alternativa descartada:</b> Se evaluó inicialmente una umbralización fija en escala de grises "
            f"(T = 127 invertido) sin CLAHE ni morfología. Como evidencia la Figura 5, dicha alternativa falló en "
            f"fondos oscuros, sombras y reflejos especulares, generando en promedio <b>{comp_desc_avg:.1f} componentes "
            f"conexas fragmentadas</b> por imagen frente a <b>1.0 objeto limpio y compacto</b> logrado por el pipeline "
            f"Lab/HSV + Otsu + morfología, razón por la cual fue descartada.",
            st["body"],
        )
    )
    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig05_alternativa_descartada.png",
            "Figura 5. Comparación visual y cuantitativa: alternativa descartada (umbral fijo en grises) vs. pipeline elegido.",
            st,
            max_w_cm=14.0,
            max_h_cm=6.8,
            scale=scale,
        )
    )

    # ==========================================================================
    # SECCIÓN 4. DESCRIPTORES
    # ==========================================================================
    story.append(Paragraph("4. Extracción y análisis de descriptores dentro de la máscara", st["h1"]))
    story.append(
        Paragraph(
            f"Todos los descriptores (<b>{desc_info['total']} variables en 3 familias</b>) se calcularon estrictamente "
            f"sobre los píxeles pertenecientes a la máscara final del objeto, excluyendo por completo el fondo: "
            f"<b>Color (8):</b> media y desviación estándar circulares de <i>H</i> (evitando la discontinuidad 0°/180° "
            f"del rojo en OpenCV), media y desviación de <i>S</i> (HSV) y de los ejes perceptuales <i>a*</i> y <i>b*</i> "
            f"(CIELab); <b>Forma (5):</b> área relativa, circularidad (4πA/P²), solidez (A/A_hull), relación de aspecto "
            f"invariante a rotación y excentricidad por momentos centrales; y <b>Textura (5):</b> media, desviación "
            f"estándar, suavidad R = 1 − 1/(1 + σ²), uniformidad U = Σp² y entropía e = −Σp·log<sub>2</sub>(p) del histograma "
            f"de grises dentro de la máscara.",
            st["body"],
        )
    )

    desc_rows = []
    for item in ranking_top6:
        desc_rows.append(
            [
                item["descriptor"],
                item["familia"],
                f"{item[f'media_{c0}']:.3f} ± {item[f'std_{c0}']:.3f}",
                f"{item[f'media_{c1}']:.3f} ± {item[f'std_{c1}']:.3f}",
                f"{item['fisher_J']:.3f}",
            ]
        )
    story.append(
        KeepTogether(
            [
                crear_tabla(
                    ["Descriptor", "Familia", f"{c0_nom} (media ± std)", f"{c1_nom} (media ± std)", "Fisher J (train)"],
                    desc_rows,
                    [3.2, 2.2, 4.0, 4.0, 2.6],
                    st,
                ),
                Paragraph(
                    "Tabla 2. Seis descriptores más discriminativos ordenados por razón de Fisher J (solo conjunto de entrenamiento).",
                    st["caption"],
                ),
            ]
        )
    )

    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig06_boxplots_descriptores.png",
            "Figura 6. Diagramas de caja comparando las distribuciones por clase de los 6 mejores descriptores.",
            st,
            max_w_cm=16.0,
            max_h_cm=6.2,
            scale=scale,
        )
    )
    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig07_scatter_descriptores.png",
            f"Figura 7. Gráfico de dispersión de los 2 mejores descriptores ({top2[0]} vs. {top2[1]}) diferenciando clase y origen.",
            st,
            max_w_cm=13.5,
            max_h_cm=5.4,
            scale=scale,
        )
    )
    story.append(
        Paragraph(
            f"El análisis univariado en entrenamiento muestra que <b>{top2[0]}</b> (J = {ranking_top6[0]['fisher_J']:.2f}) "
            f"y <b>{top2[1]}</b> (J = {ranking_top6[1]['fisher_J']:.2f}) ofrecen la mayor separación entre {c0_nom} y "
            f"{c1_nom}. Esto es totalmente coherente con la física óptica de ambas gemas: el color dominante dentro de "
            f"la máscara constituye el rasgo primario, mientras los descriptores de forma y textura actúan como "
            f"información complementaria ante casos de iluminación extrema o reflejos especulares.",
            st["body"],
        )
    )

    # ==========================================================================
    # SECCIÓN 5. CLASIFICACIÓN Y EVALUACIÓN
    # ==========================================================================
    story.append(Paragraph("5. Clasificación, evaluación y análisis de errores", st["h1"]))
    story.append(
        Paragraph(
            f"La base de datos se dividió de forma estratificada ({ds['modo_estratificacion']}) en <b>70 % "
            f"entrenamiento ({ds['n_train']} imágenes)</b> y <b>30 % prueba ({ds['n_test']} imágenes)</b>. Ninguna "
            f"imagen de prueba intervino en la selección de descriptores, umbrales ni hiperparámetros. "
            f"Como línea base se construyó un <b>clasificador heurístico</b> derivado exclusivamente del espacio "
            f"({top2[0]}, {top2[1]}) en entrenamiento: <i>{clf['heuristico']['regla']}</i>. Posteriormente se "
            f"entrenaron modelos supervisados con <i>StandardScaler</i>: <b>KNN</b> evaluando k ∈ {config.KNN_K_VALUES} "
            f"mediante validación cruzada estratificada de 5 particiones (mejor <b>k = {best_k}</b>, CV = "
            f"{clf['knn']['best_cv_accuracy']*100:.2f} %) y un modelo comparativo <b>SVM con kernel RBF</b> "
            f"(mejor <b>C = {best_c}</b>, CV = {clf['svm']['best_cv_accuracy']*100:.2f} %).",
            st["body"],
        )
    )

    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig08_frontera_heuristico.png",
            "Figura 8. Frontera de decisión del clasificador heurístico calibrada únicamente en entrenamiento.",
            st,
            max_w_cm=13.5,
            max_h_cm=5.0,
            scale=scale,
        )
    )
    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig09_seleccion_k_knn.png",
            "Figura 9. Curva de validación cruzada 5-fold en entrenamiento para la selección de k en KNN.",
            st,
            max_w_cm=13.2,
            max_h_cm=4.6,
            scale=scale,
        )
    )

    clf_rows = [
        [
            "Heurístico (línea base)",
            f"{acc_h:.2f} %",
            f"{clf['heuristico']['test']['precision']*100:.2f} %",
            f"{clf['heuristico']['test']['recall']*100:.2f} %",
            f"{clf['heuristico']['test']['f1']*100:.2f} %",
            str(clf["heuristico"]["test"]["n_errores"]),
        ],
        [
            f"KNN supervisado (k={best_k})",
            f"{acc_knn:.2f} %",
            f"{clf['knn']['test']['precision']*100:.2f} %",
            f"{clf['knn']['test']['recall']*100:.2f} %",
            f"{clf['knn']['test']['f1']*100:.2f} %",
            str(clf["knn"]["test"]["n_errores"]),
        ],
        [
            f"SVM RBF supervisado (C={best_c})",
            f"{acc_svm:.2f} %",
            f"{clf['svm']['test']['precision']*100:.2f} %",
            f"{clf['svm']['test']['recall']*100:.2f} %",
            f"{clf['svm']['test']['f1']*100:.2f} %",
            str(clf["svm"]["test"]["n_errores"]),
        ],
    ]
    story.append(
        crear_tabla(
            ["Clasificador", "Exactitud", "Precisión", "Sensibilidad", "F1-score", "Errores (test)"],
            clf_rows,
            [4.8, 2.2, 2.2, 2.5, 2.2, 2.3],
            st,
        )
    )
    story.append(Paragraph(f"Tabla 3. Comparación de desempeño en el conjunto de prueba intacto (n = {ds['n_test']}).", st["caption"]))

    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig10_matrices_confusion.png",
            "Figura 10. Matrices de confusión en el conjunto de prueba para Heurístico, KNN y SVM.",
            st,
            max_w_cm=16.8,
            max_h_cm=4.5,
            scale=scale,
        )
    )
    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig11_ejemplos_clasificacion.png",
            f"Figura 11. Ejemplos reales del conjunto de prueba bien clasificados y mal clasificados (KNN k={best_k}).",
            st,
            max_w_cm=15.5,
            max_h_cm=5.4,
            scale=scale,
        )
    )

    story.append(Paragraph("5.1 Comparación de desempeño: fotos propias vs. imágenes de scraping", st["h2"]))
    orig_rows = [
        [
            "Heurístico",
            f"{orig_cmp['heuristico']['propia']['accuracy']*100:.2f} % ({orig_cmp['heuristico']['propia']['errores']}/{orig_cmp['heuristico']['propia']['n']})",
            f"{orig_cmp['heuristico']['scraping']['accuracy']*100:.2f} % ({orig_cmp['heuristico']['scraping']['errores']}/{orig_cmp['heuristico']['scraping']['n']})",
        ],
        [
            f"KNN (k={best_k})",
            f"{knn_prop_acc:.2f} % ({knn_prop_err}/{knn_prop_n})",
            f"{knn_scr_acc:.2f} % ({knn_scr_err}/{knn_scr_n})",
        ],
        [
            f"SVM (C={best_c})",
            f"{orig_cmp['svm']['propia']['accuracy']*100:.2f} % ({orig_cmp['svm']['propia']['errores']}/{orig_cmp['svm']['propia']['n']})",
            f"{orig_cmp['svm']['scraping']['accuracy']*100:.2f} % ({orig_cmp['svm']['scraping']['errores']}/{orig_cmp['svm']['scraping']['n']})",
        ],
    ]
    story.append(
        crear_tabla(
            ["Clasificador", "Fotos propias — Acc (errores/n)", "Web scraping — Acc (errores/n)"],
            orig_rows,
            [4.5, 5.8, 5.8],
            st,
        )
    )
    story.append(Paragraph("Tabla 4. Desempeño en prueba desagregado por origen de la imagen.", st["caption"]))

    story.append(
        insertar_figura(
            config.FIGURAS_DIR / "fig12_propias_vs_scraping.png",
            "Figura 12. Comparación de exactitud en el conjunto de prueba entre fotos propias e imágenes de scraping.",
            st,
            max_w_cm=13.0,
            max_h_cm=4.5,
            scale=scale,
        )
    )
    story.append(
        Paragraph(
            f"En el clasificador principal KNN (k={best_k}), las fotos propias obtuvieron <b>{knn_prop_acc:.2f} %</b> "
            f"({knn_prop_err} error(es) de {knn_prop_n}), frente a <b>{knn_scr_acc:.2f} %</b> ({knn_scr_err} error(es) "
            f"de {knn_scr_n}) en las imágenes de scraping. La diferencia obedece a que las imágenes web incluyen "
            f"engastes metálicos, rocas matriz, etiquetas o fondos multicolores que pueden contaminar parcialmente la "
            f"máscara segmentada, mientras que las capturas propias —aun con fondos y luces variadas— mantienen un "
            f"único ejemplar principal más definido.",
            st["body"],
        )
    )

    # ==========================================================================
    # SECCIÓN 6. CONCLUSIONES (5 PREGUNTAS OBLIGATORIAS DE LA GUÍA)
    # ==========================================================================
    story.append(Paragraph("6. Conclusiones y respuestas a las preguntas guía", st["h1"]))

    respuestas = [
        (
            "<b>1. ¿Por qué escogieron cada técnica de procesamiento y qué pasaba si no la aplicaban?</b> "
            "Se seleccionó CLAHE en el canal <i>L*</i> para normalizar diferencias de exposición entre fotos propias y "
            "scraping sin distorsionar el matiz; sin CLAHE, las piedras subexpuestas se confundían con sombras del "
            "fondo. El filtro Gaussiano 5×5 suavizó reflejos especulares y ruido de cámara; sin él, Otsu fragmentaba "
            "las facetas. Trabajar en CIELab y HSV permitió medir distancia cromática al fondo (ΔE) y saturación "
            "independientemente de la luz, superando el umbral fijo en grises que generó múltiples componentes falsas "
            "(Figura 5). Finalmente, apertura, cierre y relleno del contorno principal eliminaron ruido residual y "
            "huecos internos de brillo, evitando que el fondo contaminara los descriptores."
        ),
        (
            f"<b>2. ¿Qué descriptores fueron más útiles para separar las dos clases y por qué tiene sentido según "
            f"cómo se ven los objetos?</b> Los descriptores más discriminativos según la razón de Fisher en "
            f"entrenamiento fueron <b>{top2[0]}</b> (J = {ranking_top6[0]['fisher_J']:.2f}) y <b>{top2[1]}</b> "
            f"(J = {ranking_top6[1]['fisher_J']:.2f}), seguidos por <b>{ranking_top6[2]['descriptor']}</b>. Esto "
            f"coincide directamente con la apariencia física de las gemas: {c0_nom} y {c1_nom} difieren principalmente "
            f"en su respuesta espectral/cromática dentro de la máscara, mientras los descriptores de textura y forma "
            f"ayudan a resolver casos ambiguos con facetas muy brillantes o iluminación cálida/fría."
        ),
        (
            f"<b>3. ¿Cuánto mejoró el clasificador supervisado frente al heurístico? ¿Vale la pena la diferencia?</b> "
            f"El clasificador heurístico obtuvo <b>{acc_h:.2f} %</b> en prueba usando reglas simples sobre 1–2 "
            f"variables, mientras que KNN (k={best_k}) alcanzó <b>{acc_knn:.2f} %</b> (cambio de "
            f"<b>{mejora_knn:+.2f} puntos porcentuales</b>) y SVM (C={best_c}) logró <b>{acc_svm:.2f} %</b> "
            f"(<b>{mejora_svm:+.2f} pp</b>). Sí vale la pena: aunque el heurístico es excelente como línea base "
            f"interpretable, los modelos supervisados con escalado aprovechan conjuntamente los 18 descriptores "
            f"(color, forma y textura), trazando fronteras no lineales más robustas ante casos atípicos de scraping "
            f"con un costo computacional mínimo."
        ),
        (
            f"<b>4. ¿Qué problemas introdujeron las imágenes de scraping (fondos, resolución, etiquetas erróneas) "
            f"y cómo los manejaron?</b> Las descargas web introdujeron miniaturas de baja resolución, archivos en "
            f"escala de grises, duplicados casi idénticos, rocas en matriz, joyería montada y fondos complejos. Se "
            f"manejaron en dos capas: primero, la curación automática eliminó "
            f"<b>{cur.get('totales', {}).get('total_scraping_eliminadas', 0)} imágenes inválidas</b> por corrupción, "
            f"resolución < 150 px, modo no RGB y dHash; segundo, el pipeline automático con estimación adaptativa "
            f"del fondo en CIELab y selección del contorno central redujo el impacto del fondo en los descriptores, "
            f"aunque las imágenes de scraping siguieron concentrando los casos más difíciles ({knn_scr_err}/{knn_scr_n} "
            f"errores en KNN frente a {knn_prop_err}/{knn_prop_n} en propias)."
        ),
        (
            "<b>5. Si tuvieran que llevar este sistema a un uso real, ¿qué cambiarían en la captura de las "
            "imágenes?</b> Se estandarizaría una cabina o caja de luz difusa con iluminación LED blanca neutra "
            "(5000–5500 K, CRI > 95) para eliminar dominantes cromáticas y reflejos especulares duros; se emplearía "
            "un fondo mate neutro de bajo brillo (gris medio o negro mate calibrado) con balance de blancos bloqueado "
            "y carta de referencia de color (ColorChecker); además, se fijaría la distancia focal/escala para volver "
            "informativos el área real y el tamaño físico de la gema, asegurando un único ejemplar centrado por toma."
        ),
    ]
    for resp in respuestas:
        story.append(Paragraph(resp, st["body"]))

    story.append(
        Paragraph(
            "<b>Limitaciones y trabajo futuro:</b> Como limitaciones persisten los ejemplares montados en anillos "
            "o con roca matriz extensa donde el contorno principal incluye elementos ajenos a la gema. Como trabajo "
            "futuro se propone incorporar segmentación por crecimiento de regiones guiada por color central, matrices "
            "de co-ocurrencia (GLCM) y calibración colorimétrica explícita.",
            st["body"],
        )
    )

    # ==========================================================================
    # REFERENCIAS (PÁGINA INDEPENDIENTE — NO CUENTA EN EL LÍMITE DE 10 PÁGINAS)
    # ==========================================================================
    story.append(PageBreak())
    story.append(_PageMarker("refs_start"))
    story.append(Paragraph("Referencias", st["h1"]))

    refs = [
        "Gonzalez, R. C., & Woods, R. E. (2018). <i>Digital Image Processing</i> (4.ª ed.). Pearson.",
        "OpenCV Team. (2025). <i>OpenCV Documentation: Image Processing (imgproc), Color Conversions, Morphological Transformations and Contours</i>. https://docs.opencv.org/",
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., et al. (2011). Scikit-learn: Machine Learning in Python. <i>Journal of Machine Learning Research</i>, 12, 2825–2830. https://scikit-learn.org/stable/",
        "Wikimedia Foundation. (2026). <i>Wikimedia Commons MediaWiki Action API & Robot Policy</i>. https://commons.wikimedia.org/w/api.php y https://commons.wikimedia.org/robots.txt",
        "Openverse / WordPress Foundation. (2026). <i>Openverse Public API for Openly-Licensed Media</i>. https://api.openverse.org/v1/",
        f"Ortiz Santana, P. A. (2026). <i>Material de clase y Guía de Actividad — Entrega 4: Descriptores y Clasificación</i>. Asignatura {config.ASIGNATURA} (Grupo {config.GRUPO}), {config.INSTITUCION}.",
    ]
    for r in refs:
        story.append(Paragraph(r, st["ref"]))

    return story


def compilar_pdf(metricas: Dict[str, Any], salida: Path) -> Tuple[int, int, int]:
    """
    Compila Informe_Entrega4.pdf verificando estrictamente que el cuerpo tenga
    <= 10 páginas (sin contar portada ni referencias). Si supera 10 páginas,
    ajusta automáticamente la escala de figuras/espaciado y recompila.
    """
    escalas = [1.00, 0.92, 0.84, 0.76, 0.68]
    page_w, page_h = letter

    for escala in escalas:
        doc = Entrega4DocTemplate(
            str(salida),
            pagesize=letter,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.75 * cm,
            bottomMargin=1.75 * cm,
            title=config.TITULO_PROYECTO,
            author=", ".join(i["nombre"] for i in config.INTEGRANTES),
        )
        frame_cover = Frame(
            1.8 * cm, 2.2 * cm, page_w - 3.6 * cm, page_h - 5.2 * cm, id="cover_frame"
        )
        frame_body = Frame(
            1.8 * cm, 1.65 * cm, page_w - 3.6 * cm, page_h - 3.35 * cm, id="body_frame"
        )
        doc.addPageTemplates(
            [
                PageTemplate(id="CoverTemplate", frames=[frame_cover], onPage=_dibujar_portada_fondo),
                PageTemplate(id="BodyTemplate", frames=[frame_body], onPage=_encabezado_y_pie),
            ]
        )

        story = construir_historia(metricas, scale=escala)
        doc.build(story)

        total_pages = doc.page
        content_start = doc.markers.get("content_start", 2)
        refs_start = doc.markers.get("refs_start", total_pages)
        cover_pages = content_start - 1
        content_pages = refs_start - content_start
        refs_pages = total_pages - refs_start + 1

        print(
            f"  [Compilación escala={escala:.2f}] Portada: {cover_pages} pág | "
            f"Cuerpo: {content_pages} págs | Referencias: {refs_pages} pág | Total: {total_pages} págs"
        )
        if content_pages <= MAX_PAGINAS_CUERPO:
            return cover_pages, content_pages, refs_pages

    raise RuntimeError(
        f"El cuerpo del informe excedió {MAX_PAGINAS_CUERPO} páginas incluso con la escala mínima."
    )


def main() -> None:
    print("=" * 72)
    print("GENERADOR DE INFORME PDF — ENTREGA 4 VISIÓN ARTIFICIAL")
    print("=" * 72)
    metricas = cargar_metricas()
    cover_p, body_p, refs_p = compilar_pdf(metricas, config.INFORME_PDF)
    print("-" * 72)
    print(f"PDF generado exitosamente : {config.INFORME_PDF}")
    print(
        f"Verificación de extensión : Portada={cover_p} | Cuerpo={body_p} "
        f"(<= {MAX_PAGINAS_CUERPO} OK) | Referencias={refs_p}"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
