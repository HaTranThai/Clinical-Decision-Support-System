import { Card, Form, InputNumber, Button, Typography, message, Row, Col, Divider, Alert } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSettings, updateSettings } from '../api/endpoints';
import { useEffect } from 'react';

const { Title, Text } = Typography;

export default function AdminSettingsPage() {
    const queryClient = useQueryClient();
    const [form] = Form.useForm();
    const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: getSettings });

    useEffect(() => {
        if (settings) {
            const values: Record<string, number | string | null> = {};
            settings.forEach((s) => {
                values[s.key] = typeof s.value === 'string' ? parseFloat(s.value) : s.value;
            });
            form.setFieldsValue(values);
        }
    }, [settings, form]);

    const mutation = useMutation({
        mutationFn: updateSettings,
        onSuccess: () => {
            message.success('Settings saved');
            queryClient.invalidateQueries({ queryKey: ['settings'] });
        },
        onError: () => message.error('Failed to save settings'),
    });

    return (
        <div>
            <Title level={4} style={{ marginBottom: 16 }}>System Settings</Title>
            <Card>
                <Form form={form} layout="vertical" onFinish={(v) => mutation.mutate(v)}>
                    <Title level={5}>Sepsis Alert Rules</Title>
                    <Text type="secondary">
                        Cảnh báo phát ra khi điểm nguy cơ vượt ngưỡng và duy trì đủ số giờ liên tục.
                    </Text>
                    <Row gutter={16} style={{ marginTop: 12 }}>
                        <Col span={8}>
                            <Form.Item name="alert_risk_threshold" label="Ngưỡng nguy cơ (0–1)">
                                <InputNumber step={0.05} min={0} max={1} style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name="sustained_hours" label="Số giờ cao liên tục">
                                <InputNumber min={1} max={48} style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                        <Col span={8}>
                            <Form.Item name="cooldown_hours" label="Thời gian nghỉ giữa 2 cảnh báo (giờ)">
                                <InputNumber min={0} max={72} style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Divider />

                    <Title level={5}>Replay / Mô phỏng</Title>
                    <Row gutter={16}>
                        <Col span={8}>
                            <Form.Item name="hour_interval_sec" label="Tốc độ replay (giây / giờ ICU)">
                                <InputNumber step={0.5} min={0.1} style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Alert
                        type="info"
                        showIcon
                        style={{ marginBottom: 16 }}
                        message="Lưu cấu hình vào cơ sở dữ liệu. Các service streaming hiện đọc cấu hình từ biến môi trường docker-compose lúc khởi động — đổi giá trị runtime cần khởi động lại service tương ứng."
                    />

                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={mutation.isPending} size="large">
                            Save Settings
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
}
