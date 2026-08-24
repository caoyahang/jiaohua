/**
 * 视觉告警滚动列表：DataV ScrollBoard 轮播表（自动滚动，悬停暂停为组件自带语义）。
 * DANGER 行整行高亮（token 红），未确认状态橙色；单元格经组件 HTML 渲染，
 * 业务文本必须先 escapeHtml 再拼高亮 span（防接口字段注入）。
 * 颜色全部取 darkColors token（红线4），表体文字色覆盖见 screen.styled.ts。
 */
import { useMemo, useRef, useState, useEffect } from 'react';
import { ScrollBoard } from '@jiaminghi/data-view-react';
import type { ScrollBoardConfig } from '@jiaminghi/data-view-react';
import { darkColors } from '../../styles/tokens';
import { ScrollBoardWrap } from './screen.styled';
import type { VisionAlarm, VisionScene } from '../../api/types';

/** 场景中文名映射（docs/API文档.md §5 口径，方案§4.4.1 场景清单） */
const SCENE_NAMES: Record<VisionScene, string> = {
  helmet: '未戴安全帽',
  fire: '烟火',
  intrusion: '区域闯入',
  gas_leak: '煤气泄漏',
  gauge: '表计读数异常',
  coke_cake: '焦饼成熟度异常',
};

/** 场景 → 中文名；库中出现新场景时原样回退展示 */
export function sceneNameOf(scene: VisionScene): string {
  return SCENE_NAMES[scene] ?? scene;
}

/** ScrollBoard 单元格走 HTML 渲染：接口字段必须先转义 */
function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
  );
}

/** 单元格染色：DANGER 行整行红色高亮，其余状态列按需着色（颜色均来自 token） */
function tinted(text: string, color?: string): string {
  const safe = escapeHtml(text);
  return color ? `<span style="color:${color}">${safe}</span>` : safe;
}

interface Props {
  alarms: VisionAlarm[];
}

export default function AlarmScrollList({ alarms }: Props) {
  const config = useMemo<ScrollBoardConfig>(() => {
    const shown = alarms.slice(0, 10);
    const data = shown.map((a) => {
      // DANGER 行高亮：整行红色（alarmRed token）
      const rowColor = a.level === 'DANGER' ? darkColors.alarmRed : undefined;
      const statusColor = rowColor ?? (a.acknowledged ? darkColors.textSecondary : darkColors.accentOrange);
      return [
        tinted(a.ts.slice(11, 19), rowColor),
        tinted(sceneNameOf(a.scene), rowColor),
        tinted(`${a.area ?? '未知区域'} · ${a.camera_id}`, rowColor),
        tinted(a.acknowledged ? '已确认' : '未确认', statusColor),
      ];
    });
    return {
      header: ['时间', '告警内容', '区域 · 相机', '状态'],
      data,
      rowNum: 6,
      align: ['center', 'left', 'left', 'center'],
      // 表头/行底色走 token（DataV 组件接口）
      headerBGC: darkColors.accentCyanDim,
      oddRowBGC: darkColors.bgCard,
      evenRowBGC: darkColors.bgDeep,
      // 悬停暂停（保留原语义）
      hoverPause: true,
      waitTime: 2000,
    };
  }, [alarms]);

  // ScrollBoard 只在挂载时量一次容器高度定行高；一屏 flex 布局下面板高度是
  // 后分配的，必须等容器有确定高度后再挂载（否则行溢出面板下边框）。
  // 容器尺寸变化时以 key 重挂载重算。
  const wrapRef = useRef<HTMLDivElement>(null);
  const [wrapHeight, setWrapHeight] = useState(0);
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setWrapHeight(Math.floor(entry.contentRect.height));
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  return (
    <ScrollBoardWrap ref={wrapRef}>
      {wrapHeight > 0 && (
        <ScrollBoard
          key={wrapHeight}
          config={config}
          // DataV 组件接口：轮播表尺寸靠 style 传入（非业务内联样式）
          style={{ width: '100%', height: '100%' }}
        />
      )}
    </ScrollBoardWrap>
  );
}
