import { useEffect } from 'react';
import { Row, Col, Card, Typography, Tag, Select, Empty } from 'antd';
import {
    MedicineBoxOutlined,
    AlertOutlined,
    ArrowUpOutlined,
    ArrowDownOutlined,
    MinusOutlined,
    WarningFilled,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useQuery } from '@tanstack/react-query';
import { getStays, getStayPredictions, getStayAlerts } from '../api/endpoints';
import { useLiveMonitorStore } from '../stores/liveMonitorStore';

const { Title, Text } = Typography;

const RISK_THRESHOLD = 0.6;

const VITAL_SPECS: { key: string; label: string; unit: string; lo: number; hi: number }[] = [
    { key: 'HR', label: 'Heart Rate', unit: 'bpm', lo: 60, hi: 100 },
    { key: 'O2Sat', label: 'SpO₂', unit: '%', lo: 95, hi: 100 },
    { key: 'Temp', label: 'Temperature', unit: '°C', lo: 36.0, hi: 38.0 },
    { key: 'SBP', label: 'Systolic BP', unit: 'mmHg', lo: 90, hi: 140 },
    { key: 'MAP', label: 'Mean Art. P.', unit: 'mmHg', lo: 65, hi: 110 },
    { key: 'DBP', label: 'Diastolic BP', unit: 'mmHg', lo: 60, hi: 90 },
    { key: 'Resp', label: 'Resp. Rate', unit: '/min', lo: 12, hi: 20 },
    { key: 'Lactate', label: 'Lactate', unit: 'mmol/L', lo: 0, hi: 2 },
];

function riskColor(level: string | undefined): string {
    if (level === 'HIGH') return '#ef4444';
    if (level === 'MEDIUM') return '#f59e0b';
    return '#22c55e';
}

