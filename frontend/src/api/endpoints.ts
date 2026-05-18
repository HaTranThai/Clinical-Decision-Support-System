import http from './http';
import type {
    ICUStay, Alert, AlertDetail, SepsisPrediction, Setting, AnalyticsSummary, AlertsHourly, UserOut,
    MLOpsExperimentsResponse, MLOpsRegistryResponse, PipelineStatus, DatasetStats,
    PatientOut, PatientDetail, OverviewItem,
} from '../types/domain';

export const getOverview = async () => (await http.get<OverviewItem[]>('/api/overview')).data;

export const getPatients = async (search?: string) =>
    (await http.get<PatientOut[]>('/api/patients', { params: search ? { search } : undefined })).data;
export const getPatient = async (id: string) => (await http.get<PatientDetail>(`/api/patients/${id}`)).data;
export const createPatient = async (body: { name: string; external_ref?: string; age?: number; gender?: string }) =>
    (await http.post<PatientOut>('/api/patients', body)).data;
export const updatePatient = async (id: string, body: { name?: string; external_ref?: string; age?: number; gender?: string }) =>
    (await http.put<PatientOut>(`/api/patients/${id}`, body)).data;
export const createStayForPatient = async (id: string, body: { source_record?: string }) =>
    (await http.post<ICUStay>(`/api/patients/${id}/stays`, body)).data;

export const createStay = async (body: {
    patient_name: string; external_ref?: string; age?: number; gender?: string; source_record?: string;
}) => (await http.post<ICUStay>('/api/stays', body)).data;
export const ingestVitals = async (stayId: string, body: { hour: number; record: Record<string, number> }) =>
    (await http.post(`/api/stays/${stayId}/vitals`, body)).data;

export const getStays = async () => (await http.get<ICUStay[]>('/api/stays')).data;
export const getStay = async (id: string) => (await http.get<ICUStay>(`/api/stays/${id}`)).data;
export const stopStay = async (id: string) => (await http.post(`/api/stays/${id}/stop`)).data;
export const getStayPredictions = async (id: string) => (await http.get<SepsisPrediction[]>(`/api/stays/${id}/predictions`)).data;
export const getStayAlerts = async (id: string) => (await http.get<Alert[]>(`/api/stays/${id}/alerts`)).data;

export const getAlerts = async (params?: Record<string, string>) => (await http.get<Alert[]>('/api/alerts', { params })).data;
export const getAlertDetail = async (id: string) => (await http.get<AlertDetail>(`/api/alerts/${id}`)).data;
export const ackAlert = async (id: string, body: { reason?: string; note?: string }) => (await http.post(`/api/alerts/${id}/ack`, body)).data;
export const dismissAlert = async (id: string, body: { reason?: string; note?: string }) => (await http.post(`/api/alerts/${id}/dismiss`, body)).data;

export const getSettings = async () => (await http.get<Setting[]>('/api/admin/settings')).data;
export const updateSettings = async (body: Record<string, any>) => (await http.put('/api/admin/settings', body)).data;

export const getAlertsHourly = async () => (await http.get<AlertsHourly[]>('/api/analytics/alerts_hourly')).data;
export const getAnalyticsSummary = async () => (await http.get<AnalyticsSummary>('/api/analytics/summary')).data;

export const getUsers = async () => (await http.get<UserOut[]>('/api/admin/users')).data;
export const getRoles = async () => (await http.get<{ role_id: string; name: string }[]>('/api/admin/users/roles')).data;
export const createUser = async (body: any) => (await http.post('/api/admin/users', body)).data;
export const updateUser = async (id: string, body: any) => (await http.put(`/api/admin/users/${id}`, body)).data;
export const deleteUser = async (id: string) => (await http.delete(`/api/admin/users/${id}`)).data;

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
