/**
 * AI 推荐值页（README 接口清单：GET /furnace/ai-setpoint 真实可用，占位值）。
 * AI 煤气流量设定值 vs 当前实际值同屏大数值卡 + 差值（前端规范§4：同屏对比）。
 * 当前实际值取炉温时序（GET /furnace/temp）最新时刻的双侧均值。
 */
import { useCallback, useState } from 'react';
import { Alert, Card, Col, Row, Space, Statistic, Tag, Typography, message } from 'antd';
import { useInterval, useMount } from 'ahooks';
import { ApiError, getAiSetpoint, getTemp } from '../api';
import type { AiSetpointResponse } from '../api/types';
import { useFurnaceStore } from '../stores/furnace';
import MockBadge from '../components/MockBadge';

export default function AiSetpointPage() {
  const furnaceId = useFurnaceStore((s) => s.furnaceId);
  const [setpoint, setSetpoint] = useState<AiSetpointResponse | null>(null);
  const [setpointMock, setSetpointMock] = useState(false);
  const [actualFlow, setActualFlow] = useState<number | null>(null);
  const [actualMock, setActualMock] = useState(false);

  const load = useCallback(async () => {
    try {
      const resp = await getAiSetpoint(furnaceId);
      setSetpoint(resp);
      setSetpointMock(resp.__mock === true);
    } catch (err) {
      if (err instanceof ApiError) message.error(err.message);
    }
    try {
      const temp = await getTemp(furnaceId);
      // 最新时刻的双侧煤气流量均值作为当前实际值
      const latestTs = temp.points[temp.points.length - 1]?.ts;
      const latest = temp.points.filter((p) => p.ts === latestTs);
      if (latest.length > 0) {
        const avg =
          latest.reduce((s, p) => s + p.gas_flow, 0) / latest.length;
        setActualFlow(Math.round(avg));
      }
      setActualMock(temp.__mock === true);
    } catch (err) {
      if (err instanceof ApiError) message.error(err.message);
    }
  }, [furnaceId]);

  useMount(load);
  // 与炉温监控页一致的 10s 轮询
  useInterval(load, 10_000);

  const diff =
    setpoint && actualFlow !== null
      ? Math.round((setpoint.gas_flow_setpoint - actualFlow) * 10) / 10
      : null;

  return (
    <Space direction="vertical" size="middle" className="w-full">
      <Typography.Title level={4} className="m-0">
        AI 推荐值 vs 当前实际值
      </Typography.Title>
      {setpoint?.clamped && (
        <Alert
          type="warning"
          showIcon
          message="设定值已被安全钳位"
          description="AI 原始输出超出安全限值，已按限值收窄后展示；DCS 侧另有硬钳位兜底（方案§4.2.6）。"
        />
      )}
      <Alert
        type="info"
        showIcon
        message="影子模式下 AI 推荐值仅展示，不下发 DCS"
      />
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic
              title={
                <span>
                  AI 煤气流量设定值（m³/h）
                  {setpointMock && <MockBadge />}
                </span>
              }
              value={setpoint?.gas_flow_setpoint ?? '-'}
              precision={0}
            />
            <div className="mt-2">
              {setpoint?.model_version ? (
                <Tag>模型版本：{setpoint.model_version}</Tag>
              ) : (
                <Tag>模型未注册（冷启动）</Tag>
              )}
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={
                <span>
                  当前实际煤气流量（m³/h）
                  {actualMock && <MockBadge />}
                </span>
              }
              value={actualFlow ?? '-'}
              precision={0}
            />
            <div className="mt-2 text-textSecondary">取炉温时序最新值</div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="差值（AI − 实际，m³/h）"
              value={diff ?? '-'}
              precision={1}
              // 差值为正则 AI 建议加煤气，为负则建议减煤气
              prefix={diff !== null && diff > 0 ? '+' : ''}
            />
            <div className="mt-2 text-textSecondary">
              供调火工参考，是否采纳由人工决定
            </div>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
