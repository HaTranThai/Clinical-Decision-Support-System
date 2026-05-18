import { useState } from 'react';
import { Table, Button, Input, Typography, Row, Modal, Form, InputNumber, Select, message } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getPatients, createPatient } from '../api/endpoints';
import type { PatientOut } from '../types/domain';

const { Title } = Typography;

export default function PatientsPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [search, setSearch] = useState('');
    const [modalOpen, setModalOpen] = useState(false);
    const [form] = Form.useForm();

    const { data: patients, isLoading } = useQuery({
        queryKey: ['patients', search],
        queryFn: () => getPatients(search || undefined),
    });

    const mutation = useMutation({
        mutationFn: (body: { name: string; external_ref?: string; age?: number; gender?: string }) => createPatient(body),
        onSuccess: () => {
            message.success('Patient created');
            queryClient.invalidateQueries({ queryKey: ['patients'] });
            form.resetFields();
            setModalOpen(false);
        },
        onError: () => message.error('Failed to create patient'),
    });

    const columns = [
        { title: 'Name', dataIndex: 'name', render: (v: string | null) => v || '—' },
        { title: 'External Ref', dataIndex: 'external_ref', render: (v: string | null) => v || '—' },
        { title: 'Age', dataIndex: 'age', render: (v: number | null) => v ?? '—' },
        { title: 'Gender', dataIndex: 'gender', render: (v: string | null) => v || '—' },
        { title: 'Stays', dataIndex: 'stay_count' },
        {
            title: '',
            render: (_: any, r: PatientOut) => (
                <Button size="small" type="link" onClick={() => navigate(`/patients/${r.patient_id}`)}>
                    View
                </Button>
            ),
        },
    ];

    return (
        <div>
            <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>Patients</Title>
                <div style={{ display: 'flex', gap: 8 }}>
                    <Input
                        allowClear
                        prefix={<SearchOutlined />}
                        placeholder="Search patients"
                        style={{ width: 240 }}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                        New Patient
                    </Button>
                </div>
            </Row>

            <Table
                dataSource={patients}
                columns={columns}
                rowKey="patient_id"
                loading={isLoading}
                pagination={{ pageSize: 20 }}
            />

            <Modal
                title="New Patient"
                open={modalOpen}
                onCancel={() => { form.resetFields(); setModalOpen(false); }}
                onOk={() => form.submit()}
                confirmLoading={mutation.isPending}
                okText="Create"
            >
                <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)}>
                    <Form.Item name="name" label="Name" rules={[{ required: true, message: 'Name is required' }]}>
                        <Input placeholder="Full name" />
                    </Form.Item>
                    <Form.Item name="external_ref" label="External Ref">
                        <Input placeholder="e.g. MRN / record id" />
                    </Form.Item>
                    <Form.Item name="age" label="Age">
                        <InputNumber min={0} max={130} style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name="gender" label="Gender">
                        <Select
                            allowClear
                            placeholder="Select gender"
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
