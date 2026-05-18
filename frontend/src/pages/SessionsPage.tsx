import { useState } from 'react';
import { Table, Tag, Button, Typography, Row, Popconfirm, message, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getStays, stopStay } from '../api/endpoints';
import NewMonitoringModal from '../components/common/NewMonitoringModal';
import type { ICUStay } from '../types/domain';

const { Title } = Typography;

export default function SessionsPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [modalOpen, setModalOpen] = useState(false);
    const { data: stays, isLoading } = useQuery({
        queryKey: ['stays'],
        queryFn: getStays,
        refetchInterval: 10000,
    });

    const stopMutation = useMutation({
        mutationFn: (id: string) => stopStay(id),
        onSuccess: () => {
            message.success('Monitoring stopped');
            queryClient.invalidateQueries({ queryKey: ['stays'] });
        },
        onError: () => message.error('Failed to stop monitoring'),
    });

    const columns = [
        {
            title: 'Record',
            dataIndex: 'source_record',
            render: (v: string, r: ICUStay) => v || r.stay_id.slice(0, 8),
        },
        {
            title: 'Patient',
            dataIndex: 'patient_id',
            render: (v: string) => v || '—',
        },
        {
            title: 'Status',
            dataIndex: 'status',
            render: (s: string) => (
                <span>
                    <span className={`status-dot ${s === 'RUNNING' ? 'running' : 'stopped'}`} />
                    <Tag color={s === 'RUNNING' ? 'green' : 'default'}>{s}</Tag>
                </span>
            ),
        },
        { title: 'Start', dataIndex: 'start_time', render: (t: string) => t?.slice(0, 19) || '—' },
        {
            title: '',
            render: (_: any, r: ICUStay) => (
                <Space>
                    <Button size="small" type="link" onClick={() => navigate(`/stays/${r.stay_id}`)}>
                        View
                    </Button>
                    {r.status === 'RUNNING' && (
                        <Popconfirm
                            title="Stop monitoring?"
                            description="This will end the ICU stay."
                            okText="Stop"
                            cancelText="Cancel"
                            onConfirm={() => stopMutation.mutate(r.stay_id)}
                        >
                            <Button size="small" type="link" danger loading={stopMutation.isPending}>
                                Stop
                            </Button>
                        </Popconfirm>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <div>
            <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>ICU Stays</Title>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                    New Monitoring
                </Button>
            </Row>
            <Table dataSource={stays} columns={columns} rowKey="stay_id" loading={isLoading} pagination={{ pageSize: 20 }} />
            <NewMonitoringModal
                open={modalOpen}
                onClose={() => setModalOpen(false)}
                onCreated={() => queryClient.invalidateQueries({ queryKey: ['stays'] })}
            />
        </div>
    );
}
