import {
  controlActuatorFire,
  controlGetBaseline,
  controlLoadAudit,
  controlReloadPlugins,
  controlResetBaseline,
  controlRunPlugins,
  getHistogram,
  getSummary,
  getTimeseries,
  normalizeBaseUrl,
  pingHealth,
  setProviderRest,
  startJobRest,
} from "./api.js";
import { AudioChain } from "./audio-chain.js";
import { drawHistogram, drawTimeseries } from "./charts.js";
import { setBackendStatus, setJsonView, $, pretty } from "./ui.js";
import { VideoAnalysis } from "./video-analysis.js";
import { WsClient } from "./ws-client.js";

const el = {
  backendBase: $("backendBase"),
  backendStatus: $("backendStatus"),
  pingBtn: $("pingBtn"),

  domain: $("domainSelect"),
  device: $("deviceInput"),
  text: $("textInput"),
  provider: $("providerSelect"),
  model: $("modelInput"),
  localSetupBtn: $("localSetupBtn"),
  onlineSetupBtn: $("onlineSetupBtn"),
  setupHint: $("setupHint"),
  setProviderBtn: $("setProviderBtn"),
  runJobBtn: $("runJobBtn"),
  jobResult: $("jobResult"),

  cameraBtn: $("cameraBtn"),
  loadCameraDevicesBtn: $("loadCameraDevicesBtn"),
  cameraDeviceList: $("cameraDeviceList"),
  captureBtn: $("captureBtn"),
  video: $("video"),
  roiCanvas: $("roiCanvas"),
  brightness: $("brightness"),
  contrast: $("contrast"),
  saturation: $("saturation"),
  cameraPresetRow: $("cameraPresetRow"),

  audioBtn: $("audioBtn"),
  loadMicDevicesBtn: $("loadMicDevicesBtn"),
  micDeviceList: $("micDeviceList"),
  recordBtn: $("recordBtn"),
  audioViewMode: $("audioViewMode"),
  audioMonitorCanvas: $("audioMonitorCanvas"),
  audioLevel: $("audioLevel"),
  gain: $("gain"),
  threshold: $("threshold"),
  eqLow: $("eqLow"),
  eqMid: $("eqMid"),
  eqHigh: $("eqHigh"),

  metric: $("metricSelect"),
  filterDomain: $("filterDomain"),
  filterDevice: $("filterDevice"),
  bins: $("binsInput"),
  refreshStatsBtn: $("refreshStatsBtn"),
  summaryView: $("summaryView"),
  histogramView: $("histogramView"),
  timeseriesView: $("timeseriesView"),
  histogramCanvas: $("histogramCanvas"),
  timeseriesCanvas: $("timeseriesCanvas"),

  baselineDomain: $("baselineDomain"),
  baselineDevice: $("baselineDevice"),
  baselineGetBtn: $("baselineGetBtn"),
  baselineResetBtn: $("baselineResetBtn"),
  pluginsReloadBtn: $("pluginsReloadBtn"),
  pluginsRunBtn: $("pluginsRunBtn"),
  actuatorType: $("actuatorType"),
  actuatorTarget: $("actuatorTarget"),
  actuatorPayload: $("actuatorPayload"),
  actuatorFireBtn: $("actuatorFireBtn"),
  auditLoadBtn: $("auditLoadBtn"),
  baselineView: $("baselineView"),
  pluginsView: $("pluginsView"),
  actuatorView: $("actuatorView"),
};

const state = {
  baseUrl: normalizeBaseUrl(el.backendBase.value),
  latestImageB64: null,
  latestAudioB64: null,
  selectedCameraIds: [],
  selectedMicIds: [],
  cameraActive: false,
  audioActive: false,
  cameraInfo: null,
  audioInfo: null,
  setupMode: "manual",
  cameraPresets: {},
  activeCameraPreset: null,
};

const CAMERA_PRESET_STORAGE_KEY = "labdroid.camera.presets.v1";

