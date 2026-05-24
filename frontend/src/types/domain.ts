export interface UserProfile {
    user_id: string;
    username: string;
    display_name: string | null;
    role: string;
}

export interface ICUStay {
    stay_id: string;
    patient_id: string;
    patient_name: string | null;
    start_time: string | null;
    end_time: string | null;
    status: string;
    source_record: string | null;
}

export interface SepsisPrediction {
    pred_id: string;
    stay_id: string;
    hour: number;
    risk_score: number;
    risk_level: string;
    created_at: string | null;
}

export interface Alert {
    alert_id: string;
    stay_id: string;
    patient_id: string | null;
    patient_name: string | null;
    source_record: string | null;
    start_time: string | null;
    last_update: string | null;
    severity: number | null;
    status: string;
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

export interface PatientOut {
    patient_id: string;
    name: string | null;
    external_ref: string | null;
    age: number | null;
    gender: string | null;
    stay_count: number;
}

export interface PatientDetail extends PatientOut {
    stays: ICUStay[];
}

export interface OverviewItem {
    stay_id: string;
    patient_id: string | null;
    patient_name: string | null;
    source_record: string | null;
    status: string;
    current_hour: number;
    risk_score: number;
    risk_level: string;
    alert_count: number;
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
    hour: number;
    count: number;
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
    n_patients: number;
    n_rows: number;
    n_positive: number;
    positive_rate: number;
}

export interface DatasetStats {
    available: boolean;
    train?: SplitStats;
    val?: SplitStats;
    test?: SplitStats;
    n_features?: number;
    total_patients?: number;
    generated_at?: string;
}
