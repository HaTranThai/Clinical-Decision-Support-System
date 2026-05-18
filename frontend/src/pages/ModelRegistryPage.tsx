import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Button, Card, Col, message, Modal, Row, Space, Spin, Statistic, Table, Tag, Tooltip, Typography, Empty,
} from 'antd';
import { ReloadOutlined, StarFilled } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { getMLOpsRegistry, promoteModelVersion, archiveModelVersion } from '../api/endpoints';
import { getMe } from '../api/auth';
import type { ModelVersion, UserProfile } from '../types/domain';

const { Title, Text } = Typography;

// ─── helpers ────────────────────────────────────────────────────────────────

const stageColor: Record<string, string> = {
    Production: 'success',
    Staging: 'processing',
    Archived: 'default',
    None: 'warning',
};

function fmtDt(iso: string | null | undefined): string {
    if (!iso) return '-';
    return dayjs(iso).format('YYYY-MM-DD HH:mm');
}

function parseAuroc(tags: Record<string, string>): string {
    const v = parseFloat(tags.test_auroc ?? '');
    return isNaN(v) ? '-' : (v * 100).toFixed(2) + '%';
}

function parseAuprc(tags: Record<string, string>): string {
    const v = parseFloat(tags.test_auprc ?? '');
    return isNaN(v) ? '-' : (v * 100).toFixed(2) + '%';
}

