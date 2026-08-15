/**
 * 焦炉运行状态 store（zustand）：控制模式全站常显的数据源（前端规范§4 设计纪律）。
 * 中间件按前端规范固定：devtools + subscribeWithSelector（登录态 persist 在 auth store）。
 */
import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import type { ControlMode } from '../api/types';

interface FurnaceState {
  /** 当前监控的焦炉编号（V1.1 阶段四先做单炉，默认 1 号炉） */
  furnaceId: number;
  /** 当前控制模式：manual 人工 / shadow 影子 / auto 自动（方案§4.2.2） */
  controlMode: ControlMode;
  setControlMode: (mode: ControlMode) => void;
}

export const useFurnaceStore = create<FurnaceState>()(
  devtools(
    subscribeWithSelector((set) => ({
      furnaceId: 1,
      controlMode: 'manual',
      setControlMode: (mode) => set({ controlMode: mode }, false, 'setControlMode'),
    })),
    { name: 'furnace' },
  ),
);
