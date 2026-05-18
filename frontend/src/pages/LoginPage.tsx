import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Typography, message, Space } from 'antd';
import { MedicineBoxOutlined, LockOutlined, UserOutlined } from '@ant-design/icons';
import { login } from '../api/auth';

const { Title, Text, Paragraph } = Typography;

export default function LoginPage() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);

    const onFinish = async (values: { username: string; password: string }) => {
        setLoading(true);
        try {
            const data = await login(values.username, values.password);
            localStorage.setItem('token', data.access_token);
            message.success('Login successful');
            navigate('/live');
        } catch {
            message.error('Invalid credentials');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #0a0e17 0%, #111827 50%, #0f172a 100%)',
            }}
        >
            <Card
                style={{
                    width: 420,
                    background: 'rgba(26, 32, 53, 0.9)',
                    backdropFilter: 'blur(20px)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 16,
                }}
            >
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <MedicineBoxOutlined style={{ fontSize: 48, color: '#00d4aa', marginBottom: 16 }} />
                    <Title level={3} style={{ color: '#e5e7eb', marginBottom: 4 }}>
                        Sepsis Early-Warning CDSS
                    </Title>
                    <Text style={{ color: '#9ca3af' }}>
                        Real-time ICU Sepsis Risk Monitoring
                    </Text>
                </div>

                <Form layout="vertical" onFinish={onFinish} autoComplete="off">
                    <Form.Item name="username" rules={[{ required: true, message: 'Username required' }]}>
                        <Input
                            prefix={<UserOutlined style={{ color: '#9ca3af' }} />}
                            placeholder="Username"
                            size="large"
                            style={{ borderRadius: 8 }}
                        />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, message: 'Password required' }]}>
                        <Input.Password
                            prefix={<LockOutlined style={{ color: '#9ca3af' }} />}
                            placeholder="Password"
                            size="large"
                            style={{ borderRadius: 8 }}
                        />
                    </Form.Item>
                    <Form.Item>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            block
                            size="large"
                            style={{
                                borderRadius: 8,
                                height: 48,
                                fontSize: 16,
                                fontWeight: 600,
                                background: 'linear-gradient(135deg, #00d4aa, #00b894)',
                            }}
                        >
                            Sign In
                        </Button>
                    </Form.Item>
                </Form>

                <Paragraph style={{ textAlign: 'center', color: '#6b7280', fontSize: 12 }}>
                    Demo: admin / admin123
                </Paragraph>
            </Card>
        </div>
    );
}
