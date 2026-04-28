const audioBufferToWavBase64 = async (audioBuffer) => {
  const samples = audioBuffer.getChannelData(0);
  const sampleRate = audioBuffer.sampleRate;
  const numFrames = samples.length;

  const buffer = new ArrayBuffer(44 + numFrames * 2);
  const view = new DataView(buffer);

  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + numFrames * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, numFrames * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++)
    binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
};

const stopStream = (stream) => {
  if (!stream) return;
  stream.getTracks().forEach((t) => {
    try {
      t.stop();
    } catch {
      // ignore
    }
  });
};

export class AudioChain {
  constructor({
    gainEl,
    thresholdEl,
    eqLowEl,
    eqMidEl,
    eqHighEl,
    monitorCanvasEl,
    monitorModeEl,
    audioLevelEl,
  }) {
    this.gainEl = gainEl;
    this.thresholdEl = thresholdEl;
    this.eqLowEl = eqLowEl;
    this.eqMidEl = eqMidEl;
    this.eqHighEl = eqHighEl;
    this.monitorCanvasEl = monitorCanvasEl;
    this.monitorModeEl = monitorModeEl;
    this.audioLevelEl = audioLevelEl;

    this.ctx = null;
    this.stream = null;
    this.selectedDeviceIds = [];
    this.source = null;
    this.gain = null;
    this.eqLow = null;
    this.eqMid = null;
    this.eqHigh = null;
    this.compressor = null;
    this.dest = null;
    this.recorder = null;
    this.chunks = [];

    this.monitorAnalyser = null;
    this.monitorFrequencyBuffer = null;
    this.monitorTimeBuffer = null;
    this.monitorRaf = null;
    this.waterfallImage = null;
  }