const toNumber = (value, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const getCameraFilterSettings = () => ({
  brightness: toNumber(el.brightness?.value, 100),
  contrast: toNumber(el.contrast?.value, 100),
  saturation: toNumber(el.saturation?.value, 100),
});

const getAudioChainSettings = () => ({
  gain: toNumber(el.gain?.value, 1),
  threshold: toNumber(el.threshold?.value, -24),
  eq_low: toNumber(el.eqLow?.value, 1),
  eq_mid: toNumber(el.eqMid?.value, 1),
  eq_high: toNumber(el.eqHigh?.value, 1),
  monitor_mode: el.audioViewMode?.value || "spectrum",
});

const resolveDeviceId = () => {
  const typed = el.device.value.trim();
  if (typed) return typed;
  return state.selectedCameraIds[0] || state.selectedMicIds[0] || null;
};

const updateCameraButtonUi = () => {
  if (!el.cameraBtn) return;
  el.cameraBtn.textContent =
    state.cameraActive ? "Kamera stoppen" : "Kamera starten";
};

const updateAudioButtonUi = () => {
  if (!el.audioBtn) return;
  el.audioBtn.textContent =
    state.audioActive ? "Mikrofon stoppen" : "Mikrofon starten";
};

const setSetupHint = (text) => {
  if (!el.setupHint) return;
  el.setupHint.textContent = text;
};

const markSetupMode = (mode) => {
  state.setupMode = mode;
  if (mode === "local") {
    setSetupHint(
      "Lokal-Setup aktiv: ollama + gemma4:e4b. Prüfe lokal mit: ollama list / ggf. Modell zuerst laden.",
    );
  } else if (mode === "online") {
    setSetupHint(
      "Online-Setup aktiv: openrouter. Im Backend muss OPENROUTER_API_KEY gesetzt sein.",
    );
  } else {
    setSetupHint(
      "Manuelles Setup aktiv. Tipp: Lokal/Online Setup-Buttons nutzen.",
    );
  }
};

const loadCameraPresets = () => {
  try {
    const raw = localStorage.getItem(CAMERA_PRESET_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      state.cameraPresets = parsed;
    }
  } catch {
    state.cameraPresets = {};
  }
};

const persistCameraPresets = () => {
  try {
    localStorage.setItem(
      CAMERA_PRESET_STORAGE_KEY,
      JSON.stringify(state.cameraPresets),
    );
  } catch {
    // ignore quota/storage errors
  }
};

const renderCameraPresetButtons = () => {
  const buttons =
    el.cameraPresetRow?.querySelectorAll("[data-cam-preset]") || [];
  buttons.forEach((btn) => {
    const slot = btn.getAttribute("data-cam-preset");
    const hasPreset = Boolean(state.cameraPresets[slot]);
    btn.classList.toggle("has-preset", hasPreset);
    btn.classList.toggle("active", state.activeCameraPreset === slot);
  });
};

const applyCameraPreset = (slot) => {
  const preset = state.cameraPresets[slot];
  if (!preset) {
    setJsonView(el.jobResult, {
      info: `Kamera-Preset P${slot} ist leer. Doppelklick auf P${slot}, um aktuelle Werte zu speichern.`,
    });
    return;
  }

  el.brightness.value = String(toNumber(preset.brightness, 100));
  el.contrast.value = String(toNumber(preset.contrast, 100));
  el.saturation.value = String(toNumber(preset.saturation, 100));

  el.brightness.dispatchEvent(new Event("input", { bubbles: true }));
  state.activeCameraPreset = slot;
  renderCameraPresetButtons();

  setJsonView(el.jobResult, {
    info: `Kamera-Preset P${slot} geladen`,
    settings: getCameraFilterSettings(),
  });
};

const saveCameraPreset = (slot) => {
  state.cameraPresets[slot] = getCameraFilterSettings();
  state.activeCameraPreset = slot;
  persistCameraPresets();
  renderCameraPresetButtons();
  setJsonView(el.jobResult, {
    info: `Kamera-Preset P${slot} gespeichert`,
    settings: state.cameraPresets[slot],
  });
};

const bindCameraPresetActions = () => {
  const buttons =
    el.cameraPresetRow?.querySelectorAll("[data-cam-preset]") || [];
  buttons.forEach((btn) => {
    const slot = btn.getAttribute("data-cam-preset");
    btn.addEventListener("click", () => applyCameraPreset(slot));
    btn.addEventListener("dblclick", (event) => {
      event.preventDefault();
      saveCameraPreset(slot);
    });
  });
};

const initHelpTooltips = () => {
  const helpButtons = document.querySelectorAll(".help-btn[data-help]");
  if (!helpButtons.length) return;

  const tooltip = document.createElement("div");
  tooltip.className = "help-popover";
  document.body.appendChild(tooltip);

  let hoverTimer = null;

  const hide = () => {
    tooltip.classList.remove("visible");
    if (hoverTimer) {
      clearTimeout(hoverTimer);
      hoverTimer = null;
    }
  };

  const showFor = (btn) => {
    const text = btn.getAttribute("data-help") || "";
    tooltip.textContent = text;
    const rect = btn.getBoundingClientRect();
    tooltip.style.left = `${Math.max(8, rect.left + window.scrollX - 8)}px`;
    tooltip.style.top = `${rect.bottom + window.scrollY + 10}px`;
    tooltip.classList.add("visible");
  };

  helpButtons.forEach((btn) => {
    btn.addEventListener("mouseenter", () => {
      hoverTimer = setTimeout(() => showFor(btn), 1000);
    });
    btn.addEventListener("mouseleave", hide);
    btn.addEventListener("focus", () => showFor(btn));
    btn.addEventListener("blur", hide);
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      showFor(btn);
    });
  });

  document.addEventListener("scroll", hide, true);
  document.addEventListener("click", (event) => {
    if (
      !event.target.closest(".help-btn") &&
      !event.target.closest(".help-popover")
    ) {
      hide();
    }
  });
};

