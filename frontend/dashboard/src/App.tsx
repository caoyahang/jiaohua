/**
 * 大屏外壳：顶部品牌条（名称 + 实时时钟 + 登录状态 + 退出），内容区渲染路由。
 * 领导驾驶舱为单页大屏，无多页导航。
 */
import { useState } from 'react';
import { Layout, Tag, Button, Space } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { BrowserRouter, useLocation, useNavigate } from 'react-router-dom';
import { useInterval } from 'ahooks';
import { useAuthStore } from './stores/auth';
import AppRoutes from './router';

const { Header, Content } = Layout;

/** 实时时钟：1 秒刷新，格式 YYYY-MM-DD HH:mm:ss */
function useClock(): string {
  const fmt = () => {
    const d = new Date();
    const p = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  };
  const [now, setNow] = useState(fmt);
  useInterval(() => setNow(fmt()), 1000);
  return now;
}

function Shell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { username, demo, logout } = useAuthStore();
  const clock = useClock();

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  // 登录页不显示大屏外壳
  if (location.pathname === '/login') {
    return <AppRoutes />;
  }

  return (
    <Layout className="min-h-full bg-darkPage">
      <Header className="flex items-center justify-between px-4 bg-darkPage border-b border-darkBorder">
        <span className="text-darkText text-lg font-bold whitespace-nowrap">
          焦化厂智能化平台 · 领导驾驶舱
        </span>
        <Space size="middle">
          <span className="text-darkTextSecondary font-mono">{clock}</span>
          {demo && <Tag color="warning">演示模式</Tag>}
          <span className="text-darkText">{demo ? '演示用户' : username}</span>
          <Button size="small" icon={<LogoutOutlined />} onClick={onLogout}>
            退出
          </Button>
        </Space>
      </Header>
      <Content className="p-3">
        <AppRoutes />
      </Content>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
