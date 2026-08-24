/**
 * 大屏标题栏：DataV Decoration8 双侧科技装饰线 + 发光标题字效（GlowTitle，token 青光晕），
 * 右侧实时时钟/数据同步时间/登录状态。
 * 从 App.tsx 外壳迁入大屏页（登录页不显示）；颜色全部走 dark* token。
 */
import { useState } from 'react';
import { Button, Space, Tag } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useInterval } from 'ahooks';
import { Decoration8 } from '@jiaminghi/data-view-react';
import { useAuthStore } from '../../stores/auth';
import { darkColors } from '../../styles/tokens';
import { GlowTitle } from './screen.styled';

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

interface ScreenHeaderProps {
  /** 最近一次数据同步完成时间（HH:mm:ss），未同步过传 null */
  syncedAt: string | null;
}

export default function ScreenHeader({ syncedAt }: ScreenHeaderProps) {
  const navigate = useNavigate();
  const { username, demo, logout } = useAuthStore();
  const clock = useClock();

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="relative border-b border-darkAccentCyanDim/60 bg-darkDeep px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        {/* 左侧：模块名 */}
        <span className="w-72 shrink-0 text-sm text-darkTextSecondary">领导驾驶舱</span>
        {/* 居中：Decoration8 装饰线 + 发光平台名 + 镜像装饰线 */}
        <div className="flex min-w-0 flex-1 items-center justify-center gap-3">
          <Decoration8
            className="shrink-0"
            color={[darkColors.accentCyan, darkColors.accentCyanDim]}
            // DataV 组件接口：装饰线尺寸靠 style 传入（非业务内联样式）
            style={{ width: '180px', height: '32px' }}
          />
          <GlowTitle>AI焦化厂智能管控平台</GlowTitle>
          <Decoration8
            reverse
            className="shrink-0"
            color={[darkColors.accentCyan, darkColors.accentCyanDim]}
            style={{ width: '180px', height: '32px' }}
          />
        </div>
        {/* 右侧：实时时钟 + 数据同步时间 + 登录状态（内容多，不设固定宽度、禁止换行） */}
        <div className="flex shrink-0 items-center justify-end whitespace-nowrap">
          <Space size="middle">
            <span className="font-mono text-sm text-darkText">{clock}</span>
            <span className="font-mono text-xs text-darkTextSecondary">
              数据同步 {syncedAt ?? '--:--:--'}
            </span>
            {demo && <Tag color="warning">演示模式</Tag>}
            <span className="text-sm text-darkText">{demo ? '演示用户' : username}</span>
            <Button size="small" icon={<LogoutOutlined />} onClick={onLogout}>
              退出
            </Button>
          </Space>
        </div>
      </div>
    </header>
  );
}
