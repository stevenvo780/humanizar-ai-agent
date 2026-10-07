import { Sparkles } from 'lucide-react';

export function BrandMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark ${small ? 'brand-mark-small' : ''}`} aria-hidden="true">
      <Sparkles strokeWidth={1.5} />
    </span>
  );
}
