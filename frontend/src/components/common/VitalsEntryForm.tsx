import { useState } from 'react';
import { Card, Form, InputNumber, Select, Button, Row, Col, Typography, message } from 'antd';
import { useMutation, useQuery } from '@tanstack/react-query';
import { getStays, ingestVitals } from '../../api/endpoints';
import type { ICUStay } from '../../types/domain';

const { Text } = Typography;

const VITAL_FIELDS = ['HR', 'O2Sat', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'Lactate', 'WBC', 'Creatinine'];

interface VitalsEntryFormProps {
    stayId?: string;
}

export default function VitalsEntryForm({ stayId }: VitalsEntryFormProps) {
    const [form] = Form.useForm();
    const [selectedStay, setSelectedStay] = useState<string | undefined>(stayId);

    const { data: stays } = useQuery({
        queryKey: ['stays'],
        queryFn: getStays,
        enabled: !stayId,
    });

    const runningStays = (stays ?? []).filter((s) => s.status === 'RUNNING');
    const activeStay = stayId ?? selectedStay;

    const mutation = useMutation({
        mutationFn: (body: { hour: number; record: Record<string, number> }) =>
            ingestVitals(activeStay!, body),
        onSuccess: () => {
            message.success('Vitals pushed');
            const current = form.getFieldValue('hour');
            form.resetFields();
            form.setFieldValue('hour', typeof current === 'number' ? current + 1 : 0);
        },
        onError: () => message.error('Failed to push vitals'),
    });

    const onFinish = (values: Record<string, number | undefined>) => {
        if (!activeStay) {
            message.warning('Select a stay first');
            return;
        }
        const { hour, ...rest } = values;
        if (hour == null) {
            message.warning('Hour is required');
            return;
        }
        const record: Record<string, number> = {};
        for (const f of VITAL_FIELDS) {
            const val = rest[f];
            if (val != null) record[f] = val;
        }
        mutation.mutate({ hour: hour as number, record });
    };

    return (
        <Card title="Manual Vitals Entry">
            <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ hour: 0 }}>
                {!stayId && (
                    <Form.Item label="ICU Stay" required>
                        <Select
                            placeholder="Select a RUNNING stay"
                            value={selectedStay}
                            onChange={setSelectedStay}
                            options={runningStays.map((s: ICUStay) => ({
                                value: s.stay_id,
                                label: `${s.patient_name || s.source_record || s.stay_id.slice(0, 8)} (${s.stay_id.slice(0, 8)})`,
                            }))}
                        />
                    </Form.Item>
                )}
                <Form.Item name="hour" label="Hour" rules={[{ required: true, message: 'Hour is required' }]}>
                    <InputNumber min={0} style={{ width: 160 }} />
                </Form.Item>
                <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    Leave a field blank to omit it from the record.
                </Text>
                <Row gutter={[12, 0]}>
                    {VITAL_FIELDS.map((f) => (
                        <Col xs={12} sm={8} md={6} key={f}>
                            <Form.Item name={f} label={f}>
                                <InputNumber style={{ width: '100%' }} step={0.1} placeholder={f} />
                            </Form.Item>
                        </Col>
                    ))}
                </Row>
                <Button type="primary" htmlType="submit" loading={mutation.isPending}>
                    Push
                </Button>
            </Form>
        </Card>
    );
}
