/**
 * 安全看板：PdM 未确认/DANGER 摘要 + 视觉告警滚动列表 + 场景分布饼图。
 * 数据源：GET /pdm/alarms、GET /vision/alarms（占位空表/不可达 → mock）。
 */
import { useMemo } from 'react';
import { Card, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import MockBadge from '../MockBadge';
import AlarmScrollList from './AlarmScrollList';
import { darkPieOption } from './chartTheme';
import type { PdmAlarm, VisionAlarm, VisionScene } from '../../api/types';

interface Props {
  pdmAlarms: PdmAlarm[];
  visionAlarms: VisionAlarm[];
  pdmMock: boolean;
  visionMock: boolean;
}

/** 场景中文名（与 AlarmScrollList 一致，饼图图例用） */
const SCENE_NAMES: Record<VisionScene, string> = {
  helmet: '未戴安全帽',
  fire_smoke: '烟火',
  intrusion: '区域闯入',
  gas_leak: '煤气泄漏',
};

export default function SafetyPanel({ pdmAlarms, visionAlarms, pdmMock, visionMock }: Props) {
  const pdmUnacked = pdmAlarms.filter((a) => !a.acknowledged);
  const pdmDanger = pdmUnacked.filter((a) => a.level === 'DANGER');

  const pieOption = useMemo(() => {
    const count = new Map<VisionScene, number>();
    for (const a of visionAlarms) {
      count.set(a.scene, (count.get(a.scene) ?? 0) + 1);
    }
    return darkPieOption(
      [...count.entries()].map(([scene, value]) => ({
        name: SCENE_NAMES[scene],
        value,
      })),
    );
  }, [visionAlarms]);

  return (
    <Card
      size="small"
      title={
        <span>
          安全看板
          {(pdmMock || visionMock) && <MockBadge />}
        </span>
      }
    >
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {/* PdM 摘要 */}
        <div>
          <div className="mb-2 text-darkTextSecondary text-xs">
            设备 PdM：未确认 {pdmUnacked.length} 条，其中 DANGER {pdmDanger.length} 条
          </div>
          {pdmUnacked.slice(0, 4).map((a) => (
            <div key={a.alarm_id} className="mb-1 flex items-center gap-2">
              <Tag color={a.level === 'DANGER' ? 'error' : 'warning'} className="mr-0">
                {a.level}
              </Tag>
              <span className="truncate text-darkText text-xs">{a.msg}</span>
            </div>
          ))}
          {/* 场景分布饼图 */}
          <ReactECharts
            option={pieOption}
            className="mt-2 w-full"
            // 高度属图表容器固有属性，非颜色/排版样式
            style={{ height: 200 }}
            notMerge
          />
        </div>
        {/* 视觉告警滚动列表 */}
        <div className="lg:col-span-2">
          <div className="mb-2 text-darkTextSecondary text-xs">
            视觉 AI 告警（最新 10 条，自动滚动，悬停暂停）
          </div>
          <AlarmScrollList alarms={visionAlarms} />
        </div>
      </div>
    </Card>
  );
}
