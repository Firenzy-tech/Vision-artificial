# -*- coding: utf-8 -*-
"""
Configuración centralizada del proyecto — Entrega 4: Descriptores y Clasificación.
Asignatura: Introducción a la Visión Artificial (Grupo 190202024-4)

Proyecto contextualizado en el Centro de Investigación Gemológico de Medellín (CIGEM):
Clasificación binaria exclusiva de esmeraldas colombianas:
  - Clase 0: esmeralda_suelta  (esmeraldas sueltas talladas o trapiche, sin engaste)
  - Clase 1: esmeralda_montada (esmeraldas engastadas en piezas de joyería)
"""

from pathlib import Path

# ==============================================================================
# 1. DEFINICIÓN DE CLASES Y TÉRMINOS DE SCRAPING (EXCLUSIVO ESMERALDAS — CIGEM)
# ==============================================================================
CLASE_0 = "esmeralda_suelta"
CLASE_0_NOMBRE = "Esmeralda suelta"
TERMINOS_SCRAPING_0 = [
    "emerald gemstone",
    "cut emerald",
    "emerald crystal",
    "trapiche emerald",
    "emerald mineral",
    "emerald beryl",
]
CLASE_0_DESC_VISUAL = (
    "ejemplares de esmeralda sin engaste (talladas o trapiche), donde la región segmentada "
    "presenta un color verde dominante más homogéneo (canal a* fuertemente negativo en CIELab, "
    "baja dispersión cromática H_std/b_std) y contornos compactos de alta solidez y convexidad"
)

CLASE_1 = "esmeralda_montada"
CLASE_1_NOMBRE = "Esmeralda montada"
TERMINOS_SCRAPING_1 = [
    "emerald ring",
    "emerald pendant",
    "emerald necklace",
    "emerald earrings",
    "emerald brooch",
    "emerald jewelry",
    "emerald bracelet",
    "emerald tiara",
]
CLASE_1_DESC_VISUAL = (
    "piezas de joyería con esmeraldas engastadas en oro o plata (anillos, dijes, cruces, "
    "aretes, pulseras y collares), donde coexisten el verde de la gema con tonos metálicos "
    "amarillos/blancos (mayor b_mean y mayor dispersión cromática H_std, a_std, b_std), "
    "textura más heterogénea por diamantes y garras, y contornos menos compactos (menor solidez)"
)

CLASES = [CLASE_0, CLASE_1]
CLASES_NOMBRES = {
    CLASE_0: CLASE_0_NOMBRE,
    CLASE_1: CLASE_1_NOMBRE,
}
TERMINOS_SCRAPING = {
    CLASE_0: TERMINOS_SCRAPING_0,
    CLASE_1: TERMINOS_SCRAPING_1,
}
DESCRIPCIONES_VISUALES = {
    CLASE_0: CLASE_0_DESC_VISUAL,
    CLASE_1: CLASE_1_DESC_VISUAL,
}

# ==============================================================================
# 2. METADATOS ACADÉMICOS Y PORTADA (MODIFICAR INTEGRANTES ANTES DE ENVIAR)
# ==============================================================================
INTEGRANTES = [
    {"nombre": "Juan Carlos Escobar Gil", "documento": "1033649534"},
]

TITULO_PROYECTO = (
    f"Sistema de Visión Artificial para Clasificación de Esmeraldas Colombianas "
    f"({CLASE_0_NOMBRE} vs. {CLASE_1_NOMBRE}) en Valoración Gemológica Asistida (CIGEM)"
)
ASIGNATURA = "Introducción a la Visión Artificial"
DOCENTE = "Paula Alejandra Ortiz Santana"
GRUPO = "190202024-4"
FECHA = "26 de noviembre de 2026"
INSTITUCION = "Instituto Tecnológico Metropolitano — ITM"
CORREO_DOCENTE = "paulaortiz4523@correo.itm.edu.co"

# ==============================================================================
# 3. RUTAS DEL PROYECTO (RELATIVAS AL DIRECTORIO RAÍZ — NO HARDCODEAR)
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent
FOTOS_PROPIAS_DIR = BASE_DIR / "fotos_propias"
SCRAPING_RAW_DIR = BASE_DIR / "_cache_scraping"
DATASET_DIR = BASE_DIR / "dataset"
DATASET_CSV = DATASET_DIR / "dataset_origen.csv"

RESULTADOS_DIR = BASE_DIR / "resultados"
FIGURAS_DIR = RESULTADOS_DIR / "figuras"
CARACTERISTICAS_CSV = RESULTADOS_DIR / "caracteristicas.csv"
METRICAS_JSON = RESULTADOS_DIR / "metricas.json"
CURACION_LOG_JSON = RESULTADOS_DIR / "curacion_log.json"

NOTEBOOK_PATH = BASE_DIR / "entrega4_vision_artificial.ipynb"
INFORME_PDF = BASE_DIR / "Informe_Entrega4.pdf"

# ==============================================================================
# 4. PARÁMETROS DEL PIPELINE DE SCRAPING, CURACIÓN Y VISIÓN ARTIFICIAL
# ==============================================================================
USER_AGENT = (
    "ITM-VisionArtificial-Entrega4/1.0 "
    "(Proyecto academico CIGEM Grupo 190202024-4; contacto: estudiante@correo.itm.edu.co)"
)
SLEEP_ENTRE_PETICIONES = 0.5        # Segundos de pausa ética entre peticiones HTTP
MIN_PROPIAS_RECOMENDADAS = 40       # Mínimo exigido por la guía por clase
MIN_TOTAL_POR_CLASE = 150           # Mínimo exigido por la guía (propias + scraping)
OBJETIVO_DESCARGA_POR_CLASE = 180   # Margen de descarga para absorber descartes en curación
MIN_RESOLUCION_PX = 150             # Resolución mínima (ancho y alto >= 150 px)
DHASH_DISTANCIA_MAX = 6             # Distancia de Hamming <= 6 para casi-duplicados (64 bits)

IMG_SIZE = 256                      # Tamaño estándar de entrada al pipeline (256x256)
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)
GAUSSIAN_KSIZE = (5, 5)
GAUSSIAN_SIGMA = 1.0
MORPH_OPEN_KSIZE = (5, 5)
MORPH_CLOSE_KSIZE = (11, 11)

TEST_SIZE = 0.30                    # División 70% entrenamiento / 30% prueba
RANDOM_STATE = 42
KNN_K_VALUES = [1, 3, 5, 7, 9, 11]
SVM_C_VALUES = [0.1, 1.0, 10.0]

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
