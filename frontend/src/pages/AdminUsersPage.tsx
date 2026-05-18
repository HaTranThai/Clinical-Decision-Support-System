import { Table, Button, Typography, Modal, Form, Input, Select, message, Tag, Space } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUsers, getRoles, createUser, updateUser, deleteUser } from '../api/endpoints';
import { getMe } from '../api/auth';
import { useState } from 'react';

const { Title } = Typography;

function errorDetail(err: any, fallback: string): string {
    return err?.response?.data?.detail || fallback;
}

export default function AdminUsersPage() {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const [form] = Form.useForm();
    const { data: users, isLoading } = useQuery({ queryKey: ['users'], queryFn: getUsers });
    const { data: roles } = useQuery({ queryKey: ['roles'], queryFn: getRoles });
    const { data: me } = useQuery({ queryKey: ['me'], queryFn: getMe });

    const refresh = () => qc.invalidateQueries({ queryKey: ['users'] });

    const createMut = useMutation({
        mutationFn: createUser,
        onSuccess: () => {
            message.success('User created');
            refresh();
            setOpen(false);
            form.resetFields();
        },
        onError: (err) => message.error(errorDetail(err, 'Failed to create user')),
    });

    const setActiveMut = useMutation({
        mutationFn: ({ id, active }: { id: string; active: boolean }) => updateUser(id, { is_active: active }),
        onSuccess: () => {
            message.success('User updated');
            refresh();
        },
        onError: (err) => message.error(errorDetail(err, 'Failed to update user')),
    });

    const deleteMut = useMutation({
        mutationFn: deleteUser,
        onSuccess: () => {
            message.success('User deleted');
            refresh();
        },
        onError: (err) => message.error(errorDetail(err, 'Failed to delete user')),
    });

    const confirmDelete = (user: any) => {
        Modal.confirm({
            title: `Delete user "${user.username}"?`,
            content: 'This permanently removes the account. Use Deactivate to keep history.',
            okText: 'Delete',
            okType: 'danger',
            onOk: () => deleteMut.mutate(user.user_id),
        });
    };

    const columns = [
        { title: 'Username', dataIndex: 'username' },
        { title: 'Display Name', dataIndex: 'display_name' },
        { title: 'Role', dataIndex: 'role_name', render: (r: string) => <Tag color={r === 'admin' ? 'gold' : 'blue'}>{r}</Tag> },
        { title: 'Active', dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? 'Yes' : 'No'}</Tag> },
        { title: 'Created', dataIndex: 'created_at', render: (t: string) => t?.slice(0, 19) },
        {
            title: 'Actions',
            render: (_: unknown, r: any) => {
                if (me && r.user_id === me.user_id) {
                    return <Tag>Your account</Tag>;
                }
                return (
                    <Space>
                        {r.is_active ? (
                            <Button size="small" onClick={() => setActiveMut.mutate({ id: r.user_id, active: false })}>
                                Deactivate
                            </Button>
                        ) : (
                            <Button size="small" onClick={() => setActiveMut.mutate({ id: r.user_id, active: true })}>
                                Reactivate
                            </Button>
                        )}
                        <Button size="small" danger onClick={() => confirmDelete(r)}>
                            Delete
                        </Button>
                    </Space>
                );
            },
        },
    ];

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>User Management</Title>
                <Button type="primary" onClick={() => setOpen(true)}>Add User</Button>
            </div>
            <Table dataSource={users} columns={columns} rowKey="user_id" loading={isLoading} />
            <Modal
                title="Create User"
                open={open}
                onCancel={() => setOpen(false)}
                onOk={() => form.submit()}
                confirmLoading={createMut.isPending}
            >
                <Form form={form} layout="vertical" onFinish={(v) => createMut.mutate(v)}>
                    <Form.Item name="username" label="Username" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="password" label="Password" rules={[{ required: true }]}>
                        <Input.Password />
                    </Form.Item>
                    <Form.Item name="display_name" label="Display Name">
                        <Input />
                    </Form.Item>
                    <Form.Item name="role_id" label="Role" rules={[{ required: true }]}>
                        <Select
                            placeholder="Select role"
                            options={(roles ?? []).map((r) => ({ value: r.role_id, label: r.name }))}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
