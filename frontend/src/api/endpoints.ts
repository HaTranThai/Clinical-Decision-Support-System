/** Sessions, Alerts, Settings, Analytics API */
import http from './http';
import type {
    Session, Alert, AlertDetail, Prediction, Setting, AnalyticsSummary, AlertsHourly, UserOut,
    MLOpsExperimentsResponse, MLOpsRegistryResponse, PipelineStatus, DatasetStats,
} from '../types/domain';

// Sessions
export const getSessions = async () => (await http.get<Session[]>('/api/sessions')).data;
export const getSession = async (id: string) => (await http.get<Session>(`/api/sessions/${id}`)).data;
export const stopSession = async (id: string) => (await http.post(`/api/sessions/${id}/stop`)).data;
export const getSessionPredictions = async (id: string) => (await http.get<Prediction[]>(`/api/sessions/${id}/predictions`)).data;
export const getSessionAlerts = async (id: string) => (await http.get<Alert[]>(`/api/sessions/${id}/alerts`)).data;

// Alerts
export const getAlerts = async (params?: Record<string, string>) => (await http.get<Alert[]>('/api/alerts', { params })).data;
export const getAlertDetail = async (id: string) => (await http.get<AlertDetail>(`/api/alerts/${id}`)).data;
export const ackAlert = async (id: string, body: { reason?: string; note?: string }) => (await http.post(`/api/alerts/${id}/ack`, body)).data;
export const dismissAlert = async (id: string, body: { reason?: string; note?: string }) => (await http.post(`/api/alerts/${id}/dismiss`, body)).data;

// Settings
export const getSettings = async () => (await http.get<Setting[]>('/api/admin/settings')).data;
export const updateSettings = async (body: Record<string, any>) => (await http.put('/api/admin/settings', body)).data;

// Analytics
export const getAlertsHourly = async () => (await http.get<AlertsHourly[]>('/api/analytics/alerts_hourly')).data;
export const getAnalyticsSummary = async () => (await http.get<AnalyticsSummary>('/api/analytics/summary')).data;

// Users
export const getUsers = async () => (await http.get<UserOut[]>('/api/admin/users')).data;
export const createUser = async (body: any) => (await http.post('/api/admin/users', body)).data;
export const updateUser = async (id: string, body: any) => (await http.put(`/api/admin/users/${id}`, body)).data;
export const deleteUser = async (id: string) => (await http.delete(`/api/admin/users/${id}`)).data;

// MLOps
export const getMLOpsExperiments = async () =>
    (await http.get<MLOpsExperimentsResponse>('/api/mlops/experiments')).data;
export const getMLOpsRegistry = async () =>
    (await http.get<MLOpsRegistryResponse>('/api/mlops/registry')).data;
export const getPipelineStatus = async () =>
    (await http.get<PipelineStatus>('/api/mlops/pipeline/status')).data;
export const getDatasetStats = async () =>
    (await http.get<DatasetStats>('/api/mlops/dataset/stats')).data;
export const promoteModelVersion = async (version: string) =>
    (await http.post(`/api/mlops/registry/${version}/promote`)).data;
export const archiveModelVersion = async (version: string) =>
    (await http.post(`/api/mlops/registry/${version}/archive`)).data;
