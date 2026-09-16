/**
 * 全厂运营总览：以常规企业管理页面呈现 KPI、趋势、质量和安全告警。
 * 依据方案§7.2 阶段六；页面 10 秒轮询，小屏自然纵向滚动。
 */
import { useCallback, useState } from 'react';
import { Badge, Breadcrumb, message } from 'antd';
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
import AlarmTable from '../components/dashboard/AlarmTable';
import KpiCards from '../components/dashboard/KpiCards';
import Panel from '../components/dashboard/Panel';
import PushKChart from '../components/dashboard/PushKChart';
import QualityPanel from '../components/dashboard/QualityPanel';
import SafetyPanel from '../components/dashboard/SafetyPanel';
import ScreenHeader from '../components/dashboard/ScreenHeader';
import ThermalKChart from '../components/dashboard/ThermalKChart';

/** 轮询周期（前端规范§5：告警类页面刷新延迟 ≤10s） */
const POLL_MS = 10_000;

type Mocked<T extends object> = (T & { __mock?: true }) | null;

/** 数据同步时间戳：HH:mm:ss。 */
function nowHM(): string {
  const date = new Date();
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<Mocked<OverviewKpi>>(null);
  const [kData, setKData] = useState<Mocked<KCoefficientsResponse>>(null);
  const [quality, setQuality] = useState<Mocked<QualityBoardResponse>>(null);
  const [pdm, setPdm] = useState<Mocked<PdmAlarmsResponse>>(null);
  const [vision, setVision] = useState<Mocked<VisionAlarmsResponse>>(null);
  const [syncedAt, setSyncedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const safe = <T extends object>(promise: Promise<T & { __mock?: true }>, label: string) =>
      promise.catch((error: unknown) => {
        message.error(`${label}加载失败：${error instanceof ApiError ? error.message : '未知错误'}`);
        return null;
      });

    try {
      const [overviewResult, kResult, qualityResult, pdmResult, visionResult] = await Promise.all([
        safe(getOverviewKpi(), '全厂汇总'),
        safe(getKCoefficients(), 'K 系数'),
        safe(getQualityBoard(), '质量趋势'),
        safe(getPdmAlarms(), 'PdM 告警'),
        safe(getVisionAlarms(), '视觉告警'),
      ]);
      if (overviewResult) setOverview(overviewResult);
      if (kResult) setKData(kResult);
      if (qualityResult) setQuality(qualityResult);
      if (pdmResult) setPdm(pdmResult);
      if (visionResult) setVision(visionResult);
      setSyncedAt(nowHM());
    } finally {
      setLoading(false);
    }
  }, []);

  useMount(load);
  useInterval(load, POLL_MS);

  const unackedAlarms =
    (vision?.items.filter((alarm) => !alarm.acknowledged).length ?? 0) +
    (pdm?.items.filter((alarm) => !alarm.acknowledged).length ?? 0);
  const visionMock = vision?.__mock === true;
  const pdmMock = pdm?.__mock === true;

  return (
    <div className="min-h-screen bg-bgPage">
      <ScreenHeader syncedAt={syncedAt} onRefresh={() => void load()} loading={loading} />
      <main className="mx-auto max-w-screen-2xl px-4 py-6 sm:px-6">
        <Breadcrumb items={[{ title: '首页' }, { title: '运营总览' }]} />
        <div className="mb-5 mt-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-text">运营总览</h1>
            <p className="mt-1 text-sm text-textSecondary">
              汇总生产稳定性、焦炭质量和安全告警，辅助日常运营判断。
            </p>
          </div>
          <Badge status={unackedAlarms > 0 ? 'warning' : 'success'} text={`待处理告警 ${unackedAlarms} 条`} />
        </div>

        <KpiCards
          overview={overview}
          unackedAlarms={unackedAlarms}
          overviewMock={overview?.__mock === true}
          alarmsMock={visionMock || pdmMock}
        />

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <ThermalKChart rows={kData?.records ?? []} mock={kData?.__mock === true} />
          <PushKChart rows={kData?.records ?? []} mock={kData?.__mock === true} />
        </div>

        <div className="mt-4 grid items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)]">
          <QualityPanel batches={quality?.batches ?? []} mock={!quality || quality.__mock === true} />
          <SafetyPanel
            pdmAlarms={pdm?.items ?? []}
            visionAlarms={vision?.items ?? []}
            pdmMock={pdmMock}
            visionMock={visionMock}
          />
        </div>

        <Panel title="最新视觉告警" mock={visionMock} className="mt-4">
          <AlarmTable alarms={vision?.items ?? []} />
        </Panel>
      </main>
    </div>
  );
}
