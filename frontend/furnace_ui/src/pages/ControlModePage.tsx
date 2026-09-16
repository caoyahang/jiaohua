/**
 * 控制模式页（README 接口清单：POST /furnace/control-mode 真实可用）。
 * 安全红线（方案§4.2.6）：「一键切手动」为 DCS 硬切换，不经过本界面——
 * 本页严禁出现任何「一键切手动」软按钮；软切换需操作人+复核人双人确认。
 */
import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { ApiError, setControlMode } from '../api';
import type { ControlMode } from '../api/types';
import { useFurnaceStore } from '../stores/furnace';
import ConfirmModal from '../components/ConfirmModal';
import { colors } from '../styles/tokens';

/** 控制模式展示配置（与 App.tsx 徽标口径一致，颜色来自 tokens） */
const MODE_META: Record<ControlMode, { label: string; color: string }> = {
  manual: { label: '手动', color: colors.textSecondary },
  shadow: { label: '影子', color: colors.info },
  auto: { label: '自动', color: colors.success },
};

interface SwitchForm {
  mode: Exclude<ControlMode, 'manual'>;
  operator: string;
  reviewer: string;
  reason: string;
}

export default function ControlModePage() {
  const { furnaceId, controlMode, setControlMode: saveMode } = useFurnaceStore();
  const [form] = Form.useForm<SwitchForm>();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pending, setPending] = useState<SwitchForm | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 表单校验通过后先弹二次确认，不直接提交
  const onFinish = (values: SwitchForm) => {
    setPending(values);
    setConfirmOpen(true);
  };

  const onConfirm = async () => {
    if (!pending) return;
    setSubmitting(true);
    try {
      // 复核人写入 reason 一并送后端审计日志（furnace.py logger.info 记录）
      await setControlMode({
        furnace_id: furnaceId,
        mode: pending.mode,
        operator: pending.operator,
        reviewer: pending.reviewer,
        reason: pending.reason,
        confirm: true,
      });
      saveMode(pending.mode);
      message.success(`控制模式已切换为：${MODE_META[pending.mode].label}`);
      setConfirmOpen(false);
      form.resetFields();
    } catch (err) {
      if (err instanceof ApiError) {
        message.error(err.message);
      } else {
        message.error('切换失败，请重试');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Space direction="vertical" size="middle" className="w-full max-w-2xl">
      <Typography.Title level={4} className="m-0">
        控制模式切换
      </Typography.Title>
      {/* 安全红线提示（方案§4.2.6）：红色边框 Alert，原文展示 */}
      <Alert
        type="error"
        showIcon
        className="border-danger"
        message="安全红线"
        description="一键切手动为 DCS 硬切换，不经过本界面；本界面所有 AI 操作仅影响设定值，DCS 侧硬钳位（方案§4.2.6）"
      />
      <Card title="当前模式">
        <Tag color={MODE_META[controlMode].color} className="text-base px-3 py-1">
          {MODE_META[controlMode].label}
        </Tag>
        <div className="mt-2 text-textSecondary">
          三阶段模式（方案§4.2.2）：手动 → 影子（AI 只展示不下发）→ 自动（AI 设定值经钳位后下发）
        </div>
      </Card>
      <Card title="软切换（双人确认）">
        <Form<SwitchForm> form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="mode"
            label="目标模式"
            rules={[{ required: true, message: '请选择目标模式' }]}
          >
            <Select
              placeholder="请选择目标模式"
              options={(['shadow', 'auto'] as const).map((value) => ({
                value,
                label: `${MODE_META[value].label}（${value}）`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="operator"
            label="操作人（工号/姓名）"
            rules={[{ required: true, message: '请输入操作人' }]}
          >
            <Input placeholder="操作人工号或姓名" />
          </Form.Item>
          <Form.Item
            name="reviewer"
            label="复核人（工号/姓名，不得与操作人相同）"
            dependencies={['operator']}
            rules={[
              { required: true, message: '请输入复核人' },
              ({ getFieldValue }) => ({
                validator: (_, value: string) =>
                  value && value === getFieldValue('operator')
                    ? Promise.reject(new Error('复核人不得与操作人相同'))
                    : Promise.resolve(),
              }),
            ]}
          >
            <Input placeholder="复核人工号或姓名" />
          </Form.Item>
          <Form.Item
            name="reason"
            label="切换原因"
            rules={[{ required: true, message: '请填写切换原因' }]}
          >
            <Input.TextArea rows={2} placeholder="切换原因（写入后端审计日志）" />
          </Form.Item>
          <Button type="primary" htmlType="submit">
            提交切换
          </Button>
        </Form>
      </Card>
      <ConfirmModal
        open={confirmOpen}
        title="确认切换控制模式"
        okText="确认切换"
        confirmLoading={submitting}
        onConfirm={onConfirm}
        onCancel={() => setConfirmOpen(false)}
        content={
          pending && (
            <div>
              <p>
                目标模式：
                <Tag color={MODE_META[pending.mode].color}>
                  {MODE_META[pending.mode].label}（{pending.mode}）
                </Tag>
              </p>
              <p>操作人：{pending.operator}　复核人：{pending.reviewer}</p>
              <p>切换原因：{pending.reason}</p>
              <p className="text-textSecondary">
                请复核人现场确认后再点「确认切换」；本操作仅影响 AI 设定值通路，DCS
                侧硬钳位不受影响（方案§4.2.6）。
              </p>
            </div>
          )
        }
      />
    </Space>
  );
}
