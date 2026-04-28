import { normalizeBaseUrl } from "./api.js";

const toWsUrl = (baseUrl) => {
  const httpUrl = normalizeBaseUrl(baseUrl);
  if (httpUrl.startsWith("https://")) {
    return httpUrl.replace("https://", "wss://") + "/ws";
  }
  return httpUrl.replace("http://", "ws://") + "/ws";
};

export class WsClient {
  constructor({ baseUrl, onMessage, onStatus }) {
    this.baseUrl = baseUrl;
    this.onMessage = onMessage;
    this.onStatus = onStatus;
    this.ws = null;
    this.pending = new Map();
    this.counter = 0;
  }

  connect() {
    if (this.ws && this.ws.readyState <= 1) return;
    const url = toWsUrl(this.baseUrl);
    this.ws = new WebSocket(url);

    this.ws.onopen = () => this.onStatus?.("open");
    this.ws.onclose = () => this.onStatus?.("closed");
    this.ws.onerror = () => this.onStatus?.("error");
    this.ws.onmessage = (event) => this._handleMessage(event.data);
  }

  close() {
    if (!this.ws) return;
    this.ws.close();
    this.ws = null;
  }

  setBaseUrl(baseUrl) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.close();
      this.connect();
    }
  }

  async request(type, payload = {}, timeoutMs = 20_000) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.connect();
    }

    await this._waitOpen(timeoutMs);

    const reqId = `req_${Date.now()}_${++this.counter}`;
    const message = { type, payload: { ...payload, _req_id: reqId } };
    this.ws.send(JSON.stringify(message));

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(reqId);
        reject(new Error(`WS timeout for ${type}`));
      }, timeoutMs);

      this.pending.set(reqId, {
        resolve: (data) => {
          clearTimeout(timer);
          resolve(data);
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        },
      });
    });
  }

  _handleMessage(raw) {
    let data;
    try {
      data = JSON.parse(raw);
    } catch {
      this.onMessage?.({ type: "error", detail: "invalid_json" });
      return;
    }

    const reqId = data?.payload?._req_id;
    if (reqId && this.pending.has(reqId)) {
      const waiter = this.pending.get(reqId);
      this.pending.delete(reqId);
      waiter.resolve(data);
    }

    this.onMessage?.(data);
  }

  _waitOpen(timeoutMs) {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      const started = Date.now();
      const check = () => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          resolve();
          return;
        }
        if (Date.now() - started > timeoutMs) {
          reject(new Error("WS connect timeout"));
          return;
        }
        setTimeout(check, 80);
      };
      check();
    });
  }
}