function parseSensitivity(tags: Record<string, string>): string {
    const v = parseFloat(tags.test_sensitivity ?? '');
    return isNaN(v) ? '-' : (v * 100).toFixed(2) + '%';
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ModelRegistryPage() {
    const queryClient = useQueryClient();
    const [user, setUser] = useState<UserProfile | null>(null);
    const isAdmin = user?.role === 'admin';

    useEffect(() => {
        getMe().then(setUser).catch(() => {});
    }, []);

    const { data: registry, isLoading, isFetching, refetch } = useQuery({
        queryKey: ['mlops-registry'],
        queryFn: getMLOpsRegistry,
    });

    const promoteMutation = useMutation({
        mutationFn: (version: string) => promoteModelVersion(version),
        onSuccess: () => {
            message.success('Model promoted to Production');
            queryClient.invalidateQueries({ queryKey: ['mlops-registry'] });
        },
        onError: () => {
            message.error('Failed to promote model');
        },
    });

    const archiveMutation = useMutation({
        mutationFn: (version: string) => archiveModelVersion(version),
        onSuccess: () => {
            message.success('Model archived');
            queryClient.invalidateQueries({ queryKey: ['mlops-registry'] });
        },
        onError: () => {
            message.error('Failed to archive model');
        },
    });

    const handlePromote = (version: string) => {
        Modal.confirm({
            title: `Promote version ${version} to Production?`,
            content: 'This will replace the current Production model.',
            okText: 'Promote',
            okType: 'primary',
            onOk: () => promoteMutation.mutate(version),
        });
    };

    const handleArchive = (version: string) => {
        Modal.confirm({
            title: `Archive version ${version}?`,
            content: 'This model will be moved to Archived stage.',
            okText: 'Archive',
            okType: 'danger',
            onOk: () => archiveMutation.mutate(version),
        });
    };

    const versions = registry?.versions ?? [];
    const productionVersion = versions.find((v) => v.stage === 'Production');
    const stagingCount = versions.filter((v) => v.stage === 'Staging').length;

    const actionColumn: ColumnsType<ModelVersion>[number] = {
        title: 'Actions',
        key: 'actions',
        width: 240,
        render: (_: unknown, record: ModelVersion) => {
            const isProduction = record.stage === 'Production';
            const isArchived = record.stage === 'Archived';
            const isStaging = record.stage === 'Staging';
            const isNone = record.stage === 'None';

            return (
                <Space>
                    {(isStaging || isNone) && (
                        <Button
                            size="small"
                            type="primary"
                            onClick={() => handlePromote(record.version)}
                            loading={promoteMutation.isPending && promoteMutation.variables === record.version}
                            disabled={promoteMutation.isPending}
                        >
                            Promote
                        </Button>
                    )}
                    {isProduction && (
                        <Button size="small" type="primary" disabled>
                            Production
                        </Button>
                    )}
                    {(isStaging || isNone) && (
                        <Button
                            size="small"
                            danger
                            onClick={() => handleArchive(record.version)}
                            loading={archiveMutation.isPending && archiveMutation.variables === record.version}
                            disabled={archiveMutation.isPending}
                        >
                            Archive
                        </Button>
                    )}
                    {isArchived && (
                        <Button size="small" disabled>
                            Archived
                        </Button>
                    )}
                </Space>
            );
        },
    };

    const baseColumns: ColumnsType<ModelVersion> = [
        {
            title: 'Version',
            dataIndex: 'version',
            key: 'version',
            width: 90,
            render: (ver: string, record: ModelVersion) => (
                <Space>
                    {record.stage === 'Production' && (
                        <Tooltip title="Current Production model">
                            <StarFilled style={{ color: '#faad14' }} />
                        </Tooltip>
                    )}
                    <Text strong>v{ver}</Text>
                </Space>
            ),
            sorter: (a, b) => parseInt(a.version) - parseInt(b.version),
            defaultSortOrder: 'descend',
        },
        {
            title: 'Stage',
            dataIndex: 'stage',
            key: 'stage',
            width: 110,
            render: (stage: string) => (
                <Tag color={stageColor[stage] ?? 'default'}>{stage}</Tag>
            ),
        },
        {
            title: 'AUROC',
            key: 'auroc',
            width: 100,
            render: (_: unknown, r: ModelVersion) => parseAuroc(r.tags),
            sorter: (a, b) => {
                const va = parseFloat(a.tags.test_auroc ?? '0');
                const vb = parseFloat(b.tags.test_auroc ?? '0');
                return va - vb;
            },
        },
        {
            title: 'AUPRC',
            key: 'auprc',
            width: 100,
            render: (_: unknown, r: ModelVersion) => parseAuprc(r.tags),
            sorter: (a, b) => {
                const va = parseFloat(a.tags.test_auprc ?? '0');
                const vb = parseFloat(b.tags.test_auprc ?? '0');
                return va - vb;
            },
        },
        {
            title: 'Sensitivity',
            key: 'sensitivity',
            width: 110,
            render: (_: unknown, r: ModelVersion) => parseSensitivity(r.tags),
            sorter: (a, b) => {
                const va = parseFloat(a.tags.test_sensitivity ?? '0');
                const vb = parseFloat(b.tags.test_sensitivity ?? '0');
                return va - vb;
            },
        },
        {
            title: 'Registered At',
            dataIndex: 'creation_timestamp',
            key: 'creation_timestamp',
            width: 160,
            render: (v: string | null) => fmtDt(v),
        },
        {
            title: 'Run ID',
            dataIndex: 'run_id',
            key: 'run_id',
            width: 110,
            render: (id: string) => (
                <Tooltip title={id}>
                    <Text code style={{ fontSize: 11 }}>{id.slice(0, 8)}</Text>
                </Tooltip>
            ),
        },
    ];

    const columns: ColumnsType<ModelVersion> = isAdmin
        ? [...baseColumns, actionColumn]
        : baseColumns;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={3} style={{ margin: 0 }}>
                    Model Registry{registry?.model_name ? ` — ${registry.model_name}` : ''}
                </Title>
                <Button
                    icon={<ReloadOutlined />}
                    onClick={() => refetch()}
                    loading={isFetching}
                >
                    Refresh
                </Button>
            </div>

            {/* Summary cards */}
            <Row gutter={16}>
                <Col span={8}>
                    <Card>
                        <Statistic
                            title="Production Version"
                            value={
                                productionVersion
                                    ? `v${productionVersion.version} | AUROC: ${parseAuroc(productionVersion.tags)}`
                                    : 'None'
                            }
                            valueStyle={{ color: productionVersion ? '#00d4aa' : '#9ca3af', fontSize: 18 }}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic title="Staging Versions" value={stagingCount} />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card>
                        <Statistic title="Total Versions" value={versions.length} />
                    </Card>
                </Col>
            </Row>

            {/* Versions table */}
            <Spin spinning={isLoading} tip="Loading registry...">
                {!isLoading && versions.length === 0 ? (
                    <Empty description="No model versions found" style={{ padding: 60 }} />
                ) : (
                    <Table<ModelVersion>
                        dataSource={versions}
                        columns={columns}
                        rowKey="version"
                        size="middle"
                        pagination={false}
                        rowClassName={(record) =>
                            record.stage === 'Production' ? 'production-row' : ''
                        }
                    />
                )}
            </Spin>

            <style>{`
                .production-row > td {
                    background: rgba(0, 212, 170, 0.05) !important;
                }
            `}</style>
        </div>
    );
}
