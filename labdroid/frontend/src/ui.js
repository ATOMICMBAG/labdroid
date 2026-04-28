export const $ = (id) => document.getElementById(id);

export const pretty = (value) => JSON.stringify(value, null, 2);

export const setJsonView = (element, value) => {
  if (!element) return;
  element.textContent = typeof value === "string" ? value : pretty(value);
};

export const setBackendStatus = (element, online, text) => {
  if (!element) return;
  element.classList.toggle("online", online);
  element.classList.toggle("offline", !online);
  element.textContent = text;
};

export const drawMessage = (ctx, text) => {
  if (!ctx) return;
  const { canvas } = ctx;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#9aa6b5";
  ctx.font = "13px sans-serif";
  ctx.fillText(text, 12, 22);
};
