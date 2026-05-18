import { useState } from 'react';
import { Table, Tag, Button, Drawer, Form, Input, Typography, Space, message, Select } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAlerts, getAlertDetail, ackAlert, dismissAlert } from '../api/endpoints';
import type { Alert } from '../types/domain';

const { Title, Text } = Typography;
const { TextArea } = Input;

function severityColor(sev: number | null): string {
    if (sev != null && sev >= 3) return 'red';
    if (sev != null && sev >= 2) return 'orange';
    return 'gold';
}

function statusColor(s: string): string {
    if (s === 'NEW') return 'red';
    if (s === 'ACK') return 'blue';
    return 'default';
}

export default function AlertsPage() {
    const queryClient = useQueryClient();
    const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
    const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
    const [actionType, setActionType] = useState<'ack' | 'dismiss' | null>(null);
    const [form] = Form.useForm();

    const { data: alerts, isLoading } = useQuery({
        queryKey: ['alerts', statusFilter],
        queryFn: () => getAlerts(statusFilter ? { status: statusFilter } : undefined),
        refetchInterval: 5000,
    });

    const { data: alertDetail } = useQuery({
        queryKey: ['alertDetail', selectedAlertId],
        queryFn: () => getAlertDetail(selectedAlertId!),
        enabled: !!selectedAlertId,
    });

    const ackMutation = useMutation({
        mutationFn: (body: { reason?: string; note?: string }) => ackAlert(selectedAlertId!, body),
        onSuccess: () => {
            message.success('Alert acknowledged');
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
            queryClient.invalidateQueries({ queryKey: ['alertDetail'] });
            setActionType(null);
            form.resetFields();
        },
    });

    const dismissMutation = useMutation({
        mutationFn: (body: { reason?: string; note?: string }) => dismissAlert(selectedAlertId!, body),
        onSuccess: () => {
            message.success('Alert dismissed');
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
            queryClient.invalidateQueries({ queryKey: ['alertDetail'] });
            setActionType(null);
            form.resetFields();
        },
    });

    const columns = [
        {
            title: 'Severity',
            dataIndex: 'severity',
            render: (v: number | null) => <Tag color={severityColor(v)}>Severity {v ?? '—'}</Tag>,
        },
        {
            title: 'Status',
            dataIndex: 'status',
            render: (s: string) => <Tag color={statusColor(s)}>{s}</Tag>,
        },
        { title: 'Start Time', dataIndex: 'start_time', render: (t: string) => t?.slice(0, 19) || '—' },
        { title: 'Last Update', dataIndex: 'last_update', render: (t: string) => t?.slice(0, 19) || '—' },
        { title: 'Stay', dataIndex: 'stay_id', render: (s: string) => s?.slice(0, 8) + '…' },
        {
            title: 'Actions',
            render: (_: any, record: Alert) => (
                <Button size="small" onClick={() => setSelectedAlertId(record.alert_id)}>
                    Detail
                </Button>
            ),
        },
    ];

    return (
        <div>
            <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
                <Title level={4} style={{ margin: 0 }}>Sepsis Alerts</Title>
                <Select
                    placeholder="Filter by status"
                    allowClear
                    style={{ width: 200 }}
                    onChange={(v) => setStatusFilter(v)}
                    options={[
                        { value: 'NEW', label: 'NEW' },
                        { value: 'ACK', label: 'ACK' },
                        { value: 'DISMISSED', label: 'DISMISSED' },
                    ]}
                />
            </Space>

            <Table
                dataSource={alerts}
                columns={columns}
                rowKey="alert_id"
                loading={isLoading}
                pagination={{ pageSize: 20 }}
            />

            <Drawer
                title="Sepsis Alert Detail"
                open={!!selectedAlertId}
                onClose={() => { setSelectedAlertId(null); setActionType(null); }}
                width={500}
            >
                {alertDetail && (
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        <div>
                            <Tag color={severityColor(alertDetail.severity)} style={{ fontSize: 16, padding: '4px 16px' }}>
                                Severity {alertDetail.severity ?? '—'}
                            </Tag>
                            <Tag color={statusColor(alertDetail.status)}>{alertDetail.status}</Tag>
                        </div>
                        <div><Text strong>Stay ID:</Text> {alertDetail.stay_id}</div>
                        <div><Text strong>Start Time:</Text> {alertDetail.start_time?.slice(0, 19) || '—'}</div>
                        <div><Text strong>Last Update:</Text> {alertDetail.last_update?.slice(0, 19) || '—'}</div>
                        <div>
                            <Text strong>Evidence:</Text>
                            <pre style={{ background: '#1a2035', padding: 12, borderRadius: 8, fontSize: 12, overflow: 'auto' }}>
                                {JSON.stringify(alertDetail.evidence_json, null, 2)}
                            </pre>
                        </div>

                        {alertDetail.status === 'NEW' && (
                            <Space>
                                <Button type="primary" onClick={() => setActionType('ack')}>ACK</Button>
                                <Button danger onClick={() => setActionType('dismiss')}>DISMISS</Button>
                            </Space>
                        )}

                        {actionType && (
                            <Form form={form} layout="vertical" onFinish={(values) => {
                                if (actionType === 'ack') ackMutation.mutate(values);
                                else dismissMutation.mutate(values);
                            }}>
                                <Form.Item name="reason" label="Reason">
                                    <Input placeholder="Enter reason" />
                                </Form.Item>
                                <Form.Item name="note" label="Note">
                                    <TextArea rows={3} placeholder="Additional notes" />
                                </Form.Item>
                                <Button type="primary" htmlType="submit" loading={ackMutation.isPending || dismissMutation.isPending}>
                                    Submit {actionType.toUpperCase()}
                                </Button>
                            </Form>
                        )}

                        {alertDetail.actions.length > 0 && (
                            <div>
                                <Text strong>Action History:</Text>
                                {alertDetail.actions.map((act) => (
                                    <div key={act.action_id} style={{ padding: 8, margin: '4px 0', background: '#1a2035', borderRadius: 8 }}>
                                        <Tag>{act.action_type}</Tag>
                                        <Text style={{ fontSize: 12 }}>{act.action_time?.slice(0, 19)}</Text>
                                        {act.reason && <div><Text style={{ fontSize: 12 }}>Reason: {act.reason}</Text></div>}
                                        {act.note && <div><Text style={{ fontSize: 12 }}>Note: {act.note}</Text></div>}
                                    </div>
                                ))}
                            </div>
                        )}
                    </Space>
                )}
            </Drawer>
        </div>
    );
}
