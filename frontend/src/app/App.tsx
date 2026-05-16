import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import ProtectedRoute from '../components/common/ProtectedRoute';
import LoginPage from '../pages/LoginPage';
import LiveMonitorPage from '../pages/LiveMonitorPage';
import AlertsPage from '../pages/AlertsPage';
import SessionsPage from '../pages/SessionsPage';
import SessionDetailPage from '../pages/SessionDetailPage';
import AnalyticsPage from '../pages/AnalyticsPage';
import AdminSettingsPage from '../pages/AdminSettingsPage';
import AdminUsersPage from '../pages/AdminUsersPage';
import MLOpsDashboardPage from '../pages/MLOpsDashboardPage';
import ExperimentsPage from '../pages/ExperimentsPage';
import ModelRegistryPage from '../pages/ModelRegistryPage';

export default function App() {
    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                    <Route path="/live" element={<LiveMonitorPage />} />
                    <Route path="/alerts" element={<AlertsPage />} />
                    <Route path="/sessions" element={<SessionsPage />} />
                    <Route path="/sessions/:id" element={<SessionDetailPage />} />
                    <Route path="/analytics" element={<AnalyticsPage />} />
                    <Route path="/admin/settings" element={<AdminSettingsPage />} />
                    <Route path="/admin/users" element={<AdminUsersPage />} />
                    <Route path="/mlops" element={<MLOpsDashboardPage />} />
                    <Route path="/mlops/experiments" element={<ExperimentsPage />} />
                    <Route path="/mlops/registry" element={<ModelRegistryPage />} />
                    <Route path="/" element={<Navigate to="/live" replace />} />
                </Route>
            </Route>
        </Routes>
    );
}
