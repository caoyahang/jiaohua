/**
 * 安全看板：PdM 未确认/DANGER 摘要 + 视觉告警场景分布饼图。
 * 数据源：GET /pdm/alarms、GET /vision/alarms（真实查询；503/断网 → mock）。
 * 视觉告警滚动列表已拆为页面右栏独立面板（AlarmScrollList），见 DashboardPage。
 */
import { useMemo } from 'react';
import { Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import Panel from './Panel';
import { sceneNameOf } from './AlarmScrollList';
import { darkPieOption } from './chartTheme';
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

  const pieOption = useMemo(() => {
    const count = new Map<string, number>();
    for (const a of visionAlarms) {
      const name = sceneNameOf(a.scene);
      count.set(name, (count.get(name) ?? 0) + 1);
    }
    return darkPieOption(
      [...count.entries()].map(([name, value]) => ({ name, value })),
    );
  }, [visionAlarms]);

  return (
    <Panel title="安全看板" mock={pdmMock || visionMock}>
      <div className="mb-2 text-xs text-darkTextSecondary">
        设备 PdM：未确认 {pdmUnacked.length} 条，其中 DANGER {pdmDanger.length} 条
      </div>
      {pdmUnacked.slice(0, 4).map((a) => (
        <div key={a.alarm_id} className="mb-1 flex items-center gap-2">
          <Tag color={a.level === 'DANGER' ? 'error' : 'warning'} className="mr-0">
            {a.level}
          </Tag>
          <span className="truncate text-xs text-darkText">{a.msg ?? `设备 #${a.equipment_id}`}</span>
        </div>
      ))}
      {/* 场景分布饼图 */}
      <ReactECharts
        option={pieOption}
        className="mt-2 w-full"
        // 高度属图表容器固有属性，非颜色/排版样式
        style={{ height: 150 }}
        notMerge
      />
    </Panel>
  );
}
