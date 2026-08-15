/**
 * 领导驾驶舱大屏页：全厂 KPI 一屏深色展示（方案§7.2 阶段六）。
 * 布局：顶部 5 张 KPI 卡 → 热工/推焦趋势 → 质量看板 + 安全看板；
 * 网格 auto-fit 响应式换行；全页 ahooks useInterval 10s 轮询。
 */
import { useCallback, useState } from 'react';
import { message } from 'antd';
import { useInterval, useMount } from 'ahooks';
import {
  ApiError,
  getKCoefficients,
  getOverviewKpi,
  getPdmAlarms,
  getQualityBoard,
  getVisionAlarms,
} from '../api';
import type {
  KCoefficientsResponse,
  OverviewKpi,
  PdmAlarmsResponse,
  QualityBoardResponse,
  VisionAlarmsResponse,
} from '../api/types';
import KpiCards from '../components/dashboard/KpiCards';
import ThermalKChart from '../components/dashboard/ThermalKChart';
import PushKChart from '../components/dashboard/PushKChart';
import QualityPanel from '../components/dashboard/QualityPanel';
import SafetyPanel from '../components/dashboard/SafetyPanel';

/** 轮询周期（前端规范§5：告警类页面刷新延迟 ≤10s） */
const POLL_MS = 10_000;

type Mocked<T extends object> = (T & { __mock?: true }) | null;

export default function DashboardPage() {
  const [overview, setOverview] = useState<Mocked<OverviewKpi>>(null);
  const [kData, setKData] = useState<Mocked<KCoefficientsResponse>>(null);
  const [quality, setQuality] = useState<Mocked<QualityBoardResponse>>(null);
  const [pdm, setPdm] = useState<Mocked<PdmAlarmsResponse>>(null);
  const [vision, setVision] = useState<Mocked<VisionAlarmsResponse>>(null);

  const load = useCallback(async () => {
    // 各区块独立取数：单接口失败不影响其他区块
    const safe = <T extends object>(p: Promise<T & { __mock?: true }>, label: string) =>
      p.catch((err: unknown) => {
        // 4xx/5xx（非 503）才走到这里：如实报错，本周期保留旧数据
        message.error(`${label}加载失败：${err instanceof ApiError ? err.message : '未知错误'}`);
        return null;
      });
    const [o, k, q, p, v] = await Promise.all([
      safe(getOverviewKpi(), '全厂汇总'),
      safe(getKCoefficients(), 'K系数'),
      safe(getQualityBoard(), '质量看板'),
      safe(getPdmAlarms(), 'PdM告警'),
      safe(getVisionAlarms(), '视觉告警'),
    ]);
    if (o) setOverview(o);
    if (k) setKData(k);
    if (q) setQuality(q);
    if (p) setPdm(p);
    if (v) setVision(v);
  }, []);

  useMount(load);
  useInterval(load, POLL_MS);

  const unackedAlarms =
    (vision?.alarms.filter((a) => !a.acknowledged).length ?? 0) +
    (pdm?.alarms.filter((a) => !a.acknowledged).length ?? 0);

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(460px,1fr))] gap-3">
      {/* 顶部 KPI 卡片区：占满整行 */}
      <div className="col-span-full">
        <KpiCards
          overview={overview}
          unackedAlarms={unackedAlarms}
          overviewMock={overview?.__mock === true}
          alarmsMock={vision?.__mock === true || pdm?.__mock === true}
        />
      </div>
      <ThermalKChart rows={kData?.coefficients ?? []} mock={kData?.__mock === true} />
      <PushKChart rows={kData?.coefficients ?? []} mock={kData?.__mock === true} />
      <QualityPanel batches={quality?.batches ?? []} mock={!quality || quality.__mock === true} />
      <SafetyPanel
        pdmAlarms={pdm?.alarms ?? []}
        visionAlarms={vision?.alarms ?? []}
        pdmMock={pdm?.__mock === true}
        visionMock={vision?.__mock === true}
      />
    </div>
  );
}
