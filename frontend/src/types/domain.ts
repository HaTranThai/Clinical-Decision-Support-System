/** Domain types for ECG CDSS frontend */

export interface UserProfile {
    user_id: string;
    username: string;
    display_name: string | null;
    role: string;
}

export interface Session {
    session_id: string;
    patient_id: string | null;
    start_time: string | null;
    end_time: string | null;
    source_type: string | null;
    status: string;
    record_name: string | null;
}

export interface Prediction {
    pred_id: string;
    session_id: string;
    beat_ts_sec: number;
    pred_class: string;
    confidence: number | null;
    p_a: number | null;
    probs_json: Record<string, number> | null;
    created_at: string | null;
}

export interface Alert {
    alert_id: string;
    session_id: string;
    start_time: string | null;
    last_update: string | null;
    alert_type: string;
    status: string;
    severity: number | null;
    evidence_json: Record<string, any> | null;
}

export interface AlertAction {
    action_id: string;
    alert_id: string;
    user_id: string;
    action_time: string | null;
    action_type: string;
    reason: string | null;
    note: string | null;
}

export interface AlertDetail extends Alert {
    actions: AlertAction[];
}

export interface Setting {
    key: string;
    value: string | number | null;
}

export interface AnalyticsSummary {
    total_alerts: number;
    ack_count: number;
    dismiss_count: number;
    new_count: number;
    dismiss_rate: number;
    avg_response_time_sec: number | null;
}

export interface AlertsHourly {
    hour: string;
    count: number;
    alert_type: string | null;
}

export interface UserOut {
    user_id: string;
    username: string;
    display_name: string | null;
    role_id: string;
    role_name: string | null;
    is_active: boolean;
    created_at: string | null;
}

// MLOps types
export interface MLOpsRun {
    run_id: string;
    run_name: string;
    status: string;
    start_time: string | null;
    end_time: string | null;
    duration_sec: number | null;
    experiment_id: string;
    params: Record<string, string>;
    metrics: Record<string, number>;
}

export interface MLOpsExperimentsResponse {
    runs: MLOpsRun[];
    total: number;
    error?: string;
}

export interface ModelVersion {
    version: string;
    stage: string;
    creation_timestamp: string | null;
    last_updated_timestamp: string | null;
    run_id: string;
    description: string;
    tags: Record<string, string>;
    status: string;
}

export interface MLOpsRegistryResponse {
    model_name: string;
    versions: ModelVersion[];
    error?: string;
}

export interface PipelineRun {
    dag_run_id: string;
    state: string;
    start_date: string;
    end_date: string | null;
    run_type: string;
    logical_date?: string;
}

export interface PipelineStatus {
    available: boolean;
    dag_id?: string;
    last_run: PipelineRun | null;
    recent_runs: PipelineRun[];
    next_run: string | null;
}

export interface SplitStats {
    n_beats: number;
    records: string[];
    class_counts: { N: number; A: number; V: number };
}

export interface DatasetStats {
    available: boolean;
    train?: SplitStats;
    val?: SplitStats;
    test?: SplitStats;
    total_records?: number;
    generated_at?: string;
}
