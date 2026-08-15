/**
 * 确认对话框封装：基于 AntD Modal，统一「AI 建议 + 人工确认」交互（方案§13.2）。
 */
import { Modal } from 'antd';
import type { ReactNode } from 'react';

interface ConfirmModalProps {
  open: boolean;
  title: string;
  content: ReactNode;
  /** 确认按钮文案，默认「确认」 */
  okText?: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmLoading?: boolean;
}

export default function ConfirmModal({
  open,
  title,
  content,
  okText = '确认',
  onConfirm,
  onCancel,
  confirmLoading = false,
}: ConfirmModalProps) {
  return (
    <Modal
      open={open}
      title={title}
      okText={okText}
      cancelText="取消"
      onOk={onConfirm}
      onCancel={onCancel}
      confirmLoading={confirmLoading}
    >
      {content}
    </Modal>
  );
}
