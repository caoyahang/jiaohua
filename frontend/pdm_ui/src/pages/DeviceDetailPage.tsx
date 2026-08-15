/**
 * 单机详情页：/devices/:device_id。
 * 健康评分仪表 + 分项评分 + 7 天健康趋势 + 振动速度趋势（ISO 10816 四区色带）。
 * GET /pdm/devices/{id}/health 后端恒 503 → 必走 mock，恒挂「演示数据」角标。
 * 红线：不展示 RUL 剩余寿命（方案§4.3，故障样本不足，该能力后置 2~3 年）。
 */
import { useEffect, useState } from 'react';
import { Alert, Card, Col, message, Progress, Row } from 'antd';
import { Link, useParams } from 'react-router-dom';
import { getDeviceHealth } from '../api';
import { mockVibrationTrend } from '../api/mock';
import type { HealthResponse } from '../api/types';
import ChartCard from '../components/ChartCard';
import MockBadge from '../components/MockBadge';
import { deviceNameOf, devicePriorityOf, priorityTag } from '../components/pdmTags';
import { colors } from '../styles/tokens';
import { gaugeOption, healthTrendOption, vibrationTrendOption } from './detailOptions';

/** 分项评分进度条颜色：≥80 绿 / ≥60 黄 / 其余红 */
function scoreColor(score: number): string {
  if (score >= 80) return colors.success;
  if (score >= 60) return colors.warning;
  return colors.danger;
}

const SUBSCORE_LABELS: { key: keyof HealthResponse['subscores']; label: string }[] = [
  { key: 'vibration', label: '振动' },
  { key: 'bearing_temp', label: '轴承温度' },
  { key: 'motor_current', label: '电机电流' },
];

export default function DeviceDetailPage() {
  const { deviceId = '' } = useParams();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [mock, setMock] = useState(false);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!deviceId) return;
    getDeviceHealth(deviceId)
      .then((resp) => {
        setHealth(resp);
        setMock(resp.__mock === true);
      })
      .catch((err: unknown) => {
        // 404 设备不存在；其余错误如实展示
        if (err instanceof Error && 'status' in err && err.status === 404) {
          setNotFound(true);
        } else {
          message.error(err instanceof Error ? err.message : '查询失败');
        }
      });
  }, [deviceId]);

  if (notFound) {
    return (
      <Alert
        type="error"
        showIcon
        message={`设备不存在: ${deviceId}`}
        description={<Link to="/devices">返回设备总览</Link>}
      />
    );
  }
  if (!health) return null;

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">
        <Link to="/devices">设备总览</Link>
        <span className="mx-2">/</span>
        {deviceNameOf(deviceId)}
        {priorityTag(devicePriorityOf(deviceId))}
        {mock && <MockBadge />}
      </h2>
      <Row gutter={16}>
        <Col span={8}>
          <ChartCard
            title="综合健康评分"
            option={gaugeOption(health.health_score)}
            height={260}
            mock={mock}
          />
        </Col>
        <Col span={16}>
          <Card size="small" title="分项评分" className="mb-4">
            {SUBSCORE_LABELS.map(({ key, label }) => (
              <div key={key} className="mb-3">
                <span className="inline-block w-20">{label}</span>
                <Progress
                  className="inline-block w-4/5 align-middle"
                  percent={health.subscores[key]}
                  strokeColor={scoreColor(health.subscores[key])}
                  size="small"
                />
              </div>
            ))}
            <div className="text-textSecondary text-xs">
              分项评分由异常检测（孤立森林）+ 趋势外推（LSTM）综合得出（方案§4.3）
            </div>
          </Card>
          <ChartCard
            title="7 天健康趋势"
            option={healthTrendOption(health.trend_7d)}
            height={220}
            mock={mock}
          />
        </Col>
      </Row>
      <Row gutter={16} className="mt-4">
        <Col span={24}>
          <ChartCard
            title="振动速度趋势（ISO 10816 分区）"
            option={vibrationTrendOption(mockVibrationTrend(deviceId))}
            height={300}
            mock={mock}
          />
        </Col>
      </Row>
    </div>
  );
}