const video = new VideoAnalysis({
  videoEl: el.video,
  roiCanvas: el.roiCanvas,
  brightnessEl: el.brightness,
  contrastEl: el.contrast,
  saturationEl: el.saturation,
});

const audio = new AudioChain({
  gainEl: el.gain,
  thresholdEl: el.threshold,
  eqLowEl: el.eqLow,
  eqMidEl: el.eqMid,
  eqHighEl: el.eqHigh,
  monitorCanvasEl: el.audioMonitorCanvas,
  monitorModeEl: el.audioViewMode,
  audioLevelEl: el.audioLevel,
});

const ws = new WsClient({
  baseUrl: state.baseUrl,
  onStatus: (status) => {
    if (status === "open") {
      setBackendStatus(el.backendStatus, true, "Backend: WS verbunden");
    } else if (status === "closed") {
      setBackendStatus(el.backendStatus, false, "Backend: WS getrennt");
    } else {
      setBackendStatus(el.backendStatus, false, "Backend: WS Fehler");
    }
  },
  onMessage: (msg) => {
    if (msg?.type === "job_result") {
      setJsonView(el.jobResult, msg.payload);
    }
    if (msg?.type === "error") {
      setJsonView(el.jobResult, msg);
    }
  },
});

const getFilters = () => ({
  domain: el.filterDomain.value.trim(),
  device: el.filterDevice.value.trim(),
});

const deviceLabel = (dev, idx) => {
  const base = dev.label?.trim();
  if (base) return base;
  return `${dev.kind === "videoinput" ? "Kamera" : "Mikrofon"} ${idx + 1}`;
};

const renderDeviceList = ({
  container,
  devices,
  selectedIds,
  groupName,
  singleSelect = true,
  onChange,
}) => {
  if (!container) return;
  container.innerHTML = "";

  if (!devices?.length) {
    container.textContent = "Keine Geräte gefunden oder Berechtigung fehlt.";
    return;
  }

  devices.forEach((dev, idx) => {
    const row = document.createElement("label");
    row.className = "deviceItem";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.name = groupName;
    cb.value = dev.deviceId;
    cb.checked = selectedIds.includes(dev.deviceId);

    cb.addEventListener("change", () => {
      let next = [...selectedIds];
      if (singleSelect) {
        next = cb.checked ? [dev.deviceId] : [];
      } else {
        if (cb.checked) {
          if (!next.includes(dev.deviceId)) next.push(dev.deviceId);
        } else {
          next = next.filter((id) => id !== dev.deviceId);
        }
      }
      onChange(next);
    });

    const text = document.createElement("span");
    text.textContent = `${deviceLabel(dev, idx)} · ${dev.deviceId.slice(0, 12)}…`;

    row.appendChild(cb);
    row.appendChild(text);
    container.appendChild(row);
  });
};

