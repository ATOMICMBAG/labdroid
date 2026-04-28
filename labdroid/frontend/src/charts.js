import { drawMessage } from "./ui.js";

const fitCanvas = (canvas) => {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(300, Math.floor(rect.width || canvas.width));
  const height = Math.max(180, Math.floor(rect.height || canvas.height));
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width, height };
};

export const drawHistogram = (canvas, histogram) => {
  const { ctx, width, height } = fitCanvas(canvas);
  ctx.clearRect(0, 0, width, height);

  const rows = histogram?.histogram || [];
  if (!rows.length) {
    drawMessage(ctx, "Keine Histogramm-Daten");
    return;
  }

  const maxCount = Math.max(...rows.map((r) => r.count), 1);
  const pad = { left: 34, right: 10, top: 12, bottom: 26 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const barW = plotW / rows.length;

  ctx.strokeStyle = "#2f3845";
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + plotH);
  ctx.lineTo(pad.left + plotW, pad.top + plotH);
  ctx.stroke();

  rows.forEach((row, i) => {
    const h = (row.count / maxCount) * (plotH - 4);
    const x = pad.left + i * barW + 2;
    const y = pad.top + plotH - h;
    ctx.fillStyle = "#3b82f6";
    ctx.fillRect(x, y, Math.max(2, barW - 4), h);
  });

  ctx.fillStyle = "#9aa6b5";
  ctx.font = "12px sans-serif";
  ctx.fillText("0", 12, pad.top + plotH + 4);
  ctx.fillText(String(maxCount), 6, pad.top + 12);
};

export const drawTimeseries = (canvas, ts) => {
  const { ctx, width, height } = fitCanvas(canvas);
  ctx.clearRect(0, 0, width, height);

  const points = ts?.points || [];
  if (points.length < 2) {
    drawMessage(ctx, "Zu wenige Timeseries-Daten");
    return;
  }

  const values = points.map((p) => Number(p.value));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = Math.max(1e-9, max - min);

  const pad = { left: 34, right: 10, top: 12, bottom: 24 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  ctx.strokeStyle = "#2f3845";
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + plotH);
  ctx.lineTo(pad.left + plotW, pad.top + plotH);
  ctx.stroke();

  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((p, i) => {
    const x = pad.left + (i / (points.length - 1)) * plotW;
    const y = pad.top + plotH - ((Number(p.value) - min) / spread) * plotH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#9aa6b5";
  ctx.font = "12px sans-serif";
  ctx.fillText(min.toFixed(3), 2, pad.top + plotH + 4);
  ctx.fillText(max.toFixed(3), 2, pad.top + 12);
};
