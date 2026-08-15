/**
 * 登录页：POST /auth/login（真实接口，不降级）。
 * 后端不可达时提示并允许进入「演示模式」；账号密码错误（401）如实报错。
 */
import { useState } from 'react';
import { Alert, Button, Card, Form, Input, message } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { ApiError, BackendUnreachableError, login } from '../api';
import { useAuthStore } from '../stores/auth';

interface LoginForm {
  username: string;
  password: string;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login: saveLogin, enterDemo } = useAuthStore();
  const [loading, setLoading] = useState(false);
  // 后端不可达时展示演示模式入口（明确提示，不与真实登录混淆）
  const [unreachable, setUnreachable] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const onFinish = async (values: LoginForm) => {
    setLoading(true);
    setUnreachable(false);
    try {
      const resp = await login(values.username, values.password);
      saveLogin(resp.access_token, values.username);
      message.success('登录成功');
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof BackendUnreachableError) {
        setUnreachable(true);
      } else if (err instanceof ApiError) {
        message.error(err.message);
      } else {
        message.error('登录失败，请重试');
      }
    } finally {
      setLoading(false);
    }
  };

  const onEnterDemo = () => {
    enterDemo();
    message.warning('已进入演示模式，所有数据均为演示数据');
    navigate('/', { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-darkPage">
      <Card title="焦化厂智能化平台 · 领导驾驶舱" className="w-96 shadow">
        {unreachable && (
          <Alert
            type="warning"
            showIcon
            className="mb-4"
            message="后端服务不可达"
            description="无法连接服务器，可进入演示模式体验界面（所有数据均为演示数据）。"
          />
        )}
        <Form<LoginForm> layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="username"
            label="账号"
            rules={[{ required: true, message: '请输入账号' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="账号" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            登录
          </Button>
          {unreachable && (
            <Button block className="mt-2" onClick={onEnterDemo}>
              进入演示模式
            </Button>
          )}
        </Form>
      </Card>
    </div>
  );
}