function VitalTile({
    spec,
    value,
    prev,
}: {
    spec: (typeof VITAL_SPECS)[number];
    value: number | null | undefined;
    prev: number | null | undefined;
}) {
    const hasValue = value != null;
    const abnormal = hasValue && (value! < spec.lo || value! > spec.hi);
    const color = !hasValue ? '#6b7280' : abnormal ? '#ef4444' : '#00d4aa';

    let trend = <MinusOutlined style={{ color: '#6b7280' }} />;
    if (hasValue && prev != null) {
        if (value! > prev + 0.05) trend = <ArrowUpOutlined style={{ color: '#f59e0b' }} />;
        else if (value! < prev - 0.05) trend = <ArrowDownOutlined style={{ color: '#3b82f6' }} />;
    }

    return (
        <div
            style={{
                background: 'var(--bg-secondary)',
                border: `1px solid ${abnormal ? 'rgba(239,68,68,0.4)' : 'var(--border)'}`,
                borderRadius: 10,
                padding: '12px 14px',
                height: '100%',
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text style={{ color: '#9ca3af', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {spec.label}
                </Text>
                {trend}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
                <span style={{ color, fontSize: 28, fontWeight: 700, lineHeight: 1 }}>
                    {hasValue ? Number(value!.toFixed(1)) : '—'}
                </span>
                <span style={{ color: '#6b7280', fontSize: 12 }}>{spec.unit}</span>
            </div>
            <Text style={{ color: '#4b5563', fontSize: 10 }}>
                normal {spec.lo}–{spec.hi}
            </Text>
        </div>
    );
}

export default function LiveMonitorPage() {
    const { data: stays } = useQuery({ queryKey: ['stays'], queryFn: getStays, refetchInterval: 15000 });

    const {
        stayId: selectedStay,
        selectStay,
        connected,
        lastVitals,
        vitalsHistory,
        riskHistory,
        lastPrediction,
        alerts,
        seedRisk,
        seedAlerts,
    } = useLiveMonitorStore();

    const { data: predictionHistory } = useQuery({
        queryKey: ['stay-predictions', selectedStay],
        queryFn: () => getStayPredictions(selectedStay!),
        enabled: !!selectedStay,
    });

    const { data: stayAlerts } = useQuery({
        queryKey: ['stay-alerts', selectedStay],
        queryFn: () => getStayAlerts(selectedStay!),
        enabled: !!selectedStay,
    });

    useEffect(() => {
        if (stays && stays.length > 0 && !selectedStay) {
            const running = stays.find((s) => s.status === 'RUNNING');
            selectStay(running ? running.stay_id : stays[0].stay_id);
        }
    }, [stays, selectedStay, selectStay]);

    useEffect(() => {
        if (predictionHistory) seedRisk(predictionHistory);
    }, [predictionHistory, seedRisk]);

    useEffect(() => {
        if (stayAlerts) seedAlerts(stayAlerts);
    }, [stayAlerts, seedAlerts]);

    const stay = stays?.find((s) => s.stay_id === selectedStay);
    const riskScore = lastPrediction?.risk_score ?? 0;
    const riskLevel = lastPrediction?.risk_level ?? 'LOW';
    const riskPct = Math.round(riskScore * 100);
    const currentHour = lastPrediction?.hour ?? riskHistory[riskHistory.length - 1]?.hour ?? 0;

    const prevVitals = vitalsHistory.length >= 2 ? vitalsHistory[vitalsHistory.length - 2].record : null;

    const gaugeOption = {
        animationDuration: 400,
        series: [
            {
                type: 'gauge',
                startAngle: 210,
                endAngle: -30,
                min: 0,
                max: 100,
                radius: '95%',
                progress: { show: true, width: 16, itemStyle: { color: riskColor(riskLevel) } },
                axisLine: {
                    lineStyle: {
                        width: 16,
                        color: [
                            [0.3, 'rgba(34,197,94,0.25)'],
                            [0.6, 'rgba(245,158,11,0.25)'],
                            [1, 'rgba(239,68,68,0.25)'],
                        ],
                    },
                },
                pointer: { width: 5, itemStyle: { color: riskColor(riskLevel) } },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                anchor: { show: true, size: 14, itemStyle: { color: riskColor(riskLevel) } },
                detail: {
                    valueAnimation: true,
                    formatter: '{value}%',
                    color: riskColor(riskLevel),
                    fontSize: 34,
                    fontWeight: 700,
                    offsetCenter: [0, '38%'],
                },
                data: [{ value: riskPct }],
            },
        ],
    };

    const trajectoryOption = {
        animation: false,
        tooltip: { trigger: 'axis' as const },
        grid: { top: 24, right: 24, bottom: 40, left: 48 },
        xAxis: {
            type: 'category' as const,
            name: 'ICU hour',
            nameLocation: 'middle' as const,
            nameGap: 26,
            nameTextStyle: { color: '#6b7280' },
            data: riskHistory.map((r) => r.hour),
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
                data: riskHistory.map((r) => +r.risk_score.toFixed(4)),
                smooth: true,
                symbol: 'circle',
                symbolSize: 4,
                lineStyle: { color: '#00d4aa', width: 2.5 },
                itemStyle: { color: '#00d4aa' },
                areaStyle: {
                    color: {
                        type: 'linear' as const,
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(0,212,170,0.30)' },
                            { offset: 1, color: 'rgba(0,212,170,0.02)' },
                        ],
                    },
                },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{ yAxis: RISK_THRESHOLD }],
                    lineStyle: { color: '#ef4444', type: 'dashed' as const },
                    label: { formatter: 'Alert threshold', color: '#ef4444', position: 'insideEndTop' as const },
                },
                markArea: {
                    silent: true,
                    data: [
                        [{ yAxis: 0, itemStyle: { color: 'rgba(34,197,94,0.05)' } }, { yAxis: 0.3 }],
                        [{ yAxis: 0.3, itemStyle: { color: 'rgba(245,158,11,0.05)' } }, { yAxis: 0.6 }],
                        [{ yAxis: 0.6, itemStyle: { color: 'rgba(239,68,68,0.06)' } }, { yAxis: 1 }],
                    ],
                },
            },
        ],
        backgroundColor: 'transparent',
    };

    const showBanner = riskLevel === 'HIGH' || alerts.length > 0;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Row align="middle" justify="space-between">
                <Col>
                    <Title level={4} style={{ margin: 0 }}>
                        <MedicineBoxOutlined style={{ marginRight: 8, color: '#00d4aa' }} />
                        ICU Patient Monitor
                    </Title>
                </Col>
                <Col>
                    <span style={{ marginRight: 12 }}>
                        <span
                            style={{
                                display: 'inline-block',
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                marginRight: 6,
                                background: connected ? '#22c55e' : '#ef4444',
                                boxShadow: connected ? '0 0 6px #22c55e' : 'none',
                            }}
                        />
                        <Text style={{ color: connected ? '#22c55e' : '#ef4444', fontSize: 12 }}>
                            {connected ? 'LIVE' : 'DISCONNECTED'}
                        </Text>
                    </span>
                    <Select
                        showSearch
                        placeholder="Search patient / ICU stay"
                        value={selectedStay}
                        onChange={selectStay}
                        style={{ width: 340 }}
                        optionFilterProp="label"
                        filterOption={(input, option) =>
                            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                        }
                        options={stays?.map((s) => ({
                            value: s.stay_id,
                            label: `${s.patient_name || s.source_record || s.stay_id.slice(0, 8)}  ·  ${s.source_record || '—'}  ·  ${s.status}`,
                        }))}
                    />
                </Col>
            </Row>

            {stay && (
                <Card bodyStyle={{ padding: '10px 18px' }}>
                    <Row gutter={32}>
                        <Col><Text type="secondary" style={{ fontSize: 12 }}>Patient</Text><div><Text strong>{stay.patient_name || '—'}</Text></div></Col>
                        <Col><Text type="secondary" style={{ fontSize: 12 }}>Record</Text><div><Text strong>{stay.source_record || '—'}</Text></div></Col>
                        <Col><Text type="secondary" style={{ fontSize: 12 }}>Status</Text><div><Tag color={stay.status === 'RUNNING' ? 'green' : 'default'}>{stay.status}</Tag></div></Col>
                        <Col><Text type="secondary" style={{ fontSize: 12 }}>Current ICU hour</Text><div><Text strong>{currentHour}</Text></div></Col>
                        <Col><Text type="secondary" style={{ fontSize: 12 }}>Stay ID</Text><div><Text code style={{ fontSize: 11 }}>{stay.stay_id.slice(0, 8)}</Text></div></Col>
                    </Row>
                </Card>
            )}

            {showBanner && (
                <div
                    style={{
                        background: 'linear-gradient(90deg, rgba(239,68,68,0.18), rgba(239,68,68,0.04))',
                        border: '1px solid rgba(239,68,68,0.45)',
                        borderRadius: 10,
                        padding: '12px 18px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                    }}
                >
                    <WarningFilled style={{ color: '#ef4444', fontSize: 20 }} />
                    <Text strong style={{ color: '#fca5a5' }}>
                        {riskLevel === 'HIGH'
                            ? `HIGH SEPSIS RISK — ${riskPct}% at ICU hour ${currentHour}.`
                            : 'Active sepsis alert on this patient.'}{' '}
                        {alerts.length > 0 && `${alerts.length} alert(s) raised.`} Clinical review recommended.
                    </Text>
                </div>
            )}

            <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                    <Card title="Sepsis Risk Score" style={{ height: '100%' }}>
                        <ReactECharts option={gaugeOption} style={{ height: 230 }} notMerge />
                        <div style={{ textAlign: 'center', marginTop: -8 }}>
                            <Tag color={riskColor(riskLevel)} style={{ fontSize: 13, padding: '3px 18px' }}>
                                {riskLevel} RISK
                            </Tag>
                        </div>
                    </Card>
                </Col>
                <Col xs={24} md={16}>
                    <Card title="Sepsis Risk Trajectory" style={{ height: '100%' }}>
                        {riskHistory.length === 0 ? (
                            <Empty description="Waiting for risk data" style={{ padding: 60 }} />
                        ) : (
                            <ReactECharts option={trajectoryOption} style={{ height: 270 }} notMerge />
                        )}
                    </Card>
                </Col>
            </Row>

            <Card title="Vital Signs" bodyStyle={{ padding: 16 }}>
                <Row gutter={[12, 12]}>
                    {VITAL_SPECS.map((spec) => (
                        <Col xs={12} sm={8} md={6} lg={3} key={spec.key}>
                            <VitalTile spec={spec} value={lastVitals?.[spec.key]} prev={prevVitals?.[spec.key]} />
                        </Col>
                    ))}
                </Row>
            </Card>

            <Card title={<span><AlertOutlined style={{ marginRight: 8 }} />Sepsis Alerts</span>}>
                {alerts.length === 0 ? (
                    <Text style={{ color: '#6b7280' }}>No alerts for this patient.</Text>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 240, overflow: 'auto' }}>
                        {alerts.map((a, i) => (
                            <div
                                key={a.alert_id || i}
                                style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '10px 14px',
                                    borderRadius: 8,
                                    background: 'rgba(239,68,68,0.07)',
                                    border: '1px solid rgba(239,68,68,0.22)',
                                }}
                            >
                                <span>
                                    <WarningFilled style={{ color: '#ef4444', marginRight: 8 }} />
                                    <Text strong>Sepsis warning</Text>
                                    <Text type="secondary" style={{ marginLeft: 10, fontSize: 12 }}>
                                        {a.start_time ? a.start_time.slice(0, 19).replace('T', ' ') : '—'}
                                    </Text>
                                </span>
                                <span>
                                    <Tag color={riskColor('HIGH')}>severity {(a.severity ?? 0).toFixed(2)}</Tag>
                                    <Tag>{a.status}</Tag>
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </Card>
        </div>
    );
}
