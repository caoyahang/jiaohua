/**
 * 焦炉加热系统 2D 工艺示意图：炭化室 / 机·焦侧燃烧室火道 / 煤气管道 / 烟道 / 集气管，
 * 在对应位置叠加实时温度/流量/压力数值。
 * 数据源：GET /furnace/temp（后端恒 503 → 必走 mock，角标常显）。
 * 纯 SVG + 数值标签，不引新依赖；SVG 颜色全部取 darkColors token。
 */
import Panel from './Panel';
import { darkColors } from '../../styles/tokens';
import type { BurnerSide, FurnaceTempResponse, TempPoint } from '../../api/types';

interface FurnaceSchematicProps {
  temp: FurnaceTempResponse | null;
  mock?: boolean;
}

/** 火道温度越限提示区间（演示用视觉提示，非安全判定；安全钳位在 safety_limits.py） */
const TEMP_WARN_LOW = 1150;
const TEMP_WARN_HIGH = 1280;

function pointOf(temp: FurnaceTempResponse | null, side: BurnerSide): TempPoint | undefined {
  return temp?.points.find((p) => p.burner_side === side);
}

const fmt = (v: number | undefined, digits = 1): string =>
  v === undefined ? '--' : v.toFixed(digits);

export default function FurnaceSchematic({ temp, mock = false }: FurnaceSchematicProps) {
  const machine = pointOf(temp, 'machine');
  const coke = pointOf(temp, 'coke');
  const tempWarn = (v: number | undefined) =>
    v !== undefined && (v < TEMP_WARN_LOW || v > TEMP_WARN_HIGH);

  return (
    <Panel title="焦炉加热系统示意" mock={mock} border="bb8" fill className="min-h-0 flex-1">
      <svg
        viewBox="0 0 720 420"
        preserveAspectRatio="xMidYMid meet"
        className="h-full w-full"
        role="img"
        aria-label="焦炉加热系统示意"
      >
        <defs>
          {/* 发光描边滤镜：token 青色辉光（DataV 科技风质感增强） */}
          <filter id="furnace-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={darkColors.accentCyan} floodOpacity="0.7" />
          </filter>
        </defs>
        {/* ===== 集气管（炭化室上方） ===== */}
        <rect x={310} y={56} width={10} height={44} fill={darkColors.accentCyanDim} />
        <rect x={200} y={42} width={240} height={14} fill={darkColors.bgCard} stroke={darkColors.accentCyanDim} />
        <text x={320} y={53} textAnchor="middle" fontSize={11} fill={darkColors.textSecondary}>
          集气管
        </text>

        {/* ===== 三个主室：机侧燃烧室 | 炭化室 | 焦侧燃烧室 ===== */}
        {/* 机侧燃烧室 */}
        <rect x={180} y={100} width={110} height={140} fill={darkColors.bgCard} stroke={darkColors.border} />
        {[0, 1, 2, 3].map((i) => (
          <rect
            key={`m${i}`}
            x={192 + i * 25}
            y={118}
            width={14}
            height={104}
            fill={darkColors.gridLine}
            stroke={darkColors.accentCyanDim}
          />
        ))}
        <text x={235} y={112} textAnchor="middle" fontSize={11} fill={darkColors.textSecondary}>
          燃烧室·机侧
        </text>
        {/* 炭化室 */}
        <rect x={310} y={100} width={120} height={140} fill={darkColors.gridLine} stroke={darkColors.border} filter="url(#furnace-glow)" />
        <text x={370} y={168} textAnchor="middle" fontSize={13} fill={darkColors.text}>
          炭化室
        </text>
        <text x={370} y={186} textAnchor="middle" fontSize={10} fill={darkColors.textSecondary}>
          煤料 / 红焦
        </text>
        {/* 焦侧燃烧室 */}
        <rect x={450} y={100} width={110} height={140} fill={darkColors.bgCard} stroke={darkColors.border} />
        {[0, 1, 2, 3].map((i) => (
          <rect
            key={`c${i}`}
            x={462 + i * 25}
            y={118}
            width={14}
            height={104}
            fill={darkColors.gridLine}
            stroke={darkColors.accentCyanDim}
          />
        ))}
        <text x={505} y={112} textAnchor="middle" fontSize={11} fill={darkColors.textSecondary}>
          燃烧室·焦侧
        </text>

        {/* ===== 煤气管道（下方水平母管 + 两侧上升管） ===== */}
        <rect x={223} y={240} width={8} height={60} fill={darkColors.accentCyanDim} />
        <rect x={493} y={240} width={8} height={60} fill={darkColors.accentCyanDim} />
        <rect x={100} y={300} width={520} height={10} fill={darkColors.bgCard} stroke={darkColors.accentCyan} filter="url(#furnace-glow)" />
        {/* 管道流光：SMIL 虚线流动动画（stroke 取 token 青） */}
        <line x1={104} y1={305} x2={616} y2={305} stroke={darkColors.accentCyan} strokeWidth={2} strokeDasharray="10 14">
          <animate attributeName="stroke-dashoffset" from="0" to="-24" dur="1.2s" repeatCount="indefinite" />
        </line>
        <text x={360} y={326} textAnchor="middle" fontSize={11} fill={darkColors.accentCyan}>
          煤气管道
        </text>

        {/* ===== 烟道（最下方，经废气盘与燃烧室相连） ===== */}
        <rect x={253} y={240} width={8} height={110} fill={darkColors.border} />
        <rect x={523} y={240} width={8} height={110} fill={darkColors.border} />
        <rect x={200} y={350} width={320} height={12} fill={darkColors.bgCard} stroke={darkColors.border} />
        <text x={360} y={346} textAnchor="middle" fontSize={11} fill={darkColors.textSecondary}>
          烟道
        </text>

        {/* ===== 数值标签与引线 ===== */}
        <line x1={148} y1={128} x2={178} y2={140} stroke={darkColors.accentCyanDim} strokeDasharray="3 3" />
        <ValueTag x={8} y={110} label="机侧火道温度" value={fmt(machine?.fire_channel_temp)} unit="℃" warn={tempWarn(machine?.fire_channel_temp)} />
        <line x1={560} y1={140} x2={572} y2={128} stroke={darkColors.accentCyanDim} strokeDasharray="3 3" />
        <ValueTag x={572} y={110} label="焦侧火道温度" value={fmt(coke?.fire_channel_temp)} unit="℃" warn={tempWarn(coke?.fire_channel_temp)} />
        <line x1={148} y1={290} x2={223} y2={290} stroke={darkColors.accentCyanDim} strokeDasharray="3 3" />
        <ValueTag x={8} y={272} label="煤气流量" value={fmt(machine?.gas_flow, 0)} unit="m³/h" />
        <ValueTag x={480} y={8} label="集气管压力" value={fmt(machine?.collector_pressure, 0)} unit="Pa" />
        <line x1={480} y1={44} x2={430} y2={49} stroke={darkColors.accentCyanDim} strokeDasharray="3 3" />
        <ValueTag x={8} y={368} label="烟道吸力" value={fmt(machine?.flue_suction, 0)} unit="Pa" />
        <line x1={148} y1={380} x2={198} y2={356} stroke={darkColors.accentCyanDim} strokeDasharray="3 3" />
        <ValueTag x={572} y={368} label="废气残氧" value={fmt(machine?.oxygen_content)} unit="%" />
        <line x1={572} y1={380} x2={522} y2={356} stroke={darkColors.accentCyanDim} strokeDasharray="3 3" />
      </svg>
    </Panel>
  );
}

interface ValueTagProps {
  x: number;
  y: number;
  label: string;
  value: string;
  unit: string;
  /** 越限提示：数值与单位转告警橙 */
  warn?: boolean;
}

/** 数值标签：半透明底框 + 青色描边，上行标签、下行数值 */
function ValueTag({ x, y, label, value, unit, warn = false }: ValueTagProps) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width={140} height={40} fill={darkColors.bgCard} stroke={darkColors.accentCyanDim} />
      <rect width={3} height={40} fill={warn ? darkColors.accentOrange : darkColors.accentCyan} />
      <text x={10} y={16} fontSize={10} fill={darkColors.textSecondary}>
        {label}
      </text>
      <text
        x={10}
        y={33}
        fontSize={14}
        fontFamily="monospace"
        fill={warn ? darkColors.accentOrange : darkColors.accentCyan}
      >
        {value}
        <tspan fontSize={10} fill={darkColors.textSecondary}>
          {' '}
          {unit}
        </tspan>
      </text>
    </g>
  );
}
