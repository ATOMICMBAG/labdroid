# Audio and Visio Labdroid Backend (MVP Phase A)

Dieses Backend ist der **erste lauffähige MVP-Schritt** für das Labdroid-System:

- FastAPI + WebSocket Ingestion
- Async Queue + Worker
- deterministische Inspection-Pipeline
- Report-System (JSON + Markdown + Evidence)
- Timing-Telemetrie pro Pipeline-Stufe (`timings` im Job-Result + Report)
- Statistik-Endpoints (Summary, Histogram, Timeseries)
- Provider-Abstraktion (LiteRT, Ollama, OpenRouter) mit Runtime-Switching

## Struktur (Kurz)

```text
app/
  api/         # REST + WS Endpunkte
  core/        # Config, Security, Rate Limit
  models/      # Pydantic Modelle
  pipeline/    # Deterministische Analyse
  processing/  # Queue + Worker + Timeout
  providers/   # Model Provider Layer
  reporting/   # JSON/MD/Evidence Speicherung
  stats/       # Statistik-Berechnungen
  main.py      # App-Factory + Startup/Lifespan
```

## Installation

Im Ordner `labdroid/backend`:

```bash
uv sync
```

Alternativ mit pip:

```bash
pip install -e .
```

## Start

```bash
uv run python -m app.main
```

Healthcheck:

```bash
curl http://localhost:8000/health
```

## Setup-Companion (empfohlen)

Für ungeübte User gibt es jetzt einen Setup-Assistenten:

```bash
python labdroid/backend/setup_companion.py status --profile auto
```

Er prüft u. a.:

- Python-Version
- Backend-Module
- Ollama CLI/Server/Modell (lokal)
- OpenRouter API-Key (online)

### Env-Profil erzeugen

Lokales Profil (Ollama):

```bash
python labdroid/backend/setup_companion.py write-env --profile local --output labdroid/backend/.env.local
```

Online-Profil (OpenRouter):

```bash
python labdroid/backend/setup_companion.py write-env --profile online --output labdroid/backend/.env.online
```

Danach Backend mit Profil starten (Beispiel):

```bash
python -m uvicorn app.main:app --app-dir labdroid/backend --host 0.0.0.0 --port 8000 --env-file labdroid/backend/.env.local
```

## Wichtige Endpunkte

### Jobs

- `POST /jobs/start`
- `POST /jobs/provider/select`
- `GET /jobs/provider/current`
- `POST /jobs/{job_id}/replay`

### Reports

- `GET /reports/{job_id}`
- `GET /reports/{job_id}/markdown`

### Statistik

- `GET /stats/summary`
- `GET /stats/histogram?metric=brightness_mean`
- `GET /stats/timeseries?metric=audio_rms`

### WebSocket

- `GET /ws`

### Control (Ausbaustufen)

- `POST /control/actuator/fire`
- `GET /control/actuator/audit`
- `GET /control/baseline?domain=<name>&device_id=<id>`
- `POST /control/baseline/update`
- `POST /control/baseline/reset`
- `GET /control/plugins`
- `POST /control/plugins/reload`
- `POST /control/plugins/run`

Nachrichtenformat:

```json
{
  "type": "inspect",
  "payload": {
    "domain": "pcb",
    "text": "Bitte Inspektion starten",
    "image_b64": null,
    "audio_b64": null
  }
}
```

## Deterministische Entscheidung

Die eigentliche Entscheidung `OK/NOK` kommt aus:

`Input -> Preprocess -> Features -> Rule Engine -> Decision`

LLM-Provider werden nur für Erklärtext verwendet.

## Konfiguration (Env, optional)

- `LABDROID_BASE_DIR`
- `LABDROID_DATA_DIR`
- `LABDROID_REPORTS_DIR`
- `LABDROID_EVIDENCE_DIR`
- `LABDROID_DEFAULT_PROVIDER` (z. B. `litert`, `ollama`, `openrouter`)
- `LABDROID_PROVIDER_ALLOWLIST` (CSV)
- `LABDROID_MODEL_TIMEOUT_S`
- `LABDROID_WS_RATE_LIMIT_PER_MINUTE`
- `LABDROID_OLLAMA_BASE_URL`
- `LABDROID_OLLAMA_DEFAULT_MODEL`
- `LABDROID_OPENROUTER_BASE_URL`
- `LABDROID_OPENROUTER_DEFAULT_MODEL`
- `OPENROUTER_API_KEY`

### Baseline / Plugins / Safety / HW-Vorbereitung

- `LABDROID_BASELINE_FILE` (Default: `data/baselines.json`)
- `LABDROID_BASELINE_MIN_SAMPLES` (Default: `10`)
- `LABDROID_PLUGIN_DIR` (Default: `plugins`)
- `LABDROID_ACTUATOR_SIMULATION_DEFAULT` (Default: `true`)
- `LABDROID_ACTUATOR_COOLDOWN_S` (Default: `5`)
- `LABDROID_ACTUATOR_HTTP_ALLOWLIST` (CSV, Default: `localhost,127.0.0.1`)
- `LABDROID_ACTUATOR_REQUEST_TIMEOUT_S` (Default: `5`)
- `LABDROID_MQTT_ENABLED` (Default: `false`)
- `LABDROID_MQTT_BROKER` (Default: `localhost`)
- `LABDROID_MQTT_TOPIC_PREFIX` (Default: `labdroid`)
- `LABDROID_AUDIT_LOG_FILE` (Default: `reports/actuator_audit.log`)

## Hardware-Test-Preparation (sicherer Ablauf)

1. **Simulation aktiv lassen** (`LABDROID_ACTUATOR_SIMULATION_DEFAULT=true`)
2. HTTP-Actuator erst gegen lokale Mock-Endpoints testen
3. MQTT zuerst mit Test-Broker (lab-intern) und isoliertem Topic-Prefix testen
4. Für reale Aktuation:
   - `require_confirmation=true`
   - Cooldown > 0 beibehalten
   - Audit-Logs prüfen (`/control/actuator/audit`)
5. Erst danach Simulation pro Command deaktivieren

## Hinweis zum aktuellen Stand

Phase A liefert einen stabilen Grundkern. Nächste Schritte sind u. a.:

- reale LiteRT-Anbindung (statt Stub-Response)
- Frontend Dashboard + Audio/Video Controls
- Safety Layer + Actuator-System
