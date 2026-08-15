/**
 * 「演示数据」角标：凡响应带 __mock 的页面/卡片必须展示（前端规范红线6）。
 */
import { Tag, Tooltip } from 'antd';

export default function MockBadge() {
  return (
    <Tooltip title="后端不可用或未接通，当前展示的是前端演示数据">
      <Tag color="warning" className="ml-2">
        演示数据
      </Tag>
    </Tooltip>
  );
}
