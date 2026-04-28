const toJpegBase64 = (canvas, quality = 0.85) => {
  return canvas.toDataURL("image/jpeg", quality).split(",")[1] || null;
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

export class VideoAnalysis {
  constructor({ videoEl, roiCanvas, brightnessEl, contrastEl, saturationEl }) {
    this.videoEl = videoEl;
    this.roiCanvas = roiCanvas;
    this.brightnessEl = brightnessEl;
    this.contrastEl = contrastEl;
    this.saturationEl = saturationEl;

    this.stream = null;
    this.selectedDeviceIds = [];
    this.dragging = false;
    this.roi = null;
    this.dragStart = { x: 0, y: 0 };

    this._bindFilterControls();
    this._bindRoiEvents();
  }

  async enumerateVideoDevices() {
    try {
      const temp = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });
      stopStream(temp);
    } catch {
      // permission denied or no camera
    }

    const all = await navigator.mediaDevices.enumerateDevices();
    return all.filter((d) => d.kind === "videoinput");
  }

  setSelectedDeviceIds(ids) {
    this.selectedDeviceIds = Array.isArray(ids) ? ids.filter(Boolean) : [];
  }

  _bindFilterControls() {
    const apply = () => {
      const b = Number(this.brightnessEl?.value || 100);
      const c = Number(this.contrastEl?.value || 100);
      const s = Number(this.saturationEl?.value || 100);
      this.videoEl.style.filter = `brightness(${b}%) contrast(${c}%) saturate(${s}%)`;
    };

    [this.brightnessEl, this.contrastEl, this.saturationEl].forEach((el) =>
      el?.addEventListener("input", apply),
    );
    apply();
  }

  _bindRoiEvents() {
    const canvas = this.roiCanvas;
    if (!canvas) return;

    const getPos = (event) => {
      const rect = canvas.getBoundingClientRect();
      return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        w: rect.width,
        h: rect.height,
      };
    };

    canvas.addEventListener("pointerdown", (event) => {
      const p = getPos(event);
      this.dragging = true;
      this.dragStart = { x: p.x, y: p.y };
      this.roi = { x: p.x, y: p.y, width: 1, height: 1 };
      this._drawRoi();
    });

    canvas.addEventListener("pointermove", (event) => {
      if (!this.dragging) return;
      const p = getPos(event);
      const x = Math.min(this.dragStart.x, p.x);
      const y = Math.min(this.dragStart.y, p.y);
      const width = Math.abs(p.x - this.dragStart.x);
      const height = Math.abs(p.y - this.dragStart.y);
      this.roi = { x, y, width, height };
      this._drawRoi();
    });

    const stop = () => {
      this.dragging = false;
      this._drawRoi();
    };
    canvas.addEventListener("pointerup", stop);
    canvas.addEventListener("pointerleave", stop);
  }

  _drawRoi() {
    const canvas = this.roiCanvas;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(rect.width * ratio);
    canvas.height = Math.floor(rect.height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    if (!this.roi || this.roi.width < 4 || this.roi.height < 4) return;
    ctx.strokeStyle = "#10b981";
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(this.roi.x, this.roi.y, this.roi.width, this.roi.height);
    ctx.setLineDash([]);
  }

  async startCamera() {
    this.stopCamera();

    const selectedDeviceId = this.selectedDeviceIds[0] || null;
    let constraints = {
      video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    };

    if (selectedDeviceId) {
      constraints = {
        video: {
          deviceId: { exact: selectedDeviceId },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };
    }

    this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    this.videoEl.srcObject = this.stream;
    this.videoEl.muted = true;
    this.videoEl.playsInline = true;
    this.videoEl.autoplay = true;
    this.videoEl.style.display = "block";
    this.videoEl.style.opacity = "1";
    await this.videoEl.play();

    this.videoEl.onloadedmetadata = () => {
      this._drawRoi();
    };

    this._drawRoi();

    return {
      selectedDeviceId,
      width: this.videoEl.videoWidth,
      height: this.videoEl.videoHeight,
    };
  }

  stopCamera() {
    stopStream(this.stream);
    this.stream = null;
    if (this.videoEl) {
      this.videoEl.pause();
      this.videoEl.srcObject = null;
    }
  }

  captureFrameBase64() {
    if (!this.videoEl.videoWidth || !this.videoEl.videoHeight) return null;

    const temp = document.createElement("canvas");
    const ctx = temp.getContext("2d");
    temp.width = this.videoEl.videoWidth;
    temp.height = this.videoEl.videoHeight;
    ctx.drawImage(this.videoEl, 0, 0, temp.width, temp.height);

    if (!this.roi || this.roi.width < 4 || this.roi.height < 4) {
      return toJpegBase64(temp);
    }

    const viewRect = this.roiCanvas.getBoundingClientRect();
    const sx = (this.roi.x / viewRect.width) * temp.width;
    const sy = (this.roi.y / viewRect.height) * temp.height;
    const sw = (this.roi.width / viewRect.width) * temp.width;
    const sh = (this.roi.height / viewRect.height) * temp.height;

    const roiCanvas = document.createElement("canvas");
    roiCanvas.width = Math.max(8, Math.floor(sw));
    roiCanvas.height = Math.max(8, Math.floor(sh));
    roiCanvas
      .getContext("2d")
      .drawImage(temp, sx, sy, sw, sh, 0, 0, roiCanvas.width, roiCanvas.height);

    return toJpegBase64(roiCanvas);
  }
}
