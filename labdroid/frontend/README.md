# Labdroid Frontend (MVP)

Dieses Frontend ist der erste lauffähige UI-Schritt für das bestehende Backend.

## Features

- Job starten (Domain, Device, Prompt)
- Provider auswählen (litert / ollama / openrouter)
- WebSocket-Client mit REST-Fallback
- Kamera-Preview mit ROI-Auswahl und Video-Filtern (Brightness/Contrast/Saturation)
- Kamera EIN/AUS über Toggle-Button
- Kamera-Presets (P1..P5): Klick = laden, Doppelklick = speichern
- Kamera-Geräteauswahl (Checkbox-basiert, Single-Select)
- Mikrofon-Geräteauswahl (Checkbox-basiert, Single-Select)
- Audio-Kette (Gain + 3-Band EQ + Compressor) und 5s Audio-Aufnahme
- Mikrofon EIN/AUS über Toggle-Button
- Hilfe-Buttons (`?`) mit verzögertem Hover-Tooltip (~1s)
- Audio-Monitoring mit umschaltbaren Ansichten:
  - Spektrum
  - Wasserfall
  - Phase
  - RMS-Level-Anzeige
- Setup-Assistenz im Job-Panel:
  - **Lokal setup laden** (Ollama + `gemma4:e4b`)
  - **Online setup laden** (OpenRouter + Beispielmodell)
- UI-Design an DroneScope angenähert:
  - helle Grau-Palette (Foreground/Background)
  - kleine Radiuswerte
  - einklappbare Panels (Accordion)
- Statistik-Dashboard:
  - Summary
  - Histogramm
  - Timeseries
- Control-Bereich:
  - Baseline laden/resetten
  - Plugins reload/run
  - Safe Actuator Fire (HTTP/MQTT, standardmäßig Simulation)
  - Audit-Logs laden

## Dateien

```text
frontend/
  index.html
  src/
    app.js
    api.js
    ws-client.js
    charts.js
    video-analysis.js
    audio-chain.js
    ui.js
    styles.css
```

## Start (einfach)

1. Backend starten

```bash
python -m uvicorn app.main:app --app-dir labdroid/backend --host 0.0.0.0 --port 8000
```

2. Frontend als statische Datei öffnen

```bash
start labdroid/frontend/index.html
```

> Hinweis: Für Kamera/Mikrofon ist ein lokaler HTTP-Server oft robuster als `file://`.

## Start (empfohlen mit statischem Server)

```bash
python -m http.server 5500 --directory labdroid/frontend
```

Dann im Browser öffnen:

- http://localhost:5500

## Backend-URL

Im Footer des Frontends kann die Backend-Base-URL angepasst werden (Standard: `http://localhost:8000`).

## UI Bedienung

- Panels sind einklappbar (Klick auf den Panel-Header).
- Die Abschnitte "Statistics" und "Control" starten eingeklappt.
- Für Hardware-Tests zuerst Geräte laden, dann gezielt Kamera/Mikrofon auswählen.
- Die Buttons "Kamera starten" / "Mikrofon starten" sind Toggle-Buttons (Start/Stop).
- Kamera-Presets speichern/laden:
  - Klick auf `P1..P5` lädt ein Preset
  - Doppelklick auf `P1..P5` speichert aktuelle Filterwerte
- Hilfe-Buttons `?` zeigen nach ca. 1s Mouseover einen kurzen Hilfetext.

## LLM Setup (einfach)

### Lokal (Ollama)

1. Im Job-Panel auf **Lokal setup laden** klicken
2. Danach **Provider setzen** klicken
3. Falls Modell fehlt: `ollama pull gemma4:e4b`

### Online (OpenRouter)

1. Im Backend `OPENROUTER_API_KEY` setzen
2. Im Job-Panel **Online setup laden** klicken
3. Danach **Provider setzen** klicken

## Report-Metadaten

Beim Job-Start werden zusätzliche Metadaten mitgesendet (u. a.):

- Setup-Modus (manual/local/online)
- gewählter Provider/Modell
- aktive Kamera-/Mikro-Geräte
- aktuelle Kamera-Filter und aktives Preset
- aktuelle Audio-Chain-Werte und Monitor-Modus

## Hardware-nahe Tests (sicher)

Empfohlener Ablauf:

1. Zuerst **Geräte laden** und gewünschte Kamera / Mikrofon auswählen
2. Kamera/Mikrofon starten und Monitoring im Frontend prüfen (Bild + Audio-Visualisierung)
3. Erst mit `simulation=true` testen (im UI bereits voreingestellt)
4. HTTP nur gegen lokale/staging Endpunkte auf Allowlist testen
5. MQTT zunächst mit Test-Broker und nicht-kritischen Topics testen
6. Vor realer Aktuation:
   - Confirmation Token aktiv nutzen (`CONFIRM`)
   - Cooldown nicht auf 0 setzen
   - Audit-Log nach jedem Test prüfen
