/**
 * 领导驾驶舱大屏页：全厂 KPI 一屏深色展示（方案§7.2 阶段六）。
 * 布局：顶部标题栏（ScreenHeader）→ 三栏网格（左：KpiCards + QualityPanel；
 * 中：FurnaceSchematic + ThermalKChart；右：SafetyPanel + 视觉告警滚动列表）
 * → 底部通栏 PushKChart；小屏单列纵向滚动；全页 ahooks useInterval 10s 轮询。
 */
import { useCallback, useState } from 'react';
import { message } from 'antd';
import { useInterval, useMount } from 'ahooks';
import {
  ApiError,
  getFurnaceTemp,
  getKCoefficients,
  getOverviewKpi,
  getPdmAlarms,
  getQualityBoard,
  getVisionAlarms,
} from '../api';
import type {
  FurnaceTempResponse,
  KCoefficientsResponse,
  OverviewKpi,
  PdmAlarmsResponse,
  QualityBoardResponse,
  VisionAlarmsResponse,
} from '../api/types';
import ScreenHeader from '../components/dashboard/ScreenHeader';
import Panel from '../components/dashboard/Panel';
import KpiCards from '../components/dashboard/KpiCards';
import FurnaceSchematic from '../components/dashboard/FurnaceSchematic';
import ThermalKChart from '../components/dashboard/ThermalKChart';
import PushKChart from '../components/dashboard/PushKChart';
import QualityPanel from '../components/dashboard/QualityPanel';
import SafetyPanel from '../components/dashboard/SafetyPanel';
import AlarmScrollList from '../components/dashboard/AlarmScrollList';
import { ScreenShell } from '../components/dashboard/screen.styled';

/** 轮询周期（前端规范§5：告警类页面刷新延迟 ≤10s） */
const POLL_MS = 10_000;

type Mocked<T extends object> = (T & { __mock?: true }) | null;

/** 数据同步时间戳：HH:mm:ss */
function nowHM(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<Mocked<OverviewKpi>>(null);
  const [kData, setKData] = useState<Mocked<KCoefficientsResponse>>(null);
  const [quality, setQuality] = useState<Mocked<QualityBoardResponse>>(null);
  const [pdm, setPdm] = useState<Mocked<PdmAlarmsResponse>>(null);
  const [vision, setVision] = useState<Mocked<VisionAlarmsResponse>>(null);
  const [temp, setTemp] = useState<Mocked<FurnaceTempResponse>>(null);
  const [syncedAt, setSyncedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    // 各区块独立取数：单接口失败不影响其他区块
    const safe = <T extends object>(p: Promise<T & { __mock?: true }>, label: string) =>
      p.catch((err: unknown) => {
        // 4xx/5xx（非 503）才走到这里：如实报错，本周期保留旧数据
        message.error(`${label}加载失败：${err instanceof ApiError ? err.message : '未知错误'}`);
        return null;
      });
    const [o, k, q, p, v, t] = await Promise.all([
      safe(getOverviewKpi(), '全厂汇总'),
      safe(getKCoefficients(), 'K系数'),
      safe(getQualityBoard(), '质量看板'),
      safe(getPdmAlarms(), 'PdM告警'),
      safe(getVisionAlarms(), '视觉告警'),
      safe(getFurnaceTemp(), '实时炉温'),
    ]);
    if (o) setOverview(o);
    if (k) setKData(k);
    if (q) setQuality(q);
    if (p) setPdm(p);
    if (v) setVision(v);
    if (t) setTemp(t);
    setSyncedAt(nowHM());
  }, []);

  useMount(load);
  useInterval(load, POLL_MS);

  const unackedAlarms =
    (vision?.items.filter((a) => !a.acknowledged).length ?? 0) +
    (pdm?.items.filter((a) => !a.acknowledged).length ?? 0);
  const visionMock = vision?.__mock === true;
  const pdmMock = pdm?.__mock === true;

  return (
    <ScreenShell className="h-screen overflow-hidden">
      <div className="flex h-full flex-col">
        <ScreenHeader syncedAt={syncedAt} />
        <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto p-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_minmax(0,1fr)] xl:grid-rows-[minmax(0,1fr)_200px] xl:overflow-hidden">
          {/* 左栏：KPI 卡片 + 质量看板 */}
          <div className="flex min-h-0 flex-col gap-3">
            <div className="shrink-0">
              <KpiCards
                overview={overview}
                unackedAlarms={unackedAlarms}
                overviewMock={overview?.__mock === true}
                alarmsMock={visionMock || pdmMock}
              />
            </div>
            <QualityPanel batches={quality?.batches ?? []} mock={!quality || quality.__mock === true} />
          </div>
          {/* 中栏：工艺示意图 + 热工 KPI */}
          <div className="flex min-h-0 flex-col gap-3">
            <FurnaceSchematic temp={temp} mock={temp?.__mock === true} />
            <div className="shrink-0">
              <ThermalKChart rows={kData?.coefficients ?? []} mock={kData?.__mock === true} />
            </div>
          </div>
          {/* 右栏：安全看板 + 视觉告警滚动列表 */}
          <div className="flex min-h-0 flex-col gap-3">
            <div className="shrink-0">
              <SafetyPanel
                pdmAlarms={pdm?.items ?? []}
                visionAlarms={vision?.items ?? []}
                pdmMock={pdmMock}
                visionMock={visionMock}
              />
            </div>
            <Panel title="视觉 AI 告警（滚动轮播，悬停暂停）" mock={visionMock} fill>
              <AlarmScrollList alarms={vision?.items ?? []} />
            </Panel>
          </div>
          {/* 底部通栏：推焦 KPI */}
          <div className="min-h-0 xl:col-span-3">
            <PushKChart rows={kData?.coefficients ?? []} mock={kData?.__mock === true} />
          </div>
        </main>
      </div>
    </ScreenShell>
  );
}
