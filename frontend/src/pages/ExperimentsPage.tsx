import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    Button, Input, Select, Table, Tag, Typography, Space, Spin, Empty, Descriptions, Tooltip,
} from 'antd';
import { ReloadOutlined, CopyOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getMLOpsExperiments } from '../api/endpoints';
import type { MLOpsRun } from '../types/domain';

const { Title, Text } = Typography;
const { Search } = Input;

// ─── helpers ────────────────────────────────────────────────────────────────

const statusColor: Record<string, string> = {
    FINISHED: 'success',
    FAILED: 'error',
    RUNNING: 'processing',
};

function fmtDt(iso: string | null | undefined): string {
    if (!iso) return '-';
    return dayjs(iso).format('YYYY-MM-DD HH:mm');
}

function fmtDuration(sec: number | null): string {
    if (sec == null) return '-';
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function fmtMetric(val: number | undefined): string {
    if (val == null) return '-';
    return (val * 100).toFixed(2) + '%';
}

// ─── Expanded Row ────────────────────────────────────────────────────────────

function ExpandedRow({ record }: { record: MLOpsRun }) {
    const paramItems = Object.entries(record.params).map(([k, v]) => ({ key: k, value: v }));
    const metricItems = Object.entries(record.metrics).map(([k, v]) => ({ key: k, value: v.toFixed(6) }));

    const copyRunId = () => {
        navigator.clipboard.writeText(record.run_id).catch(() => {});
    };

    return (
        <div style={{ padding: '8px 16px', background: 'rgba(0,0,0,0.2)', borderRadius: 4 }}>
            <Space align="center" style={{ marginBottom: 12 }}>
                <Text strong style={{ fontSize: 12 }}>Run ID:</Text>
                <Text code style={{ fontSize: 11 }}>{record.run_id}</Text>
                <Tooltip title="Copy Run ID">
                    <Button
                        icon={<CopyOutlined />}
                        size="small"
                        type="text"
                        onClick={copyRunId}
                    />
                </Tooltip>
            </Space>

            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                    <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>Parameters</Text>
                    {paramItems.length === 0 ? (
                        <Text type="secondary" style={{ fontSize: 12 }}>No params</Text>
                    ) : (
                        <Descriptions
                            column={1}
                            size="small"
                            bordered
                            items={paramItems.map((p) => ({ key: p.key, label: p.key, children: p.value }))}
                        />
                    )}
                </div>
                <div style={{ flex: 2, minWidth: 300 }}>
                    <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>Metrics</Text>
                    {metricItems.length === 0 ? (
                        <Text type="secondary" style={{ fontSize: 12 }}>No metrics</Text>
                    ) : (
                        <Descriptions
                            column={2}
                            size="small"
                            bordered
                            items={metricItems.map((m) => ({ key: m.key, label: m.key, children: m.value }))}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExperimentsPage() {
    const [searchText, setSearchText] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('ALL');

    const { data, isLoading, refetch, isFetching } = useQuery({
        queryKey: ['mlops-experiments'],
        queryFn: getMLOpsExperiments,
    });

    const filtered = useMemo(() => {
        const runs = data?.runs ?? [];
        return runs.filter((r) => {
            const matchName = r.run_name.toLowerCase().includes(searchText.toLowerCase());
            const matchStatus = statusFilter === 'ALL' || r.status === statusFilter;
            return matchName && matchStatus;
        });
    }, [data, searchText, statusFilter]);

    const columns: ColumnsType<MLOpsRun> = [
        {
            title: 'Run Name',
            dataIndex: 'run_name',
            key: 'run_name',
            render: (name: string) => <Text strong>{name}</Text>,
            sorter: (a, b) => a.run_name.localeCompare(b.run_name),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 110,
            render: (status: string) => (
                <Tag color={statusColor[status] ?? 'default'}>{status}</Tag>
            ),
        },
        {
            title: 'Start Time',
            dataIndex: 'start_time',
            key: 'start_time',
            width: 160,
            render: (v: string | null) => fmtDt(v),
            sorter: (a, b) => {
                if (!a.start_time) return -1;
                if (!b.start_time) return 1;
                return a.start_time.localeCompare(b.start_time);
            },
            defaultSortOrder: 'descend',
        },
        {
            title: 'Duration',
            dataIndex: 'duration_sec',
            key: 'duration_sec',
            width: 100,
            render: (v: number | null) => fmtDuration(v),
        },
        {
            title: 'Val F1',
            key: 'val_f1',
            width: 90,
            render: (_: unknown, r: MLOpsRun) => fmtMetric(r.metrics.val_f1_macro),
            sorter: (a, b) => (a.metrics.val_f1_macro ?? 0) - (b.metrics.val_f1_macro ?? 0),
        },
        {
            title: 'Test F1',
            key: 'test_f1',
            width: 90,
            render: (_: unknown, r: MLOpsRun) => fmtMetric(r.metrics.test_f1_macro),
            sorter: (a, b) => (a.metrics.test_f1_macro ?? 0) - (b.metrics.test_f1_macro ?? 0),
        },
        {
            title: 'Test Acc',
            key: 'test_acc',
            width: 90,
            render: (_: unknown, r: MLOpsRun) => fmtMetric(r.metrics.test_accuracy),
            sorter: (a, b) => (a.metrics.test_accuracy ?? 0) - (b.metrics.test_accuracy ?? 0),
        },
    ];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={3} style={{ margin: 0 }}>Experiments</Title>
                <Button
                    icon={<ReloadOutlined />}
                    onClick={() => refetch()}
                    loading={isFetching}
                >
                    Refresh
                </Button>
            </div>

            <Space wrap>
                <Search
                    placeholder="Search by run name..."
                    allowClear
                    style={{ width: 280 }}
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                />
                <Select
                    value={statusFilter}
                    onChange={setStatusFilter}
                    style={{ width: 160 }}
                    options={[
                        { label: 'All Statuses', value: 'ALL' },
                        { label: 'FINISHED', value: 'FINISHED' },
                        { label: 'FAILED', value: 'FAILED' },
                        { label: 'RUNNING', value: 'RUNNING' },
                    ]}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                    {filtered.length} of {data?.total ?? 0} runs
                </Text>
            </Space>

            <Spin spinning={isLoading} tip="Loading experiments...">
                {!isLoading && filtered.length === 0 ? (
                    <Empty description="No runs match your filters" style={{ padding: 60 }} />
                ) : (
                    <Table<MLOpsRun>
                        dataSource={filtered}
                        columns={columns}
                        rowKey="run_id"
                        size="middle"
                        pagination={{ pageSize: 20, showSizeChanger: true, pageSizeOptions: ['10', '20', '50'] }}
                        expandable={{
                            expandedRowRender: (record) => <ExpandedRow record={record} />,
                            rowExpandable: () => true,
                        }}
                    />
                )}
            </Spin>
        </div>
    );
}
