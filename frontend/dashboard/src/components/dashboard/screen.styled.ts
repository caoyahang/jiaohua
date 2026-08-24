/**
 * 大屏 DataV 科技风配套的 styled-components（前端规范：样式集中于 *.styled.ts）。
 * 覆盖范围：整屏网格纹理底、标题发光字效、ScrollBoard 文字色覆盖。
 * 颜色全部插值自 src/styles/tokens.ts 的 darkColors（红线4）。
 */
import styled from 'styled-components';
import { darkColors } from '../../styles/tokens';

/**
 * 大屏整屏外壳：深色底 + 低透明度点阵纹理（radial-gradient，token 色 + 透明度后缀，
 * 与 Tailwind 的 darkAccentCyanDim/60 同一派生手法）。
 */
export const ScreenShell = styled.div`
  min-height: 100%;
  background-color: ${darkColors.bgDeep};
  background-image: radial-gradient(${darkColors.accentCyanDim}40 1px, transparent 1px);
  background-size: 24px 24px;
`;

/** 大屏标题发光字效：token 青色双层光晕 */
export const GlowTitle = styled.h1`
  white-space: nowrap;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.3em;
  color: ${darkColors.accentCyan};
  text-shadow:
    0 0 8px ${darkColors.accentCyan}b3,
    0 0 24px ${darkColors.accentCyan}66;
`;

/**
 * ScrollBoard 轮播表文字色覆盖：默认 #fff 改为 token 正文色；
 * 单元格内的高亮 span 由组件数据侧按 token 生成（DANGER 行红色）。
 */
export const ScrollBoardWrap = styled.div`
  height: 100%;
  min-height: 8rem;
  /* ScrollBoard 行高按容器算死，溢出必须裁掉，不能画出面板边框 */
  overflow: hidden;

  .dv-scroll-board {
    color: ${darkColors.text};

    .header {
      font-weight: 700;
    }

    .row-item {
      font-size: 13px;
    }
  }
`;

/** BorderBox 边框层：absolute 铺满父面板、不拦截点击（替代内联 style，红线3） */
export const BorderLayer = styled.div`
  position: absolute;
  inset: 0;
  pointer-events: none;
`;
