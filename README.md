# Entrega 4: Descriptores y Clasificación — Introducción a la Visión Artificial

**Asignatura:** Introducción a la Visión Artificial (Grupo `190202024-4`)  
**Docente:** Paula Alejandra Ortiz Santana · **Fecha límite:** 26 de noviembre de 2026 (11:59 p. m.)

---

## 1. Estructura del proyecto

```text
├── config.py                           # Configuración centralizada (MODIFICAR ANTES DE EJECUTAR)
├── requirements.txt                    # Dependencias Python
├── scraping_y_curacion.py              # Web scraping ético (Wikimedia Commons) + curación dHash
├── entrega4_vision_artificial.ipynb    # Pipeline completo automático (sin CNN ni IA preentrenada)
├── generar_informe.py                  # Compilador de Informe_Entrega4.pdf (<= 10 págs cuerpo)
├── empaquetar_entrega.py               # Empaquetador .zip + verificación del límite de 20 MB
├── fotos_propias/
│   ├── <CLASE_0>/                      # Mínimo 40 fotos propias (al menos 5 con apellidos a mano)
│   └── <CLASE_1>/                      # Mínimo 40 fotos propias (al menos 5 con apellidos a mano)
├── dataset/                            # Generado automáticamente + dataset_origen.csv
└── resultados/                         # caracteristicas.csv, metricas.json, curacion_log.json y figuras/
```

---

## 2. Pasos antes de ejecutar

1. **Instalar Python 3.10+ y dependencias:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. **Editar `config.py`:**
   - Ajusta `CLASE_0`, `CLASE_1`, sus nombres legibles y `TERMINOS_SCRAPING_0` / `TERMINOS_SCRAPING_1` (configurado por defecto para esmeraldas CIGEM: `esmeralda_suelta` vs. `esmeralda_montada`).
   - Completa `INTEGRANTES` con los nombres completos y documentos de identidad del grupo.
3. **Colocar las fotos propias:**
   - Copia mínimo **40 fotos propias** en `fotos_propias/<CLASE_0>/` y **40 fotos propias** en `fotos_propias/<CLASE_1>/`.
   - Recuerda incluir al menos **5 fotos por clase** con un papel escrito a mano con los apellidos del grupo (requisito de autoría de la guía) y variar fondos, luz, ángulo y distancia.

---

## 3. Ejecución completa del pipeline

```powershell
# 1. Descargar por web scraping ético, curar y generar dataset/dataset_origen.csv
python scraping_y_curacion.py

# 2. Ejecutar el notebook completo guardando todas las salidas visibles y figuras
jupyter nbconvert --to notebook --execute --inplace entrega4_vision_artificial.ipynb

# 3. Compilar el informe académico en PDF (verifica automáticamente <= 10 págs de cuerpo)
python generar_informe.py

# 4. Empaquetar la entrega en .zip y comprobar si supera los 20 MB
python empaquetar_entrega.py
```