const loadCameraDevices = async () => {
  const devices = await video.enumerateVideoDevices();
  const validSelected = state.selectedCameraIds.filter((id) =>
    devices.some((d) => d.deviceId === id),
  );
  if (!validSelected.length && devices.length) {
    validSelected.push(devices[0].deviceId);
  }
  state.selectedCameraIds = validSelected;
  video.setSelectedDeviceIds(state.selectedCameraIds);

  const render = () => {
    renderDeviceList({
      container: el.cameraDeviceList,
      devices,
      selectedIds: state.selectedCameraIds,
      groupName: "camera-device",
      singleSelect: true,
      onChange: (next) => {
        state.selectedCameraIds = next;
        video.setSelectedDeviceIds(next);
        render();
      },
    });
  };

  render();
};

const loadMicDevices = async () => {
  const devices = await audio.enumerateAudioDevices();
  const validSelected = state.selectedMicIds.filter((id) =>
    devices.some((d) => d.deviceId === id),
  );
  if (!validSelected.length && devices.length) {
    validSelected.push(devices[0].deviceId);
  }
  state.selectedMicIds = validSelected;
  audio.setSelectedDeviceIds(state.selectedMicIds);

  const render = () => {
    renderDeviceList({
      container: el.micDeviceList,
      devices,
      selectedIds: state.selectedMicIds,
      groupName: "mic-device",
      singleSelect: true,
      onChange: (next) => {
        state.selectedMicIds = next;
        audio.setSelectedDeviceIds(next);
        render();
      },
    });
  };

  render();
};

const refreshDashboard = async () => {
  const metric = el.metric.value;
  const bins = Math.max(3, Number(el.bins.value || 10));
  const filters = getFilters();

  const [summary, histogram, timeseries] = await Promise.all([
    getSummary(state.baseUrl, filters),
    getHistogram(state.baseUrl, metric, bins, filters),
    getTimeseries(state.baseUrl, metric, filters),
  ]);

  setJsonView(el.summaryView, summary);
  setJsonView(el.histogramView, histogram);
  setJsonView(el.timeseriesView, {
    metric: timeseries.metric,
    count: timeseries.count,
    points_preview: timeseries.points.slice(-10),
  });

  drawHistogram(el.histogramCanvas, histogram);
  drawTimeseries(el.timeseriesCanvas, timeseries);
};

const currentJobPayload = () => {
  const provider = el.provider.value;
  const model = el.model.value.trim() || null;

  return {
    domain: el.domain.value,
    device_id: resolveDeviceId(),
    text: el.text.value.trim() || null,
    provider,
    model,
    image_b64: state.latestImageB64,
    audio_b64: state.latestAudioB64,
    metadata: {
      frontend: "labdroid-frontend-mvp",
      setup_mode: state.setupMode,
      provider_selection: { provider, model },
      devices: {
        selected_camera_ids: [...state.selectedCameraIds],
        selected_mic_ids: [...state.selectedMicIds],
      },
      camera: {
        active: state.cameraActive,
        selected_device_id: state.cameraInfo?.selectedDeviceId || null,
        resolution:
          state.cameraInfo ?
            `${state.cameraInfo.width}x${state.cameraInfo.height}`
          : null,
        filters: getCameraFilterSettings(),
        active_preset: state.activeCameraPreset,
      },
      audio: {
        active: state.audioActive,
        selected_device_id: state.audioInfo?.selectedDeviceId || null,
        sample_rate: state.audioInfo?.sampleRate || null,
        chain: getAudioChainSettings(),
      },
      capture: {
        has_image: Boolean(state.latestImageB64),
        has_audio: Boolean(state.latestAudioB64),
      },
    },
  };
};

