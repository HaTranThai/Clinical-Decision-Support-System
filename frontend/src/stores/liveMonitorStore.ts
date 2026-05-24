import { create } from 'zustand';
import type { WSVitalsData, WSPredictionData, WSAlertData } from '../types/ws';
import type { SepsisPrediction, Alert } from '../types/domain';

interface RiskPoint {
    hour: number;
    risk_score: number;
    risk_level: string;
}

interface VitalsPoint {
    hour: number;
    record: Record<string, number | null>;
}

interface LiveMonitorState {
    stayId: string | null;
    connected: boolean;
    ws: WebSocket | null;
    lastVitals: Record<string, number | null> | null;
    vitalsHistory: VitalsPoint[];
    riskHistory: RiskPoint[];
    lastPrediction: WSPredictionData | null;
    alerts: WSAlertData[];

    selectStay: (id: string | null) => void;
    seedRisk: (preds: SepsisPrediction[]) => void;
    seedAlerts: (items: Alert[]) => void;
    connectWs: () => void;
    disconnectWs: () => void;
}

const WS_PROTO = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_BASE = (import.meta as any).env?.VITE_WS_BASE_URL || `${WS_PROTO}//${window.location.host}`;
const MAX_HISTORY = 600;

function upsertRisk(list: RiskPoint[], point: RiskPoint): RiskPoint[] {
    const idx = list.findIndex((p) => p.hour === point.hour);
    if (idx >= 0) {
        const copy = list.slice();
        copy[idx] = point;
        return copy;
    }
    return [...list, point].sort((a, b) => a.hour - b.hour).slice(-MAX_HISTORY);
}

export const useLiveMonitorStore = create<LiveMonitorState>((set, get) => ({
    stayId: null,
    connected: false,
    ws: null,
    lastVitals: null,
    vitalsHistory: [],
    riskHistory: [],
    lastPrediction: null,
    alerts: [],

    selectStay: (id) => {
        if (get().stayId === id) return;
        get().disconnectWs();
        set({
            stayId: id,
            lastVitals: null,
            vitalsHistory: [],
            riskHistory: [],
            lastPrediction: null,
            alerts: [],
        });
        if (id) {
            setTimeout(() => get().connectWs(), 50);
        }
    },

    seedRisk: (preds) => {
        const sorted = [...preds]
            .map((p) => ({ hour: p.hour, risk_score: p.risk_score, risk_level: p.risk_level }))
            .sort((a, b) => a.hour - b.hour);
        let history = get().riskHistory;
        for (const p of sorted) history = upsertRisk(history, p);
        const latest = history[history.length - 1];
        set({
            riskHistory: history,
            lastPrediction: latest
                ? { hour: latest.hour, ts: '', risk_score: latest.risk_score, risk_level: latest.risk_level }
                : get().lastPrediction,
        });
    },

    seedAlerts: (items) => {
        const mapped: WSAlertData[] = items.map((a) => ({
            alert_id: a.alert_id,
            severity: a.severity ?? 0,
            status: a.status,
            start_time: a.start_time ?? '',
        }));
        set({ alerts: mapped.slice(0, 50) });
    },

    connectWs: () => {
        const { stayId, ws: existingWs } = get();
        if (!stayId) return;
        if (existingWs && existingWs.readyState === WebSocket.OPEN) return;

        const token = localStorage.getItem('token') || '';
        const ws = new WebSocket(`${WS_BASE}/ws/live?stay_id=${stayId}&token=${token}`);

        ws.onopen = () => set({ connected: true });

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'vitals') {
                    const v = msg.data as WSVitalsData;
                    set((state) => ({
                        lastVitals: v.record,
                        vitalsHistory: [...state.vitalsHistory, { hour: v.hour, record: v.record }].slice(-MAX_HISTORY),
                    }));
                } else if (msg.type === 'prediction') {
                    const p = msg.data as WSPredictionData;
                    set((state) => ({
                        lastPrediction: p,
                        riskHistory: upsertRisk(state.riskHistory, {
                            hour: p.hour,
                            risk_score: p.risk_score,
                            risk_level: p.risk_level,
                        }),
                    }));
                } else if (msg.type === 'alert') {
                    set((state) => ({
                        alerts: [msg.data as WSAlertData, ...state.alerts].slice(0, 50),
                    }));
                }
            } catch {
                /* ignore malformed frame */
            }
        };

        ws.onclose = () => {
            set({ connected: false, ws: null });
            setTimeout(() => {
                const current = get();
                if (current.stayId && !current.ws) current.connectWs();
            }, 3000);
        };

        ws.onerror = () => ws.close();
        set({ ws });
    },

    disconnectWs: () => {
        const { ws } = get();
        if (ws) {
            ws.onclose = null;
            ws.close();
        }
        set({ ws: null, connected: false });
    },
}));
