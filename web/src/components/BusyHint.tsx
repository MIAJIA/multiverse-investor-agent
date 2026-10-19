// 长请求的等待提示：真实的已用时间 + 一句说明。后端不报告进行到哪一步，所以不显示进度条、百分比或编出来的阶段。
import { useEffect, useState } from 'react';
import { T } from '../strings';

export type BusyKind = 'analyze' | 'fork' | 'sign';

export default function BusyHint({ kind, since, online, center }: {
  kind: BusyKind; since: number; online: boolean; center?: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const secs = Math.max(0, Math.floor((now - since) / 1000));
  const title = kind === 'analyze' ? T.busy.analyze : kind === 'fork' ? T.busy.fork : T.busy.sign;
  const note = kind === 'analyze' ? T.busy.analyzeNote : kind === 'fork' ? T.busy.forkNote : T.busy.signNote;
  return (
    <div className={center ? 'busy-hint center' : 'busy-hint'} role="status" aria-live="polite">
      <div className="busy-row">
        <span className="busy-dot" aria-hidden="true" />
        <strong>{title}</strong>
        <span className="busy-time">{T.busy.elapsed(secs)}</span>
      </div>
      <div className="busy-note">{note}{kind === 'analyze' && online ? ` ${T.busy.analyzeOnline}` : ''}</div>
    </div>
  );
}
