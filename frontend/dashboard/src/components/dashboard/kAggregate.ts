/**
 * K 系数行按日期聚合：三班取平均，供趋势图使用。
 * 口径说明：日值=当日三班算术平均，与 docs/操作手册.md 验收章节的班次考核口径不冲突
 * （大屏只展示趋势，不作考核判定）。
 */
import type { KCoefficientRow } from '../../api/types';

export interface DailyK {
  date: string;
  k_uniform: number;
  k_stable: number;
  k1: number;
  k2: number;
  k3: number;
}

/** 近 7 天逐日聚合（入参须已按时间升序） */
export function aggregateByDate(rows: KCoefficientRow[]): DailyK[] {
  const round3 = (v: number) => Math.round(v * 1000) / 1000;
  const byDate = new Map<string, KCoefficientRow[]>();
  for (const r of rows) {
    const list = byDate.get(r.shift_date) ?? [];
    list.push(r);
    byDate.set(r.shift_date, list);
  }
  return [...byDate.entries()].map(([date, list]) => {
    const avg = (pick: (r: KCoefficientRow) => number) =>
      round3(list.reduce((s, r) => s + pick(r), 0) / list.length);
    return {
      date: date.slice(5), // 只留 MM-DD，大屏横向空间优先
      k_uniform: avg((r) => r.k_uniform),
      k_stable: avg((r) => r.k_stable),
      k1: avg((r) => r.k1),
      k2: avg((r) => r.k2),
      k3: avg((r) => r.k3),
    };
  });
}
