export interface DraftPosition {
  ticker: string;
  amount: number;
}

export function computeTotal(positions: DraftPosition[]): number {
  return positions.reduce((sum, p) => sum + p.amount, 0);
}

export function computeWeights(positions: DraftPosition[]): number[] {
  const total = computeTotal(positions);
  if (total === 0) return positions.map(() => 0);
  return positions.map((p) => p.amount / total);
}

export function scaleAmounts(positions: DraftPosition[], newTotal: number): DraftPosition[] {
  const total = computeTotal(positions);
  if (total === 0) {
    const even = positions.length > 0 ? newTotal / positions.length : 0;
    return positions.map((p) => ({ ...p, amount: even }));
  }
  const ratio = newTotal / total;
  return positions.map((p) => ({ ...p, amount: p.amount * ratio }));
}
