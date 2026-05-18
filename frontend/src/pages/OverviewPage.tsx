import { useState } from 'react';
import { Row, Col, Card, Typography, Button, Tag, Statistic, Spin, Empty } from 'antd';
import { ReloadOutlined, PlusOutlined, AlertOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getOverview } from '../api/endpoints';
import { useLiveMonitorStore } from '../stores/liveMonitorStore';
import NewMonitoringModal from '../components/common/NewMonitoringModal';
import type { OverviewItem } from '../types/domain';

const { Title, Text } = Typography;

function riskColor(level: string): string {
    if (level === 'HIGH') return '#ef4444';
    if (level === 'MEDIUM') return '#f59e0b';
    return '#22c55e';
}

export default function OverviewPage() {
    const navigate = useNavigate();
    const selectStay = useLiveMonitorStore((s) => s.selectStay);
    const [modalOpen, setModalOpen] = useState(false);

    const { data, isLoading, refetch, isFetching } = useQuery({
        queryKey: ['overview'],
        queryFn: getOverview,
        refetchInterval: 5000,
        refetchIntervalInBackground: true,
    });

    const items = [...(data ?? [])].sort((a, b) => b.risk_score - a.risk_score);
    const total = items.length;
    const running = items.filter((i) => i.status === 'RUNNING').length;
    const highRisk = items.filter((i) => i.risk_level === 'HIGH').length;
    const totalAlerts = items.reduce((s, i) => s + i.alert_count, 0);

    const openStay = (stayId: string) => {
        selectStay(stayId);
        navigate('/live');
    };

    return (
        <div>
            <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>ICU Triage Board</Title>
                <div>
                    <Button icon={<PlusOutlined />} type="primary" style={{ marginRight: 8 }} onClick={() => setModalOpen(true)}>
                        New Monitoring
                    </Button>
                    <Button icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetch()}>
                        Refresh
                    </Button>
                </div>
            </Row>

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={12} md={6}><Card><Statistic title="Total Stays" value={total} /></Card></Col>
                <Col xs={12} md={6}><Card><Statistic title="Running" value={running} valueStyle={{ color: '#22c55e' }} /></Card></Col>
                <Col xs={12} md={6}><Card><Statistic title="High Risk" value={highRisk} valueStyle={{ color: '#ef4444' }} /></Card></Col>
                <Col xs={12} md={6}><Card><Statistic title="Total Alerts" value={totalAlerts} valueStyle={{ color: '#f59e0b' }} /></Card></Col>
            </Row>

            {isLoading ? (
                <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
            ) : items.length === 0 ? (
                <Empty description="No ICU stays" />
            ) : (
                <Row gutter={[16, 16]}>
                    {items.map((item: OverviewItem) => {
                        const color = riskColor(item.risk_level);
                        const isHigh = item.risk_level === 'HIGH';
                        return (
                            <Col xs={24} sm={12} md={8} lg={6} key={item.stay_id}>
                                <Card
                                    hoverable
                                    onClick={() => openStay(item.stay_id)}
                                    className={isHigh ? 'triage-high' : undefined}
                                    style={{
                                        borderLeft: `4px solid ${color}`,
                                        border: isHigh ? `1px solid ${color}` : undefined,
                                    }}
                                    styles={{ body: { padding: 16 } }}
                                >
                                    <Text strong style={{ fontSize: 15, display: 'block' }}>
                                        {item.patient_name || 'Unknown Patient'}
                                    </Text>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        {item.source_record || item.stay_id.slice(0, 8)}
                                    </Text>
                                    <div style={{ margin: '12px 0', display: 'flex', alignItems: 'baseline', gap: 8 }}>
                                        <span style={{ fontSize: 32, fontWeight: 700, color }}>
                                            {(item.risk_score * 100).toFixed(0)}%
                                        </span>
                                        <Tag color={color} style={{ marginInlineEnd: 0 }}>{item.risk_level}</Tag>
                                    </div>
                                    <Row justify="space-between">
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            ICU Hour {item.current_hour}
                                        </Text>
                                        <Text style={{ fontSize: 12, color: item.alert_count > 0 ? '#ef4444' : undefined }}>
                                            <AlertOutlined /> {item.alert_count}
                                        </Text>
                                    </Row>
                                    <Tag
                                        color={item.status === 'RUNNING' ? 'green' : 'default'}
                                        style={{ marginTop: 8 }}
                                    >
                                        {item.status}
                                    </Tag>
                                </Card>
                            </Col>
                        );
                    })}
                </Row>
            )}

            <NewMonitoringModal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                onCreated={(stay) => openStay(stay.stay_id)}
            />
        </div>
    );
}