const runJob = async () => {
  const payload = currentJobPayload();
  try {
    const wsResp = await ws.request("inspect", payload);
    setJsonView(el.jobResult, wsResp.payload || wsResp);
  } catch {
    const restResp = await startJobRest(state.baseUrl, payload);
    setJsonView(el.jobResult, restResp);
  }
  await refreshDashboard();
};

const applyLocalSetupDefaults = () => {
  el.provider.value = "ollama";
  if (!el.model.value.trim()) {
    el.model.value = "gemma4:e4b";
  }
  markSetupMode("local");
  setJsonView(el.jobResult, {
    info: "Lokal-Setup gesetzt",
    provider: el.provider.value,
    model: el.model.value.trim() || null,
    hint: "Danach 'Provider setzen' klicken. Falls nötig: `ollama pull gemma4:e4b`.",
  });
};

const applyOnlineSetupDefaults = () => {
  el.provider.value = "openrouter";
  const currentModel = el.model.value.trim();
  if (!currentModel || currentModel === "gemma4:e4b") {
    el.model.value = "google/gemma-3-27b-it:free";
  }
  markSetupMode("online");
  setJsonView(el.jobResult, {
    info: "Online-Setup gesetzt",
    provider: el.provider.value,
    model: el.model.value.trim() || null,
    hint: "Im Backend muss OPENROUTER_API_KEY gesetzt sein. Danach 'Provider setzen'.",
  });
};

const setProvider = async () => {
  const provider = el.provider.value;
  const model = el.model.value.trim();

  const isLocal = provider === "ollama";
  const isOnline = provider === "openrouter";
  if (
    (state.setupMode === "local" && !isLocal) ||
    (state.setupMode === "online" && !isOnline)
  ) {
    markSetupMode("manual");
  }

  try {
    const wsResp = await ws.request("provider_select", { provider, model });
    setJsonView(el.jobResult, {
      provider_result: wsResp.payload || wsResp,
      setup_mode: state.setupMode,
    });
  } catch {
    const restResp = await setProviderRest(state.baseUrl, provider, model);
    setJsonView(el.jobResult, {
      provider_result: restResp,
      setup_mode: state.setupMode,
    });
  }
};

const toggleCamera = async () => {
  if (state.cameraActive) {
    video.stopCamera();
    state.cameraActive = false;
    state.cameraInfo = null;
    updateCameraButtonUi();
    setJsonView(el.jobResult, { camera: "inaktiv", info: "Kamera gestoppt" });
    return;
  }

  const info = await video.startCamera();
  state.cameraActive = true;
  state.cameraInfo = info;
  updateCameraButtonUi();
  setJsonView(el.jobResult, {
    camera: "aktiv",
    selectedDeviceId: info.selectedDeviceId,
    resolution: `${info.width}x${info.height}`,
  });
};

const toggleAudio = async () => {
  if (state.audioActive) {
    audio.stop();
    state.audioActive = false;
    state.audioInfo = null;
    updateAudioButtonUi();
    setJsonView(el.jobResult, { audio: "inaktiv", info: "Mikrofon gestoppt" });
    return;
  }

  const info = await audio.start();
  state.audioActive = true;
  state.audioInfo = info;
  updateAudioButtonUi();
  setJsonView(el.jobResult, {
    audio: "aktiv",
    selectedDeviceId: info.selectedDeviceId,
    sampleRate: info.sampleRate,
  });
};

const loadBaseline = async () => {
  const domain = el.baselineDomain.value.trim() || "default";
  const device = el.baselineDevice.value.trim() || null;
  const data = await controlGetBaseline(state.baseUrl, domain, device);
  setJsonView(el.baselineView, data);
};

const resetBaseline = async () => {
  const domain = el.baselineDomain.value.trim() || "default";
  const device = el.baselineDevice.value.trim() || null;
  const data = await controlResetBaseline(state.baseUrl, domain, device);
  setJsonView(el.baselineView, data);
};

