/**
 * 安全与设备告警摘要：PdM 未确认/DANGER 数量 + 视觉告警场景分布。
 * 数据源：GET /pdm/alarms、GET /vision/alarms（真实查询；503/断网 → mock）。
 * 视觉告警明细由 DashboardPage 的 AlarmTable 展示。
 */
import { useMemo } from 'react';
import { Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import Panel from './Panel';
import { sceneNameOf } from './AlarmTable';
import { pieOption } from './chartTheme';
import type { PdmAlarm, VisionAlarm } from '../../api/types';

interface Props {
  pdmAlarms: PdmAlarm[];
  visionAlarms: VisionAlarm[];
  pdmMock: boolean;
  visionMock: boolean;
}

export default function SafetyPanel({ pdmAlarms, visionAlarms, pdmMock, visionMock }: Props) {
  const pdmUnacked = pdmAlarms.filter((a) => !a.acknowledged);
  const pdmDanger = pdmUnacked.filter((a) => a.level === 'DANGER');

  const chartOption = useMemo(() => {
    const count = new Map<string, number>();
    for (const a of visionAlarms) {
      const name = sceneNameOf(a.scene);
      count.set(name, (count.get(name) ?? 0) + 1);
    }
    return pieOption(
      [...count.entries()].map(([name, value]) => ({ name, value })),
    );
  }, [visionAlarms]);

  return (
    <Panel title="安全与设备告警" mock={pdmMock || visionMock}>
      <div className="mb-3 text-sm text-textSecondary">
        设备 PdM：未确认 {pdmUnacked.length} 条，其中 DANGER {pdmDanger.length} 条
      </div>
      {pdmUnacked.slice(0, 4).map((a) => (
        <div key={a.alarm_id} className="mb-1 flex items-center gap-2">
          <Tag color={a.level === 'DANGER' ? 'error' : 'warning'} className="mr-0">
            {a.level}
          </Tag>
          <span className="truncate text-sm text-text">{a.msg ?? `设备 #${a.equipment_id}`}</span>
        </div>
      ))}
      {/* 场景分布饼图 */}
      <ReactECharts
        option={chartOption}
        className="mt-2 w-full"
        // 高度属图表容器固有属性，非颜色/排版样式
        style={{ height: 210 }}
        notMerge
      />
    </Panel>
  );
}
