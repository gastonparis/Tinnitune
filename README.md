# Tinnitune — Tinnitus Sound Generator (CSIC Protocol / Cobo et al.)

Desktop application written in Python / PySide6 for hearing loss evaluation, clinical audiogram visualization, and personalized acoustic therapy synthesis (**Enriched Acoustic Environment — EAE**), based on the peer-reviewed clinical research by **María Cuesta, Christiam Garzón, and Pedro Cobo** (CSIC, 2022 / *Brain Sciences*, 12, 82).

---

## Key Features

1. **Clinical Audiometry Input & Management:**
   * Grid input for the **11 standard clinical frequencies** analyzed in the study: `125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, and 8000 Hz`.
   * Independent thresholds for **Left Ear (L)** and **Right Ear (R)** ranging from $-10\text{ dB}$ to $110\text{ dB HL}$.
   * Quick-load presets: *Normal Hearing (0 dB)*, *High-Frequency Notch (Typical 4k loss)*, and *Presbycusis*.
   * Save and load audiometric profiles in portable JSON files.

2. **Interactive Clinical Audiogram:**
   * International clinical audiology standard: **Right Ear in red (`O`)**, **Left Ear in blue (`X`)**.
   * Inverted Y-axis (better hearing thresholds at the top, hearing loss downwards) and logarithmic frequency X-axis.
   * Real-time smooth PCHIP spectral interpolation.

3. **1000 Hz Calibration & Automatic Threshold Transfer:**
   * **Prior Audiometry Calibration:** Uses your known clinical threshold at **1000 Hz** (universal audiological anchor) to calibrate output volume on your specific computer and headphones.
   * **ISO 389-1 (RETSPL) Compensation:** Automatically models the physiological sensitivity curve of the human ear, translating digital attenuation (down to $-100\text{ dBFS}$) into estimated clinical thresholds in **dB HL**.
   * **Automatic Transfer:** A single click on *«📥 Transfer Value to Audiometry Table»* writes the calculated threshold directly to the table, redraws the chart, and auto-advances to the next frequency.

4. **DSP Synthesis Engine (Therapeutic Sound):**
   * **Colored Broadband Noise (Primary Study Stimulus):** Continuous stereo Gaussian noise shaped by a linear-phase FIR filter where the gain corresponds to $G(f) = 10^{\frac{\text{HL}(f)}{20}}$, selectively re-stimulating frequency areas affected by hearing loss.
   * **Sequential EAE Modes (Cobo et al., 2021):** Discrete acoustic pulses using *Tone-Burst* (symmetrical Hann window for hyperacusis), *Tone-Pip* (asymmetrical window for tonotopic reorganization), and *Gammatone* auditory filters.
   * Peak normalization at $-1.0\text{ dBFS}$ with smooth 5-second fade-ins and fade-outs to protect the ears.

5. **Real-Time Prelistening & "Mixing Point" Calibration:**
   * Continuous loop playback in headphones with master volume control to train patients on finding the **mixing point** (adjusting the sound level just below the perceived tinnitus loudness, as prescribed by Jastreboff's neurophysiological model).

6. **Mobile-Ready Audio Export:**
   * Direct export to high-fidelity **MP3 (320 kbps)** or uncompressed **WAV (16-bit PCM)**.
   * Daily session lengths: **60 minutes** (standard clinical dose: 1 hour/day over 4 months), 30 min, 15 min, or 1 min (test).
   * Background rendering (`QThread`) with progress bar and a button to open the destination folder directly.

---

## User Guide: 1000 Hz Calibration & Threshold Evaluation

If you have a previous clinical audiogram, you can calibrate your headphones and estimate your hearing thresholds across all frequencies:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Calibration with Prior Audiometry (at 1000 Hz)                      │
│    Ear: (•) Left (L)   ( ) Right (R)                                   │
│    Known clinical threshold at 1000 Hz: [ 15 dB HL ]                   │
│    1000 Hz Volume:  [═══════════●══════════] -65 dBFS                  │
│    [ ▶ Test 1000 Hz ]        [ ✓ Set Reference (Barely Audible) ]     │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. Frequency Evaluation & Automatic Assignment                         │
│    Frequency: [ 4000 Hz (4 kHz) ▼ ]       Ear: (•) Left  ( ) Right     │
│    Test Level:  [════════════════●═══] -25 dBFS                        │
│    Calculated Threshold (ISO 389): [  35 dB HL (LEFT)  ]               │
│                                                                        │
│    [ ▶ Listen Tone (1.5s) ]                                            │
│    [ 📥 Transfer Value to Audiometry Table ]  ◄── (Updates & advances) │
└────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Calibrate Reference Level (1000 Hz)
1. Select the ear to calibrate (*Left* or *Right*).
2. Enter the threshold from your medical report in **«Known clinical threshold at 1000 Hz»** (e.g., `15 dB HL`).
3. Move the slider and click **«▶ Test 1000 Hz»** until you locate the lowest volume where you can *just barely perceive* the tone.
4. Click **«✓ Set Reference (Barely Audible)»**. This anchors your soundcard and headphone sensitivity to your actual hearing level.

### Step 2: Evaluate Frequencies & Transfer
1. Select the frequency to test (e.g., 2000, 3000, 4000, 6000 Hz).
2. Adjust the test intensity and click **«▶ Listen Tone»** to find your hearing threshold.
3. Observe the calculated value in **«Calculated Threshold (ISO 389)»** (computed with the RETSPL physiological curve).
4. Click **«📥 Transfer Value to Audiometry Table»**:
   * The value is automatically written into the table.
   * The clinical audiogram chart updates immediately.
   * The frequency selector automatically moves to the next frequency.

---

## Installation & Requirements

Clone the repository and install the dependencies:

```bash
git clone https://github.com/gastonparis/Tinnitune.git
cd Tinnitune
pip install -r requirements.txt
```

### System Requirements
* Python 3.10 or higher
* `ffmpeg` (for high-quality MP3 encoding)
* Libraries: `PySide6`, `numpy`, `scipy`, `matplotlib`, `soundfile`, `pydub`

---

## How to Run the Application

Launch the application directly using the launcher script:

```bash
./run.sh
```

Or via Python:

```bash
python3 main.py
```

---

## Quality Control & Automated Tests

The application includes unit, spectral (FFT), and end-to-end integration tests:

```bash
# DSP Engine Tests (linear phase FIR, FFT spectral concordance, anti-clipping, exporter)
python3 tests/test_dsp.py

# End-to-End GUI & Background Worker Integration Tests
python3 tests/test_integration.py

# ISO 389-1 Calculation & Threshold Calibration Tests
python3 tests/test_calibration.py
```

---

## Scientific Reference

* Cuesta, M.; Garzón, C.; Cobo, P. *Efficacy of Sound Therapy for Tinnitus Using an Enriched Acoustic Environment with Hearing-Loss Matched Broadband Noise.* **Brain Sci. 2022, 12, 82.** https://doi.org/10.3390/brainsci12010082
* Cobo, P.; Cuesta, M.; De la Colina, C. *Customised enriched acoustic environment for sound therapy of tinnitus.* **Acta Acustica 2021, 5, 34.** https://doi.org/10.1051/aacus/2021028