const reloadPlugins = async () => {
  const data = await controlReloadPlugins(state.baseUrl);
  setJsonView(el.pluginsView, data);
};

const runPlugins = async () => {
  const payload = {
    domain: el.domain.value,
    device_id: el.device.value.trim() || null,
    metrics_hint: {
      has_image: Boolean(state.latestImageB64),
      has_audio: Boolean(state.latestAudioB64),
    },
    text: el.text.value.trim() || null,
  };
  const data = await controlRunPlugins(state.baseUrl, payload);
  setJsonView(el.pluginsView, data);
};

const fireActuator = async () => {
  const targetType = el.actuatorType.value;
  const target = el.actuatorTarget.value.trim();
  if (!target) throw new Error("Actuator target fehlt");

  let payloadObj = {};
  const raw = el.actuatorPayload.value.trim();
  if (raw) payloadObj = JSON.parse(raw);

  const resp = await controlActuatorFire(state.baseUrl, {
    target_type: targetType,
    target,
    payload: payloadObj,
    require_confirmation: true,
    confirmation_token: "CONFIRM",
    simulation: true,
    cooldown_s: 5,
    job_id: null,
    domain: el.domain.value,
    device_id: el.device.value.trim() || null,
  });
  setJsonView(el.actuatorView, resp);
};

const loadAudit = async () => {
  const resp = await controlLoadAudit(state.baseUrl, 100);
  setJsonView(el.actuatorView, resp);
};

const pingBackend = async () => {
  state.baseUrl = normalizeBaseUrl(el.backendBase.value);
  ws.setBaseUrl(state.baseUrl);
  const health = await pingHealth(state.baseUrl);
  setBackendStatus(
    el.backendStatus,
    true,
    `Backend: online (${health.status})`,
  );
};

const initCollapsiblePanels = () => {
  document.addEventListener("click", (event) => {
    if (event.target.closest(".help-btn")) return;

    const header = event.target.closest("[data-collapsible]");
    if (!header) return;

    const panel = header.closest(".panel");
    if (!panel) return;

    panel.classList.toggle("panel-collapsed");
    const chevron = header.querySelector(".chevron");
    if (chevron) {
      chevron.textContent =
        panel.classList.contains("panel-collapsed") ? "▸" : "▾";
    }
  });
};

