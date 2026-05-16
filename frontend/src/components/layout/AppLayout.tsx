import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, Avatar, Dropdown, Space, Badge } from 'antd';
import {
    HeartOutlined,
    AlertOutlined,
    DesktopOutlined,
    BarChartOutlined,
    SettingOutlined,
    TeamOutlined,
    LogoutOutlined,
    UserOutlined,
    ExperimentOutlined,
    ApiOutlined,
    DatabaseOutlined,
} from '@ant-design/icons';
import { getMe } from '../../api/auth';
import type { UserProfile } from '../../types/domain';

const { Sider, Header, Content } = Layout;
const { Text } = Typography;

export default function AppLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const [user, setUser] = useState<UserProfile | null>(null);
    const [collapsed, setCollapsed] = useState(false);

    useEffect(() => {
        getMe().then(setUser).catch(() => {
            localStorage.removeItem('token');
            navigate('/login');
        });
    }, [navigate]);

    const menuItems = [
        { key: '/live', icon: <HeartOutlined />, label: 'Live Monitor' },
        { key: '/alerts', icon: <AlertOutlined />, label: 'Alerts' },
        { key: '/sessions', icon: <DesktopOutlined />, label: 'Sessions' },
        { key: '/analytics', icon: <BarChartOutlined />, label: 'Analytics' },
        {
            key: 'mlops-group',
            type: 'group' as const,
            label: 'MLOps',
            children: [
                { key: '/mlops', icon: <ExperimentOutlined />, label: 'Dashboard' },
                { key: '/mlops/experiments', icon: <ApiOutlined />, label: 'Experiments' },
                { key: '/mlops/registry', icon: <DatabaseOutlined />, label: 'Model Registry' },
            ],
        },
        ...(user?.role === 'admin'
            ? [
                { key: '/admin/settings', icon: <SettingOutlined />, label: 'Settings' },
                { key: '/admin/users', icon: <TeamOutlined />, label: 'Users' },
            ]
            : []),
    ];

    const userMenu = {
        items: [
            {
                key: 'logout',
                icon: <LogoutOutlined />,
                label: 'Logout',
                onClick: () => {
                    localStorage.removeItem('token');
                    navigate('/login');
                },
            },
        ],
    };

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider
                collapsible
                collapsed={collapsed}
                onCollapse={setCollapsed}
                width={220}
                style={{ paddingTop: 16 }}
            >
                <div style={{ textAlign: 'center', padding: '0 16px 24px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                    <HeartOutlined style={{ fontSize: 28, color: '#00d4aa' }} />
                    {!collapsed && (
                        <Text strong style={{ display: 'block', marginTop: 8, color: '#e5e7eb', fontSize: 14 }}>
                            ECG CDSS
                        </Text>
                    )}
                </div>
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={({ key }) => navigate(key)}
                    style={{ background: 'transparent', borderRight: 0, marginTop: 8 }}
                />
            </Sider>
            <Layout>
                <Header
                    style={{
                        background: 'rgba(17, 24, 39, 0.9)',
                        backdropFilter: 'blur(10px)',
                        borderBottom: '1px solid rgba(255,255,255,0.08)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0 24px',
                    }}
                >
                    <Text style={{ fontSize: 16, fontWeight: 500 }}>
                        Real-time Arrhythmia Detection
                    </Text>
                    <Dropdown menu={userMenu} placement="bottomRight">
                        <Space style={{ cursor: 'pointer' }}>
                            <Avatar icon={<UserOutlined />} style={{ background: '#00d4aa' }} />
                            <Text style={{ color: '#e5e7eb' }}>{user?.display_name || user?.username}</Text>
                        </Space>
                    </Dropdown>
                </Header>
                <Content style={{ padding: 24, overflow: 'auto' }}>
                    <Outlet />
                </Content>
            </Layout>
        </Layout>
    );
}
