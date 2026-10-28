# Generador de Sonido Terapéutico para Tinnitus (Protocolo CSIC / Cobo et al.)

Aplicación de escritorio en Python / PySide6 para la evaluación de pérdida auditiva, visualización de audiogramas clínicos y síntesis de estímulos sonoros personalizados (*Entorno Acústico Enriquecido - EAE*) según el protocolo de investigación de **María Cuesta, Christiam Garzón y Pedro Cobo** (CSIC, 2022 / *Brain Sciences*, 12, 82).

---

## Características Principales

1. **Ingreso y Edición de Audiometría Clínica:**
   - Tabla con las 11 frecuencias estándar analizadas en el estudio: `125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000 y 8000 Hz`.
   - Control independiente para Oído Izquierdo (L) y Oído Derecho (R) en decibelios ($-10$ a $110\text{ dB HL}$).
   - Presets de carga rápida: *Normal (0 dB)*, *Caída en Agudos (Muesca típica en 4k)* y *Presbiacusia*.
   - Guardado y carga de audiometrías en archivos JSON.

2. **Audiograma Clínico Interactivo:**
   - Visualización estandarizada internacional: Oído Derecho en **rojo** (`O`), Oído Izquierdo en **azul** (`X`).
   - Eje Y invertido (mejores umbrales arriba, mayor hipoacusia abajo) y escala logarítmica de frecuencias.
   - Interpolación espectral suave PCHIP en tiempo real.

3. **Módulo de Evaluación y Calibración a 1000 Hz con Traspaso Automático:**
   - **Calibración con audiometría previa:** Permite fijar el umbral clínico conocido en **1000 Hz** (anclaje universal) y ajustar el volumen digital donde apenas se percibe el tono con los auriculares en uso.
   - **Compensación ISO 389-1 (RETSPL):** Modela la sensibilidad fisiológica del oído humano para convertir la atenuación digital en umbrales clínicos estimados en **dB HL**.
   - **Traspaso Automático:** Con un solo clic, asigna el umbral calculado directamente a la tabla de audiometría, redibuja el gráfico y avanza a la siguiente frecuencia.

4. **Motor DSP de Síntesis Terapéutica:**
   - **Ruido de Banda Ancha Coloreado:** Ruido blanco filtrado estéreo con filtro FIR de fase lineal donde la ganancia responde a $G(f) = 10^{\frac{HL(f)}{20}}$.
   - **Modos Secuenciales EAE:** Pulsos acústicos con ventanas *Tone-Burst*, *Tone-Pip* y *Gammatone*.
   - Normalización de picos a $-1.0\text{ dBFS}$ y desvanecimientos suaves (*fade-in* y *fade-out* de 5 segundos).

5. **Preescucha y Calibración del "Mixing Point":**
   - Reproducción estéreo en tiempo real en bucle con control de volumen para que el paciente ajuste el nivel en sus auriculares justo por debajo de su acúfeno (*punto de mezcla* de Jastreboff).

6. **Exportación para Teléfono Celular:**
   - Exportación a **MP3 de 320 kbps** (ideal para reproducir en celulares Android e iOS) o **WAV sin compresión**.
   - Opciones de duración: **60 minutos** (dosis diaria recomendada de 1 hora al día), 30 min, 15 min o 1 min (prueba).
   - Generación en segundo plano (`QThread`) con barra de progreso y botón para abrir directamente la carpeta de destino.

---

## Guía de Uso: Calibración a 1000 Hz y Evaluación Audiométrica

Si cuentas con una audiometría clínica previa, puedes calibrar tus auriculares en la computadora y evaluar todas las demás frecuencias de forma precisa:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Calibración con Audiometría Previa (a 1000 Hz)                      │
│    Oído: (•) Izquierdo (L)   ( ) Derecho (R)                          │
│    Mi umbral clínico en 1000 Hz: [ 15 dB HL ]                          │
│    Volumen 1000 Hz:  [═══════════●══════════] -65 dBFS                 │
│    [ ▶ Probar 1000 Hz ]     [ ✓ Fijar Referencia (Apenas Oigo) ]      │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. Evaluación de Frecuencia y Asignación Automática                    │
│    Frecuencia: [ 4000 Hz (4 kHz) ▼ ]    Oído: (•) Izq (L)  ( ) Der (R) │
│    Intensidad: [════════════════●═══] -25 dBFS                         │
│    Umbral Calculado (ISO 389): [  35 dB HL (LEFT)  ]                   │
│                                                                        │
│    [ ▶ Escuchar Tono (1.5s) ]                                          │
│    [ 📥 Pasar Valor a Tabla de Audiometría ]  ◄── (Actualiza y avanza) │
└────────────────────────────────────────────────────────────────────────┘
```

### Paso 1: Calibrar el punto de referencia (1000 Hz)
1. Selecciona el oído a calibrar (*Izquierdo* o *Derecho*).
2. Ingresa en la casilla **«Mi umbral clínico a 1000 Hz»** el valor en dB HL que figura en tu estudio médico (ej. `15 dB HL`).
3. Mueve el control de volumen de 1000 Hz y pulsa **«▶ Probar 1000 Hz»** hasta situarte en el volumen más bajo donde apenas comienzas a percibir el tono.
4. Pulsa **«✓ Fijar Referencia (Apenas Oigo)»**. Esto establece la correspondencia exacta entre la tarjeta de sonido, tus auriculares y tu nivel auditivo real.

### Paso 2: Evaluar frecuencias y traspasar valores
1. Selecciona la frecuencia a medir (ej. 2000, 3000, 4000, 6000 Hz).
2. Mueve el control deslizante y pulsa **«▶ Escuchar Tono»** para localizar tu umbral de escucha.
3. Observa el valor en el recuadro **«Umbral Calculado (ISO 389)»** (calculado aplicando la corrección estándar de sensibilidad humana RETSPL).
4. Haz clic en **«📥 Pasar Valor a Tabla de Audiometría»**:
   - El valor en dB HL se escribe automáticamente en la tabla.
   - El audiograma clínico superior se redibuja en el acto.
   - El selector de frecuencia avanza automáticamente a la siguiente para agilizar la prueba.

---

## Cómo Ejecutar la Aplicación

Para iniciar la aplicación desde la terminal:

```bash
./run.sh
```

O directamente con Python:

```bash
python3 main.py
```

---

## Ejecución de Pruebas de Calidad

La aplicación incluye un conjunto completo de pruebas unitarias, espectrales (FFT) y de integración:

```bash
# Pruebas del motor DSP (fase lineal, FFT, anti-clipping y exportador)
python3 tests/test_dsp.py

# Pruebas de integración de la interfaz y renderizado en segundo plano
python3 tests/test_integration.py

# Pruebas de cálculo ISO 389 y traspaso de calibración
python3 tests/test_calibration.py
```
