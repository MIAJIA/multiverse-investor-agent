import type { Look } from '../status';

export default function Badge({ look, title }: { look: Look; title?: string }) {
  return (
    <span className="badge" title={title} style={{ color: look.color, background: look.bg, borderColor: look.color }}>
      {look.label}
    </span>
  );
}
