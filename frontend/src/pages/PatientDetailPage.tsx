import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Table, Tag, Button, Typography, Row, Space, Popconfirm, Modal, Form, Input, InputNumber, Select, message, Spin } from 'antd';
import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPatient, updatePatient, createStayForPatient, stopStay } from '../api/endpoints';
import { useLiveMonitorStore } from '../stores/liveMonitorStore';
import type { ICUStay } from '../types/domain';

const { Title } = Typography;

export default function PatientDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const selectStay = useLiveMonitorStore((s) => s.selectStay);
    const [editOpen, setEditOpen] = useState(false);
    const [form] = Form.useForm();

    const { data: patient, isLoading } = useQuery({
        queryKey: ['patient', id],
        queryFn: () => getPatient(id!),
        enabled: !!id,
    });

    const mutation = useMutation({
        mutationFn: (body: { name?: string; external_ref?: string; age?: number; gender?: string }) =>
            updatePatient(id!, body),
        onSuccess: () => {
            message.success('Patient updated');
            queryClient.invalidateQueries({ queryKey: ['patient', id] });
            setEditOpen(false);
        },
        onError: () => message.error('Failed to update patient'),
    });

    const createStayMutation = useMutation({
        mutationFn: () => createStayForPatient(id!, {}),
        onSuccess: () => {
            message.success('ICU stay created');
            queryClient.invalidateQueries({ queryKey: ['patient', id] });
        },
        onError: () => message.error('Failed to create ICU stay'),
    });

    const stopMutation = useMutation({
        mutationFn: (stayId: string) => stopStay(stayId),
        onSuccess: () => {
            message.success('Monitoring stopped');
            queryClient.invalidateQueries({ queryKey: ['patient', id] });
        },
        onError: () => message.error('Failed to stop monitoring'),
    });

    const openEdit = () => {
        form.setFieldsValue({
            name: patient?.name,
            external_ref: patient?.external_ref,
            age: patient?.age,
            gender: patient?.gender,
        });
        setEditOpen(true);
    };

    const openStay = (stay: ICUStay) => {
        selectStay(stay.stay_id);
        navigate('/live');
    };

    const stayColumns = [
        { title: 'Record', dataIndex: 'source_record', render: (v: string | null, r: ICUStay) => v || r.stay_id.slice(0, 8) },
        {
            title: 'Status',
            dataIndex: 'status',
            render: (s: string) => <Tag color={s === 'RUNNING' ? 'green' : 'default'}>{s}</Tag>,
        },
        { title: 'Start', dataIndex: 'start_time', render: (t: string | null) => t?.slice(0, 19) || '—' },
        {
            title: '',
            render: (_: any, r: ICUStay) => (
                <Space>
                    <Button size="small" type="link" onClick={() => openStay(r)}>Open</Button>
                    {r.status === 'RUNNING' && (
                        <Popconfirm
                            title="Stop monitoring?"
                            description="This will end the ICU stay."
                            okText="Stop"
                            cancelText="Cancel"
                            onConfirm={() => stopMutation.mutate(r.stay_id)}
                        >
                            <Button size="small" type="link" danger loading={stopMutation.isPending}>Stop</Button>
                        </Popconfirm>
                    )}
                </Space>
            ),
        },
    ];

    if (isLoading) {
        return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>;
    }

    return (
        <div>
            <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>Patient Detail</Title>
                <Button icon={<EditOutlined />} onClick={openEdit}>Edit</Button>
            </Row>

            {patient && (
                <Card style={{ marginBottom: 16 }}>
                    <Descriptions column={3}>
                        <Descriptions.Item label="Name">{patient.name || '—'}</Descriptions.Item>
                        <Descriptions.Item label="External Ref">{patient.external_ref || '—'}</Descriptions.Item>
                        <Descriptions.Item label="Age">{patient.age ?? '—'}</Descriptions.Item>
                        <Descriptions.Item label="Gender">{patient.gender || '—'}</Descriptions.Item>
                        <Descriptions.Item label="ICU Stays">{patient.stay_count}</Descriptions.Item>
                    </Descriptions>
                </Card>
            )}

            <Card
                title="ICU Stay History"
                extra={
                    <Popconfirm
                        title="Start a new ICU stay?"
                        description="A new monitoring session will be created for this patient."
                        okText="Create"
                        cancelText="Cancel"
                        onConfirm={() => createStayMutation.mutate()}
                    >
                        <Button type="primary" icon={<PlusOutlined />} loading={createStayMutation.isPending}>
                            New ICU Stay
                        </Button>
                    </Popconfirm>
                }
            >
                <Table
                    dataSource={patient?.stays}
                    columns={stayColumns}
                    rowKey="stay_id"
                    pagination={{ pageSize: 10 }}
                    size="small"
                />
            </Card>

            <Modal
                title="Edit Patient"
                open={editOpen}
                onCancel={() => setEditOpen(false)}
                onOk={() => form.submit()}
                confirmLoading={mutation.isPending}
                okText="Save"
            >
                <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)}>
                    <Form.Item name="name" label="Name" rules={[{ required: true, message: 'Name is required' }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="external_ref" label="External Ref">
                        <Input />
                    </Form.Item>
                    <Form.Item name="age" label="Age">
                        <InputNumber min={0} max={130} style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name="gender" label="Gender">
                        <Select
                            allowClear
                            options={[
                                { value: 'M', label: 'Male' },
                                { value: 'F', label: 'Female' },
                                { value: 'O', label: 'Other' },
                            ]}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
