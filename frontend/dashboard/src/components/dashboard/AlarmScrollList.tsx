/**
 * 视觉告警滚动列表：最新 10 条自动滚动，悬停暂停（overlayscrollbars 统一滚动条）。
 */
import { useRef, useState } from 'react';
import { Tag } from 'antd';
import { useInterval } from 'ahooks';
import { OverlayScrollbarsComponent } from 'overlayscrollbars-react';
import type { OverlayScrollbars } from 'overlayscrollbars';
import type { VisionAlarm, VisionScene } from '../../api/types';

/** 场景中文名映射（方案§4.4.1 场景清单） */
const SCENE_NAMES: Record<VisionScene, string> = {
  helmet: '未戴安全帽',
  fire_smoke: '烟火',
  intrusion: '区域闯入',
  gas_leak: '煤气泄漏',
};

interface Props {
  alarms: VisionAlarm[];
}

export default function AlarmScrollList({ alarms }: Props) {
  // 自动滚动：每 2s 下移一行，触底回卷；悬停暂停
  const osRef = useRef<OverlayScrollbars | null>(null);
  const [paused, setPaused] = useState(false);

  useInterval(
    () => {
      const os = osRef.current;
      if (!os) return;
      const viewport = os.elements().viewport;
      const row = 44; // 单行高度（px），与下行 dom 结构一致
      const next = viewport.scrollTop + row;
      viewport.scrollTo({
        top: next >= viewport.scrollHeight - viewport.clientHeight ? 0 : next,
        behavior: 'smooth',
      });
    },
    paused ? undefined : 2000,
  );

  const shown = alarms.slice(0, 10);

  return (
    <div
      className="h-64"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <OverlayScrollbarsComponent
        options={{ scrollbars: { autoHide: 'leave' } }}
        events={{
          initialized: (instance) => {
            osRef.current = instance;
          },
        }}
        className="h-full"
      >
        {shown.map((a) => (
          <div
            key={a.alarm_id}
            className="flex h-11 items-center justify-between border-b border-darkGridLine px-2"
          >
            <div className="min-w-0">
              <span className="text-darkText text-sm">{SCENE_NAMES[a.scene]}</span>
              <span className="ml-2 text-darkTextSecondary text-xs">
                {a.area} · {a.camera_id}
              </span>
            </div>
            <div className="flex items-center gap-2 whitespace-nowrap">
              <span className="text-darkTextSecondary text-xs">
                {a.ts.slice(11, 19)}
              </span>
              <Tag color={a.acknowledged ? 'default' : 'error'} className="mr-0">
                {a.acknowledged ? '已确认' : '未确认'}
              </Tag>
            </div>
          </div>
        ))}
      </OverlayScrollbarsComponent>
    </div>
  );
}
