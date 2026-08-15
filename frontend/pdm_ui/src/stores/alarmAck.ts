/**
 * 告警确认本地状态（zustand）。
 *
 * TODO: 待后端补 PdM ack 接口（参照 /vision/alarms/{id}/ack）后改为调用接口，
 * 当前确认为纯前端本地状态，不落库。
 * 误报标记（false_positive）需回流模型迭代：误报率是第一优先级指标（<15%，方案§4.3）。
 *
 * 中间件按前端规范固定三件套：persist + devtools + subscribeWithSelector。
 */
import { create } from 'zustand';
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware';

/** 告警确认记录（处置信息） */
export interface AlarmAck {
  /** 处理人 */
  operator: string;
  /** 处置意见 */
  opinion: string;
  /** 是否误报（误报标记回流模型迭代，方案§4.3 误报率目标 <15%） */
  false_positive: boolean;
  /** 确认时间 ISO 8601 */
  ts: string;
}

interface AlarmAckState {
  /** alarm_id → 确认记录 */
  acks: Record<string, AlarmAck>;
  /** 确认告警（本地记录，后端接口待建） */
  ackAlarm: (alarmId: string, ack: Omit<AlarmAck, 'ts'>) => void;
}

export const useAlarmAckStore = create<AlarmAckState>()(
  devtools(
    persist(
      subscribeWithSelector((set) => ({
        acks: {},
        ackAlarm: (alarmId, ack) =>
          set(
            (state) => ({
              acks: {
                ...state.acks,
                [alarmId]: { ...ack, ts: new Date().toISOString() },
              },
            }),
            false,
            'ackAlarm',
          ),
      })),
      { name: 'pdm_ui_alarm_ack' },
    ),
    { name: 'pdm_ui_alarm_ack' },
  ),
);
