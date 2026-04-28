# Audio and Visio Labdroid

## 1) Zielbild
- Echtzeit-Ingestion (Audio + Bild)
- deterministischer Inspektionslogik (regelbasiert)
- LLM nur für Erklärung/Bedienung (nicht für Entscheidungen)
- Bericht, Statistik, Replay und sichere Aktorik

---

## 2) Leitprinzipien
1. **Entscheidungen deterministisch** (Rule Engine, Metriken, Schwellen)
2. **LLM als Sprach-/Erklärschicht** (keine Entscheidungsautorität)
3. **Provider-unabhängig** (LiteRT, Ollama, OpenRouter dynamisch umschaltbar)
4. **Sicher & auditierbar** (Safety Layer, Logs, Rate Limits, Pfadvalidierung)
5. **Modular statt monolithisch** (typed, testbar, austauschbare Module)

---

## 3) Ziel-Architektur

```text
Frontend SPA
  ├─ Live Audio/Video + Filter + ROI
  ├─ Dashboard (Histogramm / Timeseries / Filter)
  └─ Job/Provider/Actuator UI
        │
        ▼
FastAPI Backend
  ├─ WS Ingestion (/ws)
  ├─ REST API (/reports, /stats/*, /jobs/*)
  ├─ Async Queue + Worker
  ├─ Inspection Pipeline (deterministisch)
  ├─ Model Provider Layer (LiteRT/Ollama/OpenRouter)
  ├─ Report Store + Evidence Store
  ├─ Replay + Baseline + Anomaly
  └─ Actuator Layer + Safety Layer
```

---

## 4) Projektstruktur

```text
labdroid/
  backend/
    app/
      api/
        ws.py
        reports.py
        stats.py
        jobs.py
        actuators.py
      core/
        config.py
        logging.py
        security.py
        rate_limit.py
      models/
        schemas.py
        report_models.py
      providers/
        base.py
        litert_provider.py
        ollama_provider.py
        openrouter_provider.py
        registry.py
      pipeline/
        preprocess.py
        features_image.py
        features_audio.py
        rule_engine.py
        decision.py
        explain.py
      processing/
        queue.py
        worker.py
        timeout.py
      reporting/
        writer.py
        markdown.py
        replay.py
      stats/
        summary.py
        histogram.py
        timeseries.py
      actuators/
        safety_layer.py
        http_actuator.py
        mqtt_actuator.py
      plugins/
        base.py
        loader.py
      main.py
    tests/
  frontend/
    src/
      app.js
      ws-client.js
      audio-chain.js
      video-analysis.js
      dashboard.js
      provider-settings.js
      styles.css
      index.html
  data/
  reports/
  evidence/
```

---

## 5) Kernmodule und Verträge

## 5.1 Model Provider Layer

```python
class ModelProvider:
    async def generate(self, inputs: dict) -> dict:
        ...
```

Pflichtfelder für Provider-Response (vereinheitlicht):

- `text: str`
- `latency_ms: float`
- `provider: str`
- `model: str`
- `raw: dict`

**Runtime-Switching:**

- aktive Provider-Konfiguration in `registry.py`
- Umschalten via API (`POST /jobs/provider/select`) oder Job-Config
- Provider-Allowlist + Timeouts erzwingen

## 5.2 Deterministische Inspection Pipeline

```text
Input → Preprocessing → Feature Extraction → Rule Engine → Decision → Report
```

Beispiel-Metriken:

- Bild: `brightness_mean`, `edge_density`
- Audio: `audio_rms`

Entscheidungsregel (Beispiel):

- `NOK`, wenn ein kritischer Check fehlschlägt
- sonst `OK`, wenn alle Pflichtchecks im Toleranzbereich

## 5.3 Report-Vertrag

Pflichtfelder je Report:

- `job_id`, `timestamp`, `domain`, `result`, `confidence`
- `metrics`, `checks`, `evidence_refs`

Artefakte pro Job:

- `reports/<job_id>.json`
- `reports/<job_id>.md`
- `evidence/<job_id>/...`

---

## 6) API-Plan (MVP)

