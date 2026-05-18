import { Modal, Form, Input, InputNumber, Select, message } from 'antd';
import { useMutation } from '@tanstack/react-query';
import { createStay } from '../../api/endpoints';
import type { ICUStay } from '../../types/domain';

interface NewMonitoringModalProps {
    open: boolean;
    onClose: () => void;
    onCreated?: (stay: ICUStay) => void;
}

export default function NewMonitoringModal({ open, onClose, onCreated }: NewMonitoringModalProps) {
    const [form] = Form.useForm();

    const mutation = useMutation({
        mutationFn: (body: {
            patient_name: string; age?: number; gender?: string;
        }) => createStay(body),
        onSuccess: (stay) => {
            message.success('Monitoring session created');
            form.resetFields();
            onClose();
            onCreated?.(stay);
        },
        onError: () => message.error('Failed to create monitoring session'),
    });

    return (
        <Modal
            title="New Monitoring"
            open={open}
            onCancel={() => { form.resetFields(); onClose(); }}
            onOk={() => form.submit()}
            confirmLoading={mutation.isPending}
            okText="Create"
        >
            <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)}>
                <Form.Item name="patient_name" label="Patient Name" rules={[{ required: true, message: 'Patient name is required' }]}>
                    <Input placeholder="Full name" />
                </Form.Item>
                <Form.Item name="age" label="Age">
                    <InputNumber min={0} max={130} style={{ width: '100%' }} placeholder="Age" />
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
    );
}
