/**
 * 结果回写页：化验结果录入 → POST /blend/feedback（真实接口，断网才走 mock）。
 * 化验回流驱动增量学习（方案§4.1.7）。
 */
import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  InputNumber,
  message,
  Select,
} from 'antd';
import { listRecipes, submitFeedback } from '../api';
import type { FeedbackResponse, QualityMetrics } from '../api/types';
import MockBadge from '../components/MockBadge';

export default function FeedbackPage() {
  const [batchOptions, setBatchOptions] = useState<
    { value: string; label: string }[]
  >([]);
  const [batchNo, setBatchNo] = useState<string>();
  const [quality, setQuality] = useState<QualityMetrics>({
    M25: 91,
    M10: 6.2,
    CSR: 66,
    CRI: 24,
  });
  const [result, setResult] = useState<FeedbackResponse | null>(null);
  const [resultMock, setResultMock] = useState(false);
  const [loading, setLoading] = useState(false);

  // 批次下拉来自历史方案接口（降级 mock 时同样可用）
  useEffect(() => {
    listRecipes()
      .then((resp) => {
        setBatchOptions(
          resp.recipes.map((r) => ({ value: r.batch_no, label: r.batch_no })),
        );
      })
      .catch(() => {
        message.warning('批次列表加载失败，请稍后重试');
      });
  }, []);

  const onSubmit = async () => {
    if (!batchNo) {
      message.warning('请选择批次号');
      return;
    }
    setLoading(true);
    try {
      const resp = await submitFeedback({
        batch_no: batchNo,
        actual_quality: { ...quality },
      });
      setResult(resp);
      setResultMock(resp.__mock === true);
      message.success('化验结果已回写');
    } catch (err) {
      message.error(err instanceof Error ? err.message : '回写失败');
    } finally {
      setLoading(false);
    }
  };

  const metricItem = (
    label: string,
    key: keyof QualityMetrics,
  ) => (
    <Form.Item label={label}>
      <InputNumber
        min={0}
        step={0.1}
        value={quality[key]}
        onChange={(v) => setQuality({ ...quality, [key]: v ?? 0 })}
      />
    </Form.Item>
  );

  return (
    <div>
      <h2 className="text-lg font-bold mb-3">结果回写</h2>
      <Card size="small" title="化验结果录入" className="mb-4">
        <Form layout="inline">
          <Form.Item label="批次号" required>
            <Select
              className="w-56"
              placeholder="选择配煤批次"
              showSearch
              value={batchNo}
              options={batchOptions}
              onChange={setBatchNo}
            />
          </Form.Item>
          {metricItem('实测 M25 (%)', 'M25')}
          {metricItem('实测 M10 (%)', 'M10')}
          {metricItem('实测 CSR (%)', 'CSR')}
          {metricItem('实测 CRI (%)', 'CRI')}
          <Form.Item>
            <Button type="primary" loading={loading} onClick={onSubmit}>
              提交回写
            </Button>
          </Form.Item>
        </Form>
      </Card>
      {result && (
        <Card
          size="small"
          title={
            <span>
              回写结果
              {resultMock && <MockBadge />}
            </span>
          }
          className="mb-4"
        >
          <Descriptions column={1} size="small">
            <Descriptions.Item label="批次号">{result.batch_no}</Descriptions.Item>
            <Descriptions.Item label="状态">{result.status}</Descriptions.Item>
            <Descriptions.Item label="说明">{result.detail}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
      <Alert
        type="info"
        showIcon
        message="化验回流驱动增量学习（方案§4.1.7）：实测值与预测值误差超阈值将进入误差缓冲区，缓冲区满触发模型增量微调。"
      />
    </div>
  );
}
