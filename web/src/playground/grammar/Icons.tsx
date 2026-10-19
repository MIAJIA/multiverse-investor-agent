// 节点类型符号（线条风格参照 Lucide：zap / cloud-lightning / cog / circle-help / flag / search / pencil），单色，跟文字同色。
import type { Claim } from '../../types';

const P = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const;

function Svg({ size = 16, children }: { size?: number; children: React.ReactNode }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" {...P}>{children}</svg>;
}

export const Zap = ({ size }: { size?: number }) => <Svg size={size}><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" /></Svg>;
export const CloudBolt = ({ size }: { size?: number }) => (
  <Svg size={size}><path d="M6 16.3A5 5 0 1 1 15.9 9h1.6a4.5 4.5 0 0 1 1.7 8.7" /><path d="m13 12-3 5h4l-3 5" /></Svg>
);
export const Cog = ({ size }: { size?: number }) => (
  <Svg size={size}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1" /></Svg>
);
export const Help = ({ size }: { size?: number }) => (
  <Svg size={size}><circle cx="12" cy="12" r="10" /><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3" /><path d="M12 17h.01" /></Svg>
);
export const Flag = ({ size }: { size?: number }) => (
  <Svg size={size}><path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.3 2.8A6 6 0 0 0 20 4v10a6 6 0 0 1-4.7.8C13 14 11 12 8 12a6 6 0 0 0-4 1.3" /></Svg>
);
export const Search = ({ size }: { size?: number }) => <Svg size={size}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></Svg>;
export const Pencil = ({ size }: { size?: number }) => (
  <Svg size={size}><path d="M17 3a2.8 2.8 0 0 1 4 4L7.5 20.5 2 22l1.5-5.5z" /><path d="m15 5 4 4" /></Svg>
);

export const TYPE_ICON: Record<Claim['role'], (p: { size?: number }) => React.ReactElement> = {
  event: Zap, shock: CloudBolt, intermediate: Cog, assumption: Help, terminal: Flag,
};
