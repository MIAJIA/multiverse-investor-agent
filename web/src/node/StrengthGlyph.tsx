// 证据符号的两种画法：圆环（Activity 圆环）和信号格（手机信号）。
import { SLOTS, type Strength } from './strength';

const COLOR = { support: 'var(--pg-green)', contra: 'var(--pg-red)', neutral: 'var(--pg-muted)', empty: 'var(--pg-track)' };

export function Ring({ s, size = 22 }: { s: Strength; size?: number }) {
  const r = 9;
  const c = 2 * Math.PI * r;
  const gap = 2.2;
  const seg = c / SLOTS - gap;
  if (s.modelOnly || s.noInEdges) {
    return (
      <svg width={size} height={size} viewBox="0 0 22 22" aria-label={s.modelOnly ? '仅模型推断' : '没有入边证据'}>
        <circle cx="11" cy="11" r={r} fill="none" stroke="var(--pg-muted)" strokeWidth={s.modelOnly ? 2 : 3}
          strokeDasharray={s.modelOnly ? '1.5 3' : undefined} opacity={s.modelOnly ? 1 : 0.35} />
      </svg>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 22 22" aria-label={`正方 ${s.support}，反方 ${s.contra}`}>
      {s.slots.map((slot, i) => (
        <circle key={i} cx="11" cy="11" r={r} fill="none" stroke={COLOR[slot]} strokeWidth="3"
          strokeDasharray={`${seg} ${c - seg}`} strokeDashoffset={-i * (seg + gap)} transform="rotate(-90 11 11)" />
      ))}
    </svg>
  );
}

export function Bars({ s }: { s: Strength }) {
  const empty = s.modelOnly || s.noInEdges;
  const filled = Math.min(s.support, SLOTS);
  return (
    <span className="pg-bars" aria-label={empty ? '没有引用' : `正方 ${s.support}，反方 ${s.contra}`}>
      <svg width="20" height="16" viewBox="0 0 20 16">
        {[0, 1, 2].map((i) => (
          <rect key={i} x={i * 7} y={10 - i * 5} width="5" height={6 + i * 5} rx="1.2"
            fill={!empty && i < filled ? 'var(--pg-green)' : 'none'}
            stroke={!empty && i < filled ? 'var(--pg-green)' : 'var(--pg-muted)'}
            strokeWidth="1" strokeDasharray={s.modelOnly ? '2 1.5' : undefined} />
        ))}
      </svg>
      {s.contra > 0 && <span className="pg-contra">{s.contra}</span>}
    </span>
  );
}
