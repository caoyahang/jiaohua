/**
 * 炉温实时监控页（README 接口清单：GET /furnace/temp 恒 503 → 必走 mock）。
 * 机/焦侧火道温度双折线 + 煤气流量/吸力/集气管压力/残氧多曲线图，10s 轮询（前端规范§5）。
 */
import { useCallback, useState } from 'react';
import { Alert, Space, Typography, message } from 'antd';
import { useInterval, useMount } from 'ahooks';
import { ApiError, getTemp } from '../api';
import type { TempResponse } from '../api/types';
import { useFurnaceStore } from '../stores/furnace';
import ChartCard from '../components/ChartCard';
import MockBadge from '../components/MockBadge';
import { buildGasOption, buildTempOption } from './tempCharts';

export default function TempMonitorPage() {
  const furnaceId = useFurnaceStore((s) => s.furnaceId);
  const [data, setData] = useState<TempResponse | null>(null);
  const [mock, setMock] = useState(false);

  const load = useCallback(async () => {
    try {
      const resp = await getTemp(furnaceId);
      setData(resp);
      setMock(resp.__mock === true);
    } catch (err) {
      if (err instanceof ApiError) message.error(err.message);
    }
  }, [furnaceId]);

  useMount(load);
  // 10s 轮询（告警类页面刷新延迟 ≤10 秒，方案§7.2）
  useInterval(load, 10_000);

  return (
    <Space direction="vertical" size="middle" className="w-full">
      <Typography.Title level={4} className="m-0">
        炉温实时监控
        {mock && <MockBadge />}
      </Typography.Title>
      <Alert
        type="info"
        showIcon
        message="灰色区间为换向期，换向期脏数据不考核（方案§4.2.6）"
      />
      {data && (
        <>
          <ChartCard
            title="机/焦侧火道温度（℃）"
            option={buildTempOption(data.points)}
            height={320}
            mock={mock}
          />
          <ChartCard
            title="煤气流量 / 烟道吸力 / 集气管压力 / 废气残氧"
            option={buildGasOption(data.points)}
            height={320}
            mock={mock}
          />
        </>
      )}
    </Space>
  );
}