const wireUi = () => {
  el.localSetupBtn?.addEventListener("click", applyLocalSetupDefaults);
  el.onlineSetupBtn?.addEventListener("click", applyOnlineSetupDefaults);

  [el.provider, el.model].forEach((input) => {
    input?.addEventListener("change", () => {
      const provider = el.provider.value;
      if (provider === "ollama") {
        markSetupMode("local");
      } else if (provider === "openrouter") {
        markSetupMode("online");
      } else {
        markSetupMode("manual");
      }
    });
  });

  el.pingBtn.addEventListener("click", async () => {
    try {
      await pingBackend();
    } catch (err) {
      setBackendStatus(
        el.backendStatus,
        false,
        `Backend: offline (${err.message})`,
      );
    }
  });

  el.setProviderBtn.addEventListener("click", async () => {
    try {
      await setProvider();
    } catch (err) {
      setJsonView(el.jobResult, { error: String(err) });
    }
  });

  el.runJobBtn.addEventListener("click", async () => {
    el.runJobBtn.disabled = true;
    try {
      await runJob();
    } catch (err) {
      setJsonView(el.jobResult, { error: String(err) });
    } finally {
      el.runJobBtn.disabled = false;
    }
  });

  el.cameraBtn.addEventListener("click", async () => {
    try {
      await toggleCamera();
    } catch (err) {
      setJsonView(el.jobResult, { camera_error: String(err) });
    }
  });

  el.captureBtn.addEventListener("click", () => {
    if (!state.cameraActive) {
      setJsonView(el.jobResult, {
        warning: "Kamera ist nicht aktiv. Bitte zuerst 'Kamera starten'.",
      });
      return;
    }

    state.latestImageB64 = video.captureFrameBase64();
    setJsonView(el.jobResult, {
      info: "Bild übernommen",
      image_bytes_estimate:
        state.latestImageB64 ?
          Math.floor((state.latestImageB64.length * 3) / 4)
        : 0,
    });
  });

  el.audioBtn.addEventListener("click", async () => {
    try {
      await toggleAudio();
    } catch (err) {
      setJsonView(el.jobResult, { audio_error: String(err) });
    }
  });

  el.loadCameraDevicesBtn?.addEventListener("click", async () => {
    try {
      await loadCameraDevices();
    } catch (err) {
      setJsonView(el.jobResult, { camera_devices_error: String(err) });
    }
  });

  el.loadMicDevicesBtn?.addEventListener("click", async () => {
    try {
      await loadMicDevices();
    } catch (err) {
      setJsonView(el.jobResult, { mic_devices_error: String(err) });
    }
  });

  el.recordBtn.addEventListener("click", async () => {
    el.recordBtn.disabled = true;
    try {
      state.latestAudioB64 = await audio.recordWavBase64(5000);
      setJsonView(el.jobResult, {
        info: "Audio aufgenommen (5s)",
        audio_bytes_estimate: Math.floor((state.latestAudioB64.length * 3) / 4),
      });
    } catch (err) {
      setJsonView(el.jobResult, { audio_record_error: String(err) });
    } finally {
      el.recordBtn.disabled = false;
    }
  });

  el.refreshStatsBtn.addEventListener("click", async () => {
    try {
      await refreshDashboard();
    } catch (err) {
      setJsonView(el.summaryView, { stats_error: String(err) });
    }
  });

  el.baselineGetBtn?.addEventListener("click", async () => {
    try {
      await loadBaseline();
    } catch (err) {
      setJsonView(el.baselineView, { error: String(err) });
    }
  });

  el.baselineResetBtn?.addEventListener("click", async () => {
    try {
      await resetBaseline();
    } catch (err) {
      setJsonView(el.baselineView, { error: String(err) });
    }
  });

  el.pluginsReloadBtn?.addEventListener("click", async () => {
    try {
      await reloadPlugins();
    } catch (err) {
      setJsonView(el.pluginsView, { error: String(err) });
    }
  });

  el.pluginsRunBtn?.addEventListener("click", async () => {
    try {
      await runPlugins();
    } catch (err) {
      setJsonView(el.pluginsView, { error: String(err) });
    }
  });

  el.actuatorFireBtn?.addEventListener("click", async () => {
    try {
      await fireActuator();
    } catch (err) {
      setJsonView(el.actuatorView, { error: String(err) });
    }
  });

  el.auditLoadBtn?.addEventListener("click", async () => {
    try {
      await loadAudit();
    } catch (err) {
      setJsonView(el.actuatorView, { error: String(err) });
    }
  });
};

const init = async () => {
  loadCameraPresets();
  bindCameraPresetActions();
  renderCameraPresetButtons();
  initHelpTooltips();
  updateCameraButtonUi();
  updateAudioButtonUi();
  markSetupMode("manual");

  initCollapsiblePanels();
  wireUi();
  ws.connect();

  if (navigator.mediaDevices?.addEventListener) {
    navigator.mediaDevices.addEventListener("devicechange", async () => {
      try {
        await Promise.all([loadCameraDevices(), loadMicDevices()]);
      } catch {
        // ignore live refresh errors
      }
    });
  }

  try {
    await pingBackend();
  } catch {
    setBackendStatus(el.backendStatus, false, "Backend: offline");
  }

  try {
    await refreshDashboard();
  } catch (err) {
    setJsonView(el.summaryView, {
      info: "Noch keine Statistiken",
      detail: String(err),
    });
  }

  try {
    await loadCameraDevices();
    await loadMicDevices();
  } catch (err) {
    setJsonView(el.jobResult, {
      warning: "Geräteliste konnte nicht vollständig geladen werden",
      detail: String(err),
    });
  }

  setJsonView(el.jobResult, {
    info: "Frontend bereit",
    hint: "Geräte auswählen, Kamera/Mikrofon starten und anschließend Job ausführen.",
    ws: pretty({ baseUrl: state.baseUrl }),
  });
};

init();
