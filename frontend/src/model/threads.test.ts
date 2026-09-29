import { describe, expect, it } from 'vitest';
import { estimate, totals } from './threads';
import type { Pattern } from '@/api/types';

/** 3x3: legend 0 is the background (3 cells), legend 1 has 6 stitches, 8 backstitch units. */
const pattern: Pattern = {
  metadata: {
    title: 't', width: 3, height: 3, color_count: 2, total_stitches: 6, difficulty: 'easy',
    fabric_count: 14, fabric_width_inches: 1, fabric_height_inches: 1, source_image: null,
  },
  legend: [
    { symbol: '·', dmc_code: 'B5200', dmc_name: 'Snow White', rgb: [255, 255, 255], stitch_count: 0 },
    { symbol: '■', dmc_code: '938', dmc_name: 'Coffee Brown Ultra Dark', rgb: [54, 31, 14], stitch_count: 0 },
  ],
  grid: [
    [0, 0, 0],
    [1, 1, 1],
    [1, 1, 1],
  ],
  backstitch: [
    { start: [0, 0], end: [3, 0] }, // 3 units
    { start: [3, 3], end: [0, 3] }, // 3 units, reversed
    { start: [0, 0], end: [0, 2] }, // 2 units
  ],
  background_index: 0,
  recipe: [],
};

describe('estimate', () => {
  const rows = estimate(pattern);

  it('counts stitches from the grid, not the stored legend counts', () => {
    expect(rows[0].stitch_count).toBe(3);
    expect(rows[1].stitch_count).toBe(6);
  });

  it('background row needs no thread', () => {
    expect(rows[0]).toMatchObject({
      dmc_code: 'B5200', meters: 0, skeins: 0, skeins_decimal: 0, sections_60cm: 0,
      is_background: true, is_backstitch: false,
    });
  });

  it('6 stitches of one colour -> 9 cm -> 1 section of 2-strand thread', () => {
    expect(rows[1]).toMatchObject({
      dmc_code: '938', name: 'Coffee Brown Ultra Dark', rgb: [54, 31, 14], stitch_count: 6,
      meters: 0.09, skeins: 1, skeins_decimal: 0.01, sections_60cm: 1,
      is_background: false, is_backstitch: false,
    });
  });

  it('8 backstitch units -> 8 cm -> 1 section of 1-strand thread', () => {
    expect(rows).toHaveLength(3);
    expect(rows[2]).toEqual({
      dmc_code: '310', name: 'Black (Backstitch, 1 strand)', rgb: [0, 0, 0], stitch_count: 8,
      meters: 0.08, skeins: 1, skeins_decimal: 0.01, sections_60cm: 1,
      is_background: false, is_backstitch: true,
    });
  });

  it('scales with the fabric count (28 ct halves the length)', () => {
    const fine = estimate({ ...pattern, metadata: { ...pattern.metadata, fabric_count: 28 } });
    expect(fine[1].meters).toBe(0.05); // ceil(6 * 1.5 * 0.5) = 5 cm
    expect(fine[2].meters).toBe(0.04);
  });

  it('omits the backstitch row when there are no segments', () => {
    expect(estimate({ ...pattern, backstitch: [] })).toHaveLength(2);
  });

  it('sections round up: 121 stitches of 2-strand -> 182 cm -> 2 sections', () => {
    const big: Pattern = {
      ...pattern, backstitch: [], background_index: null,
      grid: Array.from({ length: 11 }, () => Array.from({ length: 11 }, () => 1)),
    };
    const row = estimate(big)[1];
    expect(row.meters).toBe(1.82);
    expect(row.sections_60cm).toBe(2);
    expect(row.skeins).toBe(1);
    expect(row.skeins_decimal).toBe(0.23);
  });
});

describe('totals', () => {
  it('sums cross stitches only, plus metres, skeins and sections', () => {
    expect(totals(estimate(pattern))).toEqual({ stitches: 6, meters: 0.17, skeins: 2, sections_60cm: 2 });
  });
});
