/**
 * 应用外壳：AntD Layout，顶部导航（页面菜单 + 控制模式徽标全站常显 + 登录状态 + 退出）。
 * 控制模式徽标为设计纪律（前端规范§4）：调火工任何页面都要一眼看到当前模式。
 */
import { Layout, Menu, Tag, Button, Space, Tooltip } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { BrowserRouter, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import { useFurnaceStore } from './stores/furnace';
import { colors } from './styles/tokens';
import type { ControlMode } from './api/types';
import AppRoutes from './router';

const { Header, Content } = Layout;

/** 顶部导航项：与 pages/ 一一对应 */
const NAV_ITEMS = [
  { key: '/temp', label: '炉温监控' },
  { key: '/ai-setpoint', label: 'AI推荐值' },
  { key: '/control-mode', label: '控制模式' },
  { key: '/k-coeff', label: 'K系数看板' },
];

/** 控制模式展示配置：manual 灰 / shadow 蓝 / auto 绿（颜色全部来自 tokens） */
const MODE_META: Record<ControlMode, { label: string; color: string }> = {
  manual: { label: '手动', color: colors.textSecondary },
  shadow: { label: '影子', color: colors.info },
  auto: { label: '自动', color: colors.success },
};

/** 控制模式徽标：登录后全站常显（方案§4.2.2 三阶段模式） */
function ControlModeBadge() {
  const controlMode = useFurnaceStore((s) => s.controlMode);
  const meta = MODE_META[controlMode];
  return (
    <Tooltip title="当前控制模式（方案§4.2.2）；切换请到「控制模式」页，双人确认后生效">
      {/* Tag color 取自 tokens，非颜色字面量 */}
      <Tag color={meta.color} className="m-0">
        控制模式：{meta.label}
      </Tag>
    </Tooltip>
  );
}

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
            焦炉AI加热控制
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
          <ControlModeBadge />
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
