import { Card, Row, Col, Statistic, Typography } from 'antd';
import ReactECharts from 'echarts-for-react';
import { useQuery } from '@tanstack/react-query';
import { getAnalyticsSummary, getAlertsHourly } from '../api/endpoints';

const { Title } = Typography;

export default function AnalyticsPage() {
    const { data: summary } = useQuery({ queryKey: ['summary'], queryFn: getAnalyticsSummary, refetchInterval: 30000 });
    const { data: hourly } = useQuery({ queryKey: ['hourly'], queryFn: getAlertsHourly, refetchInterval: 30000 });

    const barOption = {
        tooltip: { trigger: 'axis' as const },
        grid: { top: 40, right: 20, bottom: 40, left: 50 },
        xAxis: {
            type: 'category' as const,
            data: hourly?.map((h) => `${String(h.hour).padStart(2, '0')}:00`) || [],
            axisLabel: { color: '#9ca3af' },
        },
        yAxis: { type: 'value' as const, axisLabel: { color: '#9ca3af' } },
        series: [
            {
                name: 'Sepsis Alerts',
                type: 'bar' as const,
                data: hourly?.map((h) => h.count) || [],
                itemStyle: {
                    color: {
                        type: 'linear' as const,
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: '#00d4aa' },
                            { offset: 1, color: '#00b894' },
                        ],
                    },
                    borderRadius: [4, 4, 0, 0],
                },
            },
        ],
        backgroundColor: 'transparent',
    };

    const pieOption = {
        tooltip: { trigger: 'item' as const },
        series: [
            {
                type: 'pie' as const,
                radius: ['40%', '70%'],
                data: [
                    { value: summary?.ack_count || 0, name: 'ACK', itemStyle: { color: '#3b82f6' } },
                    { value: summary?.dismiss_count || 0, name: 'Dismissed', itemStyle: { color: '#6b7280' } },
                    { value: summary?.new_count || 0, name: 'New', itemStyle: { color: '#ef4444' } },
                ],
                label: { color: '#9ca3af' },
            },
        ],
        backgroundColor: 'transparent',
    };

    return (
        <div>
            <Title level={4} style={{ marginBottom: 16 }}>Analytics Dashboard</Title>

            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={12} md={5}>
                    <Card><Statistic title="Total Alerts" value={summary?.total_alerts || 0} /></Card>
                </Col>
                <Col xs={12} md={5}>
                    <Card><Statistic title="Acknowledged" value={summary?.ack_count || 0} valueStyle={{ color: '#3b82f6' }} /></Card>
                </Col>
                <Col xs={12} md={5}>
                    <Card><Statistic title="Dismissed" value={summary?.dismiss_count || 0} valueStyle={{ color: '#6b7280' }} /></Card>
                </Col>
                <Col xs={12} md={4}>
                    <Card>
                        <Statistic
                            title="Dismiss Rate"
                            value={((summary?.dismiss_rate || 0) * 100).toFixed(1)}
                            suffix="%"
                            valueStyle={{ color: '#f59e0b' }}
                        />
                    </Card>
                </Col>
                <Col xs={12} md={5}>
                    <Card>
                        <Statistic
                            title="Avg Response"
                            value={summary?.avg_response_time_sec != null ? Math.round(summary.avg_response_time_sec) : '—'}
                            suffix={summary?.avg_response_time_sec != null ? 's' : ''}
                            valueStyle={{ color: '#00d4aa' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={[16, 16]}>
                <Col xs={24} md={14}>
                    <Card title="Sepsis Alerts per Hour">
                        <ReactECharts option={barOption} style={{ height: 300 }} />
                    </Card>
                </Col>
                <Col xs={24} md={10}>
                    <Card title="Alert Status Distribution">
                        <ReactECharts option={pieOption} style={{ height: 300 }} />
                    </Card>
                </Col>
            </Row>
        </div>
    );
}
