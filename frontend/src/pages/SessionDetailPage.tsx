import { useParams } from 'react-router-dom';
import { Card, Table, Tag, Typography, Row, Col, Statistic, Descriptions, Button, Popconfirm, message } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { getStay, getStayPredictions, getStayAlerts, stopStay } from '../api/endpoints';
import VitalsEntryForm from '../components/common/VitalsEntryForm';
import type { SepsisPrediction } from '../types/domain';

const { Title } = Typography;

const RISK_THRESHOLD = 0.6;

function severityColor(sev: number | null): string {
    if (sev != null && sev >= 3) return 'red';
    if (sev != null && sev >= 2) return 'orange';
    return 'gold';
}

export default function SessionDetailPage() {
    const { id } = useParams<{ id: string }>();
    const queryClient = useQueryClient();

    const { data: stay } = useQuery({ queryKey: ['stay', id], queryFn: () => getStay(id!) });
    const { data: predictions } = useQuery({ queryKey: ['stayPredictions', id], queryFn: () => getStayPredictions(id!) });
    const { data: alerts } = useQuery({ queryKey: ['stayAlerts', id], queryFn: () => getStayAlerts(id!) });

    const stopMutation = useMutation({
        mutationFn: () => stopStay(id!),
        onSuccess: () => {
            message.success('Monitoring stopped');
            queryClient.invalidateQueries({ queryKey: ['stay', id] });
            queryClient.invalidateQueries({ queryKey: ['stays'] });
        },
        onError: () => message.error('Failed to stop monitoring'),
    });

    const sorted = [...(predictions ?? [])].sort((a, b) => a.hour - b.hour);
    const peakRisk = sorted.reduce((m, p) => Math.max(m, p.risk_score), 0);

    const trajectoryOption = {
        title: { text: 'Sepsis Risk Trajectory', textStyle: { color: '#e5e7eb', fontSize: 14 } },
        tooltip: { trigger: 'axis' as const },
        grid: { top: 50, right: 24, bottom: 40, left: 50 },
        xAxis: {
            type: 'category' as const,
            name: 'Hour',
            data: sorted.map((p) => p.hour),
            axisLabel: { color: '#9ca3af' },
            axisLine: { lineStyle: { color: '#374151' } },
        },
        yAxis: {
            type: 'value' as const,
            min: 0,
            max: 1,
            axisLabel: { color: '#9ca3af' },
            axisLine: { lineStyle: { color: '#374151' } },
            splitLine: { lineStyle: { color: '#1f2937' } },
        },
        series: [
            {
                type: 'line' as const,
                data: sorted.map((p) => +p.risk_score.toFixed(4)),
                smooth: true,
                symbol: 'circle',
                symbolSize: 5,
                lineStyle: { color: '#00d4aa', width: 2 },
                itemStyle: { color: '#00d4aa' },
                areaStyle: { color: 'rgba(0, 212, 170, 0.08)' },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{ yAxis: RISK_THRESHOLD }],
                    lineStyle: { color: '#ef4444', type: 'dashed' as const },
                    label: { formatter: 'Threshold 0.6', color: '#ef4444' },
                },
            },
        ],
        backgroundColor: 'transparent',
    };

    const predColumns = [
        { title: 'Hour', dataIndex: 'hour' },
        {
            title: 'Risk Score',
            dataIndex: 'risk_score',
            render: (v: number) => `${(v * 100).toFixed(1)}%`,
        },
        {
            title: 'Risk Level',
            dataIndex: 'risk_level',
            render: (l: string) => (
                <Tag color={l === 'HIGH' ? 'red' : l === 'MEDIUM' ? 'orange' : 'green'}>{l}</Tag>
            ),
        },
        { title: 'Created', dataIndex: 'created_at', render: (t: string) => t?.slice(0, 19) || '—' },
    ];

    const alertColumns = [
        {
            title: 'Severity',
            dataIndex: 'severity',
            render: (v: number | null) => <Tag color={severityColor(v)}>Severity {v ?? '—'}</Tag>,
        },
        { title: 'Status', dataIndex: 'status', render: (s: string) => <Tag>{s}</Tag> },
        { title: 'Start', dataIndex: 'start_time', render: (t: string) => t?.slice(0, 19) || '—' },
        { title: 'Last Update', dataIndex: 'last_update', render: (t: string) => t?.slice(0, 19) || '—' },
    ];

    return (
        <div>
            <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>Stay Detail</Title>
                {stay?.status === 'RUNNING' && (
                    <Popconfirm
                        title="Stop monitoring?"
                        description="This will end the ICU stay. No more vitals can be ingested."
                        okText="Stop"
                        cancelText="Cancel"
                        onConfirm={() => stopMutation.mutate()}
                    >
                        <Button danger loading={stopMutation.isPending}>Stop Monitoring</Button>
                    </Popconfirm>
                )}
            </Row>

            {stay && (
                <Card style={{ marginBottom: 16 }}>
                    <Descriptions column={3}>
                        <Descriptions.Item label="Stay ID">
                            <Typography.Text copyable={{ text: stay.stay_id }}>
                                {stay.stay_id.slice(0, 12)}…
                            </Typography.Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="Patient">{stay.patient_id}</Descriptions.Item>
                        <Descriptions.Item label="Record">{stay.source_record || '—'}</Descriptions.Item>
                        <Descriptions.Item label="Status">
                            <span className={`status-dot ${stay.status === 'RUNNING' ? 'running' : 'stopped'}`} />
                            {stay.status}
                        </Descriptions.Item>
                        <Descriptions.Item label="Start">{stay.start_time?.slice(0, 19) || '—'}</Descriptions.Item>
                        <Descriptions.Item label="End">{stay.end_time?.slice(0, 19) || '—'}</Descriptions.Item>
                    </Descriptions>
                </Card>
            )}

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col span={8}>
                    <Card><Statistic title="Total Predictions" value={predictions?.length || 0} /></Card>
                </Col>
                <Col span={8}>
                    <Card><Statistic title="Alerts" value={alerts?.length || 0} valueStyle={{ color: '#ef4444' }} /></Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Peak Risk"
                            value={(peakRisk * 100).toFixed(1)}
                            suffix="%"
                            valueStyle={{ color: '#f59e0b' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Card style={{ marginBottom: 16 }}>
                <ReactECharts option={trajectoryOption} style={{ height: 320 }} notMerge />
            </Card>

            {stay?.status === 'RUNNING' && id && (
                <div style={{ marginBottom: 16 }}>
                    <VitalsEntryForm stayId={id} />
                </div>
            )}

            <Card title="Alerts" style={{ marginBottom: 16 }}>
                <Table dataSource={alerts} columns={alertColumns} rowKey="alert_id" pagination={{ pageSize: 10 }} size="small" />
            </Card>

            <Card title="Hourly Predictions">
                <Table<SepsisPrediction> dataSource={sorted} columns={predColumns} rowKey="pred_id" pagination={{ pageSize: 20 }} size="small" />
            </Card>
        </div>
    );
}
