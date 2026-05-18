export interface WSMessage {
    type: 'vitals' | 'prediction' | 'alert';
    data: any;
}

export interface WSVitalsData {
    hour: number;
    ts: string;
    record: Record<string, number | null>;
}

export interface WSPredictionData {
    hour: number;
    ts: string;
    risk_score: number;
    risk_level: string;
}

export interface WSAlertData {
    alert_id: string;
    severity: number | null;
    status: string;
    start_time: string | null;
}