  async enumerateAudioDevices() {
    try {
      const temp = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });
      stopStream(temp);
    } catch {
      // permission denied
    }
    const all = await navigator.mediaDevices.enumerateDevices();
    return all.filter((d) => d.kind === "audioinput");
  }

  setSelectedDeviceIds(ids) {
    this.selectedDeviceIds = Array.isArray(ids) ? ids.filter(Boolean) : [];
  }

  async start() {
    this.stop();

    if (!this.ctx) {
      this.ctx = new AudioContext();
    }

    if (this.ctx.state === "suspended") {
      await this.ctx.resume();
    }

    const selectedDeviceId = this.selectedDeviceIds[0] || null;
    const audioConstraints = {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
      channelCount: 1,
    };
    if (selectedDeviceId) {
      audioConstraints.deviceId = { exact: selectedDeviceId };
    }

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: audioConstraints,
      video: false,
    });
    this.source = this.ctx.createMediaStreamSource(this.stream);

    this.gain = this.ctx.createGain();

    this.eqLow = this.ctx.createBiquadFilter();
    this.eqLow.type = "lowshelf";
    this.eqLow.frequency.value = 200;

    this.eqMid = this.ctx.createBiquadFilter();
    this.eqMid.type = "peaking";
    this.eqMid.frequency.value = 1200;
    this.eqMid.Q.value = 1;

    this.eqHigh = this.ctx.createBiquadFilter();
    this.eqHigh.type = "highshelf";
    this.eqHigh.frequency.value = 5000;

    this.compressor = this.ctx.createDynamicsCompressor();

    this.dest = this.ctx.createMediaStreamDestination();
    this.monitorAnalyser = this.ctx.createAnalyser();
    this.monitorAnalyser.fftSize = 2048;
    this.monitorAnalyser.smoothingTimeConstant = 0.15;

    this.monitorFrequencyBuffer = new Float32Array(
      this.monitorAnalyser.frequencyBinCount,
    );
    this.monitorTimeBuffer = new Float32Array(this.monitorAnalyser.fftSize);

    this.source
      .connect(this.gain)
      .connect(this.eqLow)
      .connect(this.eqMid)
      .connect(this.eqHigh)
      .connect(this.compressor);

    this.compressor.connect(this.dest);
    this.compressor.connect(this.monitorAnalyser);

    this._bindControls();
    this._applyControls();
    this._startMonitorLoop();

    return {
      selectedDeviceId,
      sampleRate: this.ctx.sampleRate,
    };
  }

  _bindControls() {
    const apply = () => this._applyControls();
    [
      this.gainEl,
      this.thresholdEl,
      this.eqLowEl,
      this.eqMidEl,
      this.eqHighEl,
    ].forEach((el) => el?.addEventListener("input", apply));
  }

  _applyControls() {
    if (!this.gain) return;
    this.gain.gain.value = Number(this.gainEl?.value || 1);
    this.compressor.threshold.value = Number(this.thresholdEl?.value || -24);

    const toDb = (linear) => 20 * Math.log10(Math.max(0.0001, linear));
    this.eqLow.gain.value = toDb(Number(this.eqLowEl?.value || 1));
    this.eqMid.gain.value = toDb(Number(this.eqMidEl?.value || 1));
    this.eqHigh.gain.value = toDb(Number(this.eqHighEl?.value || 1));
  }

  async recordWavBase64(durationMs = 5000) {
    if (!this.dest) {
      throw new Error("Audio chain not started");
    }

    this.chunks = [];
    this.recorder = new MediaRecorder(this.dest.stream, {
      mimeType: "audio/webm",
    });

    const blob = await new Promise((resolve, reject) => {
      this.recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) this.chunks.push(e.data);
      };
      this.recorder.onerror = (e) =>
        reject(e.error || new Error("recording failed"));
      this.recorder.onstop = () =>
        resolve(new Blob(this.chunks, { type: "audio/webm" }));

      this.recorder.start();
      setTimeout(() => this.recorder.stop(), durationMs);
    });

    const arr = await blob.arrayBuffer();
    const decoded = await this.ctx.decodeAudioData(arr.slice(0));
    return audioBufferToWavBase64(decoded);
  }

  stop() {
    if (this.monitorRaf) {
      cancelAnimationFrame(this.monitorRaf);
      this.monitorRaf = null;
    }
    this.waterfallImage = null;

    if (this.recorder && this.recorder.state !== "inactive") {
      try {
        this.recorder.stop();
      } catch {
        // ignore
      }
    }

    stopStream(this.stream);
    this.stream = null;

    const nodes = [
      this.source,
      this.gain,
      this.eqLow,
      this.eqMid,
      this.eqHigh,
      this.compressor,
      this.dest,
      this.monitorAnalyser,
    ];

    nodes.forEach((n) => {
      if (!n || typeof n.disconnect !== "function") return;
      try {
        n.disconnect();
      } catch {
        // ignore
      }
    });

    this.source = null;
    this.gain = null;
    this.eqLow = null;
    this.eqMid = null;
    this.eqHigh = null;
    this.compressor = null;
    this.dest = null;
    this.monitorAnalyser = null;
  }

  _startMonitorLoop() {
    if (!this.monitorCanvasEl || !this.monitorAnalyser) return;

    const canvas = this.monitorCanvasEl;
    const ctx2d = canvas.getContext("2d");

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      ctx2d.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.waterfallImage = null;
    };
    resizeCanvas();

    const drawSpectrum = (W, H, data) => {
      ctx2d.fillStyle = "#05070c";
      ctx2d.fillRect(0, 0, W, H);
      ctx2d.strokeStyle = "#3b82f6";
      ctx2d.lineWidth = 1.5;
      ctx2d.beginPath();
      for (let x = 0; x < W; x++) {
        const idx = Math.min(
          data.length - 1,
          Math.floor((x / W) * data.length),
        );
        const db = data[idx];
        const t = Math.max(0, Math.min(1, (db + 120) / 120));
        const y = H - t * H;
        if (x === 0) ctx2d.moveTo(x, y);
        else ctx2d.lineTo(x, y);
      }
      ctx2d.stroke();
    };

    const drawPhase = (W, H, timeData) => {
      ctx2d.fillStyle = "#05070c";
      ctx2d.fillRect(0, 0, W, H);
      const midX = W / 2;
      const midY = H / 2;
      const r = Math.min(W, H) * 0.45;

      ctx2d.strokeStyle = "rgba(255,255,255,0.15)";
      ctx2d.beginPath();
      ctx2d.arc(midX, midY, r, 0, Math.PI * 2);
      ctx2d.stroke();

      ctx2d.strokeStyle = "#10b981";
      ctx2d.lineWidth = 1;
      ctx2d.beginPath();
      for (let i = 0; i < timeData.length; i++) {
        const sample = timeData[i];
        const angle = (i / timeData.length) * Math.PI * 2;
        const radius = r * (0.2 + 0.8 * Math.abs(sample));
        const x = midX + Math.cos(angle) * radius;
        const y = midY + Math.sin(angle) * radius;
        if (i === 0) ctx2d.moveTo(x, y);
        else ctx2d.lineTo(x, y);
      }
      ctx2d.closePath();
      ctx2d.stroke();
    };

    const drawWaterfall = (W, H, data) => {
      const pxW = canvas.width;
      const pxH = canvas.height;
      if (
        !this.waterfallImage ||
        this.waterfallImage.width !== pxW ||
        this.waterfallImage.height !== pxH
      ) {
        this.waterfallImage = ctx2d.createImageData(pxW, pxH);
        for (let i = 0; i < this.waterfallImage.data.length; i += 4) {
          this.waterfallImage.data[i] = 5;
          this.waterfallImage.data[i + 1] = 7;
          this.waterfallImage.data[i + 2] = 12;
          this.waterfallImage.data[i + 3] = 255;
        }
      }

      const rowBytes = pxW * 4;
      const arr = this.waterfallImage.data;
      arr.copyWithin(rowBytes, 0, (pxH - 1) * rowBytes);

      for (let x = 0; x < pxW; x++) {
        const idx = Math.min(
          data.length - 1,
          Math.floor((x / pxW) * data.length),
        );
        const db = data[idx];
        const t = Math.max(0, Math.min(1, (db + 120) / 120));
        const r = Math.floor(255 * t);
        const g = Math.floor(220 * t * t);
        const b = Math.floor(255 * (1 - t));
        const off = x * 4;
        arr[off] = r;
        arr[off + 1] = g;
        arr[off + 2] = b;
        arr[off + 3] = 255;
      }

      ctx2d.putImageData(this.waterfallImage, 0, 0);
      ctx2d.fillStyle = "rgba(255,255,255,0.75)";
      ctx2d.font = '12px "Segoe UI", Arial, sans-serif';
      ctx2d.fillText("Wasserfall", 8, 16);
    };

    const tick = () => {
      if (!this.monitorAnalyser) return;

      const rect = canvas.getBoundingClientRect();
      const W = Math.max(1, Math.floor(rect.width));
      const H = Math.max(1, Math.floor(rect.height));
      if (canvas.width === 0 || canvas.height === 0) resizeCanvas();

      this.monitorAnalyser.getFloatFrequencyData(this.monitorFrequencyBuffer);
      this.monitorAnalyser.getFloatTimeDomainData(this.monitorTimeBuffer);

      const rms = Math.sqrt(
        this.monitorTimeBuffer.reduce((acc, v) => acc + v * v, 0) /
          this.monitorTimeBuffer.length,
      );
      if (this.audioLevelEl) {
        this.audioLevelEl.value =
          Number.isFinite(rms) ? rms.toFixed(4) : "0.0000";
      }

      const mode = this.monitorModeEl?.value || "spectrum";
      if (mode === "waterfall") {
        drawWaterfall(W, H, this.monitorFrequencyBuffer);
      } else if (mode === "phase") {
        drawPhase(W, H, this.monitorTimeBuffer);
      } else {
        drawSpectrum(W, H, this.monitorFrequencyBuffer);
      }

      this.monitorRaf = requestAnimationFrame(tick);
    };

    this.monitorRaf = requestAnimationFrame(tick);
  }
}
