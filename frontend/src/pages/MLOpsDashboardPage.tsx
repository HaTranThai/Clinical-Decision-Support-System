import { useQuery } from '@tanstack/react-query';
import { Card, Col, Row, Statistic, Table, Tag, Typography, Empty, Spin } from 'antd';
import {
    ExperimentOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    DatabaseOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { getMLOpsExperiments, getMLOpsRegistry, getPipelineStatus, getDatasetStats } from '../api/endpoints';
import type { PipelineRun, SplitStats } from '../types/domain';

const { Title, Text } = Typography;

// ─── helpers ────────────────────────────────────────────────────────────────

const stateColor: Record<string, string> = {
    success: 'success',
    failed: 'error',
    running: 'processing',
    queued: 'default',
};

function formatDuration(sec: number | null): string {
    if (sec == null) return '-';
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function fmtDt(iso: string | null | undefined): string {
    if (!iso) return '-';
    return dayjs(iso).format('YYYY-MM-DD HH:mm');
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function DatasetTable({ split, label }: { split: SplitStats | undefined; label: string }) {
    if (!split) return null;
    return (
        <tr>
            <td style={{ padding: '4px 8px', fontWeight: 500 }}>{label}</td>
            <td style={{ padding: '4px 8px' }}>{split.records.length}</td>
            <td style={{ padding: '4px 8px' }}>{split.n_beats.toLocaleString()}</td>
            <td style={{ padding: '4px 8px' }}>{split.class_counts.N.toLocaleString()}</td>
            <td style={{ padding: '4px 8px' }}>{split.class_counts.A.toLocaleString()}</td>
            <td style={{ padding: '4px 8px' }}>{split.class_counts.V.toLocaleString()}</td>
        </tr>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function MLOpsDashboardPage() {
    const { data: experiments, isLoading: expLoading } = useQuery({
        queryKey: ['mlops-experiments'],
        queryFn: getMLOpsExperiments,
    });

    const { data: registry, isLoading: regLoading } = useQuery({
        queryKey: ['mlops-registry'],
        queryFn: getMLOpsRegistry,
    });

    const { data: pipelineStatus, isLoading: pipeLoading } = useQuery({
        queryKey: ['pipeline-status'],
        queryFn: getPipelineStatus,
        refetchInterval: 30000,
    });

    const { data: datasetStats, isLoading: dsLoading } = useQuery({
        queryKey: ['dataset-stats'],
        queryFn: getDatasetStats,
    });

    const champion = registry?.versions.find((v) => v.stage === 'Production');
    const championAuroc = champion ? parseFloat(champion.tags.test_auroc ?? '') : null;
    const championAuprc = champion ? parseFloat(champion.tags.test_auprc ?? '') : null;

    const totalRuns = experiments?.total ?? 0;
    const lastRunState = pipelineStatus?.last_run?.state ?? null;

    const trendRuns = (experiments?.runs ?? [])
        .filter((r) => r.status === 'FINISHED' && r.start_time)
        .slice(-20);

    const trendLabels = trendRuns.map((r) => dayjs(r.start_time!).format('MM-DD HH:mm'));
    const valAurocSeries = trendRuns.map((r) => (r.metrics.val_auroc != null ? +r.metrics.val_auroc.toFixed(4) : null));
    const testAurocSeries = trendRuns.map((r) => (r.metrics.test_auroc != null ? +r.metrics.test_auroc.toFixed(4) : null));

    const chartOption = {
        title: { text: 'AUROC Trend (last 20 runs)', textStyle: { color: '#e5e7eb', fontSize: 14 } },
        tooltip: { trigger: 'axis' },
        legend: { data: ['Validation AUROC', 'Test AUROC'], textStyle: { color: '#9ca3af' } },
        grid: { left: 50, right: 20, top: 60, bottom: 60 },
        xAxis: {
            type: 'category',
            data: trendLabels,
            axisLabel: { color: '#9ca3af', rotate: 30, fontSize: 11 },
            axisLine: { lineStyle: { color: '#374151' } },
        },
        yAxis: {
            type: 'value',
            min: 0,
            max: 1,
            axisLabel: { color: '#9ca3af' },
            axisLine: { lineStyle: { color: '#374151' } },
            splitLine: { lineStyle: { color: '#1f2937' } },
        },
        series: [
            {
                name: 'Validation AUROC',
                type: 'line',
                data: valAurocSeries,
                itemStyle: { color: '#00d4aa' },
                lineStyle: { color: '#00d4aa' },
                connectNulls: true,
                smooth: true,
            },
            {
                name: 'Test AUROC',
                type: 'line',
                data: testAurocSeries,
                itemStyle: { color: '#3b82f6' },
                lineStyle: { color: '#3b82f6' },
                connectNulls: true,
                smooth: true,
            },
        ],
        backgroundColor: 'transparent',
    };

    // Pipeline recent runs table columns
    const recentRunCols = [
        {
            title: 'Run ID',
            dataIndex: 'dag_run_id',
            key: 'dag_run_id',
            render: (id: string) => (
                <Text code style={{ fontSize: 11 }}>{id.slice(0, 20)}{id.length > 20 ? '…' : ''}</Text>
            ),
        },
        {
            title: 'State',
            dataIndex: 'state',
            key: 'state',
            render: (state: string) => <Tag color={stateColor[state] ?? 'default'}>{state.toUpperCase()}</Tag>,
        },
        {
            title: 'Start',
            dataIndex: 'start_date',
            key: 'start_date',
            render: (v: string) => fmtDt(v),
        },
        {
            title: 'End',
            dataIndex: 'end_date',
            key: 'end_date',
            render: (v: string | null) => fmtDt(v),
        },
        {
            title: 'Type',
            dataIndex: 'run_type',
            key: 'run_type',
        },
    ];

    const anyLoading = expLoading || regLoading || pipeLoading || dsLoading;

    return (
        <Spin spinning={anyLoading} tip="Loading MLOps data...">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                <Title level={3} style={{ margin: 0 }}>MLOps Dashboard</Title>

                {/* Row 1: Stats cards */}
                <Row gutter={16}>
                    <Col span={6}>
                        <Card>
                            <Statistic
                                title="Champion AUROC"
                                value={championAuroc != null ? (championAuroc * 100).toFixed(2) : 'N/A'}
                                suffix={championAuroc != null ? '%' : ''}
                                prefix={<CheckCircleOutlined style={{ color: '#00d4aa' }} />}
                                valueStyle={{ color: '#00d4aa' }}
                            />
                        </Card>
                    </Col>
                    <Col span={6}>
                        <Card>
                            <Statistic
                                title="Champion AUPRC"
                                value={championAuprc != null ? (championAuprc * 100).toFixed(2) : 'N/A'}
                                suffix={championAuprc != null ? '%' : ''}
                                prefix={<CheckCircleOutlined style={{ color: '#3b82f6' }} />}
                                valueStyle={{ color: '#3b82f6' }}
                            />
                        </Card>
                    </Col>
                    <Col span={6}>
                        <Card>
                            <Statistic
                                title="Total Experiments"
                                value={totalRuns}
                                prefix={<ExperimentOutlined />}
                            />
                        </Card>
                    </Col>
                    <Col span={6}>
                        <Card>
                            <Statistic
                                title="Last Pipeline Run"
                                value={lastRunState ? lastRunState.toUpperCase() : 'N/A'}
                                prefix={<ClockCircleOutlined />}
                                valueStyle={{
                                    color: lastRunState === 'success' ? '#00d4aa'
                                        : lastRunState === 'failed' ? '#ef4444'
                                            : lastRunState === 'running' ? '#3b82f6'
                                                : '#9ca3af',
                                }}
                            />
                        </Card>
                    </Col>
                </Row>

                {/* Row 2: F1 Trend + Dataset Stats */}
                <Row gutter={16}>
                    <Col span={16}>
                        <Card bodyStyle={{ padding: 16 }}>
                            {trendRuns.length === 0 ? (
                                <Empty description="No finished runs yet" style={{ padding: 40 }} />
                            ) : (
                                <ReactECharts option={chartOption} style={{ height: 300 }} theme="dark" />
                            )}
                        </Card>
                    </Col>
                    <Col span={8}>
                        <Card
                            title={<span><DatabaseOutlined /> Dataset Statistics</span>}
                            style={{ height: '100%' }}
                        >
                            {dsLoading ? (
                                <Spin />
                            ) : !datasetStats?.available ? (
                                <Empty description="Dataset not prepared yet" />
                            ) : (
                                <div>
                                    {datasetStats.generated_at && (
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            Generated: {fmtDt(datasetStats.generated_at)}
                                        </Text>
                                    )}
                                    <table style={{ width: '100%', marginTop: 12, borderCollapse: 'collapse', fontSize: 13 }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid #374151' }}>
                                                <th style={{ padding: '4px 8px', textAlign: 'left' }}>Split</th>
                                                <th style={{ padding: '4px 8px', textAlign: 'left' }}>Records</th>
                                                <th style={{ padding: '4px 8px', textAlign: 'left' }}>Beats</th>
                                                <th style={{ padding: '4px 8px', textAlign: 'left' }}>N</th>
                                                <th style={{ padding: '4px 8px', textAlign: 'left' }}>A</th>
                                                <th style={{ padding: '4px 8px', textAlign: 'left' }}>V</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <DatasetTable split={datasetStats.train} label="Train" />
                                            <DatasetTable split={datasetStats.val} label="Val" />
                                            <DatasetTable split={datasetStats.test} label="Test" />
                                        </tbody>
                                    </table>
                                    {datasetStats.total_records != null && (
                                        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                                            Total records: {datasetStats.total_records}
                                        </Text>
                                    )}
                                </div>
                            )}
                        </Card>
                    </Col>
                </Row>

                {/* Row 3: Pipeline Status */}
                <Card title="Daily Retraining Pipeline (Airflow)">
                    {pipeLoading ? (
                        <Spin />
                    ) : !pipelineStatus?.available ? (
                        <Empty description="Airflow not available" />
                    ) : (
                        <div>
                            <Row gutter={24} style={{ marginBottom: 16 }}>
                                <Col span={8}>
                                    <Text strong>Last Run</Text>
                                    {pipelineStatus.last_run ? (
                                        <div style={{ marginTop: 8 }}>
                                            <Tag color={stateColor[pipelineStatus.last_run.state] ?? 'default'}>
                                                {pipelineStatus.last_run.state.toUpperCase()}
                                            </Tag>
                                            <div style={{ marginTop: 4 }}>
                                                <Text type="secondary" style={{ fontSize: 12 }}>
                                                    Start: {fmtDt(pipelineStatus.last_run.start_date)}
                                                </Text>
                                            </div>
                                            {pipelineStatus.last_run.end_date && (
                                                <div>
                                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                                        End: {fmtDt(pipelineStatus.last_run.end_date)}
                                                    </Text>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <Text type="secondary"> No runs yet</Text>
                                    )}
                                </Col>
                                <Col span={8}>
                                    <Text strong>Next Scheduled</Text>
                                    <div style={{ marginTop: 8 }}>
                                        {pipelineStatus.next_run ? (
                                            <Text>{fmtDt(pipelineStatus.next_run)}</Text>
                                        ) : (
                                            <Text type="secondary">Not scheduled</Text>
                                        )}
                                    </div>
                                </Col>
                                <Col span={8}>
                                    <Text strong>DAG</Text>
                                    <div style={{ marginTop: 8 }}>
                                        <Text code>{pipelineStatus.dag_id ?? '-'}</Text>
                                    </div>
                                </Col>
                            </Row>
                            <Table<PipelineRun>
                                dataSource={pipelineStatus.recent_runs}
                                columns={recentRunCols}
                                rowKey="dag_run_id"
                                pagination={false}
                                size="small"
                                title={() => <Text strong>Recent Runs (last 7)</Text>}
                            />
                        </div>
                    )}
                </Card>

                {/* Row 4: Champion Model Details */}
                <Card title="Current Production Model">
                    {regLoading ? (
                        <Spin />
                    ) : !champion ? (
                        <Empty description="No Production model found" />
                    ) : (
                        <Row gutter={24}>
                            <Col span={8}>
                                <Statistic title="Model Name" value={registry?.model_name ?? '-'} />
                            </Col>
                            <Col span={4}>
                                <Statistic title="Version" value={`v${champion.version}`} />
                            </Col>
                            <Col span={4}>
                                <Statistic
                                    title="Test AUROC"
                                    value={champion.tags.test_auroc
                                        ? (parseFloat(champion.tags.test_auroc) * 100).toFixed(2)
                                        : 'N/A'}
                                    suffix={champion.tags.test_auroc ? '%' : ''}
                                />
                            </Col>
                            <Col span={4}>
                                <Statistic
                                    title="Test AUPRC"
                                    value={champion.tags.test_auprc
                                        ? (parseFloat(champion.tags.test_auprc) * 100).toFixed(2)
                                        : 'N/A'}
                                    suffix={champion.tags.test_auprc ? '%' : ''}
                                />
                            </Col>
                            <Col span={4}>
                                <Statistic
                                    title="Registered"
                                    value={fmtDt(champion.creation_timestamp)}
                                />
                            </Col>
                            {Object.keys(champion.tags).filter(
                                (k) => !['test_auroc', 'test_auprc'].includes(k)
                            ).length > 0 && (
                                <Col span={24} style={{ marginTop: 16 }}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>Additional tags: </Text>
                                    {Object.entries(champion.tags)
                                        .filter(([k]) => !['test_auroc', 'test_auprc'].includes(k))
                                        .map(([k, v]) => (
                                            <Tag key={k} style={{ marginBottom: 4 }}>{k}: {v}</Tag>
                                        ))}
                                </Col>
                            )}
                            {champion.description && (
                                <Col span={24} style={{ marginTop: 8 }}>
                                    <Text type="secondary">{champion.description}</Text>
                                </Col>
                            )}
                        </Row>
                    )}
                </Card>
            </div>
        </Spin>
    );
}
