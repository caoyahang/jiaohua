/**
 * 应用外壳：AntD Layout，顶部导航（页面菜单 + 登录状态 + 退出），内容区渲染路由。
 */
import { Layout, Menu, Tag, Button, Space } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { BrowserRouter, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import AppRoutes from './router';

const { Header, Content } = Layout;

/** 顶部导航项：与 pages/ 一一对应 */
const NAV_ITEMS = [
  { key: '/predict', label: '质量预测' },
  { key: '/optimize', label: '方案优化' },
  { key: '/recipes', label: '历史方案' },
  { key: '/feedback', label: '结果回写' },
];

function Shell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { username, demo, logout } = useAuthStore();

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  // 登录页不显示导航外壳
  if (location.pathname === '/login') {
    return <AppRoutes />;
  }

  return (
    <Layout className="min-h-full">
      <Header className="flex items-center justify-between px-4">
        <Space size="large" className="flex-1">
          <span className="text-white text-base font-bold whitespace-nowrap">
            智能配煤系统
          </span>
          <Menu
            theme="dark"
            mode="horizontal"
            className="flex-1 min-w-0"
            selectedKeys={[location.pathname]}
            items={NAV_ITEMS}
            onClick={({ key }) => navigate(key)}
          />
        </Space>
        <Space>
          {demo && <Tag color="warning">演示模式</Tag>}
          <span className="text-white">{demo ? '演示用户' : username}</span>
          <Button
            size="small"
            icon={<LogoutOutlined />}
            onClick={onLogout}
          >
            退出
          </Button>
        </Space>
      </Header>
      <Content className="p-4">
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
