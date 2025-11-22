import { describe, it, expect } from "vitest";
import { computeTotal, computeWeights, scaleAmounts } from "./portfolio-math";
import type { DraftPosition } from "./portfolio-math";

const pos = (ticker: string, amount: number): DraftPosition => ({ ticker, amount });

describe("computeTotal", () => {
  it("sums all amounts", () => {
    expect(computeTotal([pos("A", 600), pos("B", 400)])).toBe(1000);
  });
  it("returns 0 for empty array", () => {
    expect(computeTotal([])).toBe(0);
  });
  it("handles single position", () => {
    expect(computeTotal([pos("A", 50000)])).toBe(50000);
  });
});

describe("computeWeights", () => {
  it("returns proportional weights", () => {
    const w = computeWeights([pos("A", 600), pos("B", 400)]);
    expect(w[0]).toBeCloseTo(0.6);
    expect(w[1]).toBeCloseTo(0.4);
  });
  it("weights sum to 1", () => {
    const w = computeWeights([pos("A", 333), pos("B", 333), pos("C", 334)]);
    expect(w.reduce((s, x) => s + x, 0)).toBeCloseTo(1);
  });
  it("returns zeros when total is 0", () => {
    expect(computeWeights([pos("A", 0), pos("B", 0)])).toEqual([0, 0]);
  });
  it("returns empty array for no positions", () => {
    expect(computeWeights([])).toEqual([]);
  });
});

describe("scaleAmounts", () => {
  it("scales proportionally to new total", () => {
    const scaled = scaleAmounts([pos("A", 600), pos("B", 400)], 2000);
    expect(scaled[0].amount).toBeCloseTo(1200);
    expect(scaled[1].amount).toBeCloseTo(800);
  });
  it("preserves tickers", () => {
    const scaled = scaleAmounts([pos("AAPL", 500)], 1000);
    expect(scaled[0].ticker).toBe("AAPL");
  });
  it("distributes evenly when current total is 0", () => {
    const scaled = scaleAmounts([pos("A", 0), pos("B", 0)], 1000);
    expect(scaled[0].amount).toBeCloseTo(500);
    expect(scaled[1].amount).toBeCloseTo(500);
  });
  it("does not mutate original", () => {
    const original = [pos("A", 500)];
    scaleAmounts(original, 2000);
    expect(original[0].amount).toBe(500);
  });
});