## 6.1 WebSocket

- `GET /ws`
  - Eingang: Audio/Image Frames + Job-Metadaten
  - Ausgang: Zwischenstatus, Erklärtext, Job-Fortschritt

## 6.2 REST

- `GET /stats/summary`
- `GET /stats/histogram?metric=<name>`
- `GET /stats/timeseries?metric=<name>`
- `GET /reports/{job_id}`
- `GET /reports/{job_id}/markdown`
- `POST /jobs/start`
- `POST /jobs/{job_id}/replay`
- `POST /jobs/provider/select`

---

## 7) Sicherheit & Stabilität

## 7.1 Security

- Pfadvalidierung gegen Path Traversal
- Provider-Allowlist
- Request-/Inference-/TTS-Timeouts
- WS Rate Limiting pro Client

## 7.2 Stability

- Async Queue zwischen WS und Worker
- Graceful Fallback bei Provider-/TTS-Fehlern
- saubere Fehlercodes + Audit-Logs

---

## 8) Frontend-Plan

## 8.1 Statistik-Dashboard

- Histogramm (numpy-basiert aus Backend-Daten)
- Zeitreihe
- Filter: Domain, Datum, Device

## 8.2 Audio-Processing-UI (Web Audio API)

Kette:

`Mic -> GainNode -> 3x BiquadFilterNode -> DynamicsCompressorNode -> Output`

Steuerungen:

- Gain
- EQ Low/Mid/High
- Compressor Threshold

## 8.3 Video-Processing-UI

- Live `<video>` Preview + CSS-Filter
- Canvas-Analyse auf `ImageData`
- Controls: Brightness, Contrast, Saturation, ROI

---

## 9) Erweiterte Features (nach MVP)

1. Replay-System (Vergangenes Job-Reload)
2. Baseline-Vergleich
3. Anomaly Detection (`mean ± 2*std`)
4. Plugin-System

```python
class InspectionPlugin:
    def run(input_data):
        ...
```

---

## 10) Implementierung

## Phase A — Minimal Working Prototype

1. FastAPI Grundgerüst (WS + REST)
2. Async Queue + Worker
3. Deterministische Pipeline mit 3 Kernmetriken
4. JSON + Markdown Reports + Evidence-Speicherung
5. Ein Provider zuerst (LiteRT **oder** Ollama lokal)

**Abnahme A:** End-to-End Job läuft, Report entsteht, Stats-Endpoint liefert Daten.

## Phase B — Provider-Flexibilität

1. Provider-Abstraktion finalisieren
2. Ollama + OpenRouter Adapter ergänzen
3. Runtime-Switching + Allowlist + Timeouts

**Abnahme B:** Provider kann pro Job umgeschaltet werden, gleiche Pipeline bleibt intakt.

## Phase C — Dashboard + Medienkontrollen

1. Statistik-Dashboard
2. Audio-Kette mit Controls
3. Video-Filter + ROI

**Abnahme C:** Bedienbare UI für Analyse + Metrikvisualisierung vorhanden.

## Phase D — Safety + Actuators + Replay

1. Safety Layer (Confirm, Cooldown, Simulation, Audit)
2. HTTP/MQTT Aktorik
3. Replay + Baseline + einfache Anomalieerkennung

**Abnahme D:** Sicherer Betriebsmodus inkl. Nachvollziehbarkeit.

---

## 11) Definition of Done (DoD)

- Architektur modular, typed, kein Monolith
- Deterministische Entscheidungskette aktiv
- LLM nur für Erklärtext
- Reports vollständig inkl. Evidenz-Referenzen
- Statistik-Endpoints liefern valide Daten (inkl. Histogramm)
- Sicherheitsanforderungen umgesetzt
- Runtime-Providerwechsel funktioniert stabil

---

---

## MB

# Companion: python labdroid/backend/setup_companion.py status --profile auto

# backend: python -m uvicorn app.main:app --app-dir labdroid/backend --host 0.0.0.0 --port 8000

# frontend: python -m http.server 5500 --directory labdroid/frontend

# parser: http://localhost:5500/
