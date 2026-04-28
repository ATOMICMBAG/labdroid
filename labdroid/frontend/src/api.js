const asText = async (response) => {
  try {
    return await response.text();
  } catch {
    return "";
  }
};

const toQueryString = (params) => {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    q.set(key, String(value));
  });
  const s = q.toString();
  return s ? `?${s}` : "";
};

export const normalizeBaseUrl = (raw) =>
  (raw || "http://localhost:8000").trim().replace(/\/$/, "");

export const fetchJson = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const text = await asText(response);
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json();
};

export const pingHealth = async (baseUrl) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/health`);
};

export const setProviderRest = async (baseUrl, provider, model) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/jobs/provider/select`, {
    method: "POST",
    body: JSON.stringify({ provider, model: model || null }),
  });
};

export const startJobRest = async (baseUrl, payload) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/jobs/start`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

export const getSummary = async (baseUrl, filters = {}) => {
  const base = normalizeBaseUrl(baseUrl);
  const qs = toQueryString({
    domain: filters.domain,
    device: filters.device,
  });
  return fetchJson(`${base}/stats/summary${qs}`);
};

export const getHistogram = async (baseUrl, metric, bins, filters = {}) => {
  const base = normalizeBaseUrl(baseUrl);
  const qs = toQueryString({
    metric,
    bins,
    domain: filters.domain,
    device: filters.device,
  });
  return fetchJson(`${base}/stats/histogram${qs}`);
};

export const getTimeseries = async (baseUrl, metric, filters = {}) => {
  const base = normalizeBaseUrl(baseUrl);
  const qs = toQueryString({
    metric,
    domain: filters.domain,
    device: filters.device,
  });
  return fetchJson(`${base}/stats/timeseries${qs}`);
};

export const controlGetBaseline = async (baseUrl, domain, device_id) => {
  const base = normalizeBaseUrl(baseUrl);
  const qs = toQueryString({ domain, device_id });
  return fetchJson(`${base}/control/baseline${qs}`);
};

export const controlResetBaseline = async (baseUrl, domain, device_id) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/control/baseline/reset`, {
    method: "POST",
    body: JSON.stringify({ domain, device_id: device_id || null }),
  });
};

export const controlReloadPlugins = async (baseUrl) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/control/plugins/reload`, {
    method: "POST",
    body: JSON.stringify({}),
  });
};

export const controlRunPlugins = async (baseUrl, payload) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/control/plugins/run`, {
    method: "POST",
    body: JSON.stringify(payload || {}),
  });
};

export const controlActuatorFire = async (baseUrl, payload) => {
  const base = normalizeBaseUrl(baseUrl);
  return fetchJson(`${base}/control/actuator/fire`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
};

export const controlLoadAudit = async (baseUrl, limit = 100) => {
  const base = normalizeBaseUrl(baseUrl);
  const qs = toQueryString({ limit });
  return fetchJson(`${base}/control/actuator/audit${qs}`);
};
