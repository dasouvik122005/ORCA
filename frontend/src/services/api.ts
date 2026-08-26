/* ORCA API Service — Communicates with the backend */

import type { Harbor, OrcaResponse, UserQuery, WSEvent } from '../types';

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

export async function sendMessage(query: UserQuery): Promise<OrcaResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(query),
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function getHarbors(): Promise<Record<string, Harbor>> {
  const response = await fetch(`${API_BASE}/api/harbors`);
  if (!response.ok) throw new Error('Failed to fetch harbors');
  return response.json();
}

export async function healthCheck(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error('Backend not available');
  return response.json();
}

export class OrcaWebSocket {
  private ws: WebSocket | null = null;
  private onEvent: (event: WSEvent) => void;
  private reconnectTimer: number | null = null;

  constructor(onEvent: (event: WSEvent) => void) {
    this.onEvent = onEvent;
  }

  connect() {
    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        console.log('🐋 WebSocket connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data: WSEvent = JSON.parse(event.data);
          this.onEvent(data);
        } catch {
          // ignore non-JSON messages
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...');
        this.reconnectTimer = window.setTimeout(() => this.connect(), 3000);
      };

      this.ws.onerror = () => {
        // Will trigger onclose
      };
    } catch {
      this.reconnectTimer = window.setTimeout(() => this.connect(), 3000);
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close();
  }
}
