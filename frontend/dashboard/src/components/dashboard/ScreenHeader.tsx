/**
 * 运营总览顶部导航：平台标识、当前模块、同步状态与用户操作。
 * 依据方案§7.2 阶段六；采用常规管理后台导航，不使用大屏装饰。
 */
import { ApartmentOutlined, LogoutOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, Space, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth';

interface ScreenHeaderProps {
  /** 最近一次数据同步完成时间（HH:mm:ss），未同步过传 null */
  syncedAt: string | null;
  /** 手动刷新全部总览数据 */
  onRefresh: () => void;
  /** 数据请求进行中 */
  loading: boolean;
}

export default function ScreenHeader({ syncedAt, onRefresh, loading }: ScreenHeaderProps) {
  const navigate = useNavigate();
  const { username, demo, logout } = useAuthStore();

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bgCard">
      <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-lg text-bgCard">
            <ApartmentOutlined />
          </span>
          <div className="min-w-0">
            <div className="truncate text-base font-semibold text-text">焦化厂智能化平台</div>
            <div className="text-xs text-textSecondary">运营总览</div>
          </div>
        </div>
        <Space size="middle" wrap>
          <span className="hidden text-xs text-textSecondary md:inline">
            10 秒自动刷新 · 最近同步 {syncedAt ?? '--:--:--'}
          </span>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={onRefresh}>
            刷新
          </Button>
          {demo && <Tag color="warning">演示模式</Tag>}
          <span className="hidden text-sm text-text sm:inline">{demo ? '演示用户' : username}</span>
          <Button icon={<LogoutOutlined />} onClick={onLogout}>
            退出
          </Button>
        </Space>
      </div>
    </header>
  );
}
