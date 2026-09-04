export function classificationBadge(classification) {
  if (!classification) return 'pending';
  const c = String(classification).toUpperCase();
  if (c.includes('BEFORE')) return 'before';
  if (c.includes('AFTER')) return 'after';
  if (c.includes('MISSTATEMENT')) return 'misstatement';
  if (c.includes('UNRESOLVED') || c.includes('DATA_QUALITY')) return 'unresolved';
  return 'pending';
}

export function formatLabel(value) {
  if (!value) return 'N/A';
  return String(value).replace(/_/g, ' ');
}

export function formatDate(value) {
  if (!value) return '—';
  return String(value).split('T')[0];
}

export function confidenceCaption(confidence, classification) {
  const pct = Math.round((confidence || 0) * 100);
  const forced = ['BEFORE_CUTOFF', 'AFTER_CUTOFF'].includes(classification);
  if (!forced || pct < 90) {
    return `${pct}% is a model score, not proof. Treat evidence as authoritative.`;
  }
  return `${pct}% score — still verify against the evidence bundle below.`;
}
