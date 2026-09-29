/**
 * Client-side thread estimate, identical to `xstitchlab/export/threads.py` so the panel can update
 * live while painting. Kit rule: on 14-count Aida a cross stitch uses ~1.5 cm of 2-strand thread
 * and a backstitch unit ~1 cm of 1-strand thread (wastage included); a pre-cut 60 cm section of
 * 6-strand floss yields 180 cm of 2-strand or 360 cm of 1-strand thread.
 */

import type { Pattern, Rgb, ThreadRow, ThreadTotals } from '@/api/types';

const DMC_SKEIN_LENGTH_METERS = 8.0;
const CM_PER_STITCH_14CT = 1.5;
const CM_PER_BACKSTITCH_UNIT_14CT = 1.0;
const SECTION_CM = 60;
const FLOSS_STRANDS = 6;
const CROSS_STRANDS = 2;
const BACKSTITCH_STRANDS = 1;
export const BACKSTITCH_CODE = '310';
export const BACKSTITCH_NAME = 'Black (Backstitch, 1 strand)';
const BACKSTITCH_RGB: Rgb = [0, 0, 0];

// Python rounds half to even; at an exact .xx5 the live estimate can differ by 0.01 until the saved value comes back.
const round2 = (v: number) => Math.round(v * 100) / 100;

/** Stitch count per legend index, derived from the grid. */
export function countStitches(pattern: Pattern): number[] {
  const counts = new Array<number>(pattern.legend.length).fill(0);
  for (const row of pattern.grid) for (const v of row) if (v >= 0 && v < counts.length) counts[v]++;
  return counts;
}

/** Total unit length of the backstitch segments. */
export const backstitchUnits = (pattern: Pattern) =>
  pattern.backstitch.reduce((sum, s) => sum + Math.max(Math.abs(s.end[0] - s.start[0]), Math.abs(s.end[1] - s.start[1])), 0);

/** One row per legend entry (legend order), then a backstitch row if any segments. */
export function estimate(pattern: Pattern, fabricCount?: number): ThreadRow[] {
  const counts = countStitches(pattern);
  const count = fabricCount || pattern.metadata.fabric_count || 14;
  const scale = 14 / count;
  const rows = pattern.legend.map((entry, idx) => {
    const isBackground = idx === pattern.background_index;
    const cm = isBackground ? 0 : Math.ceil(counts[idx] * CM_PER_STITCH_14CT * scale);
    return row(entry.dmc_code, entry.dmc_name, entry.rgb, counts[idx], cm, CROSS_STRANDS, isBackground, false);
  });
  const units = backstitchUnits(pattern);
  if (units) {
    const cm = Math.ceil(units * CM_PER_BACKSTITCH_UNIT_14CT * scale);
    rows.push(row(BACKSTITCH_CODE, BACKSTITCH_NAME, BACKSTITCH_RGB, units, cm, BACKSTITCH_STRANDS, false, true));
  }
  return rows;
}

/** {stitches (cross stitches only), meters, skeins, sections_60cm} over `rows`. */
export function totals(rows: ThreadRow[]): ThreadTotals {
  return {
    stitches: rows.filter((r) => !r.is_background && !r.is_backstitch).reduce((s, r) => s + r.stitch_count, 0),
    meters: round2(rows.reduce((s, r) => s + r.meters, 0)),
    skeins: rows.reduce((s, r) => s + r.skeins, 0),
    sections_60cm: rows.reduce((s, r) => s + r.sections_60cm, 0),
  };
}

function row(
  code: string, name: string, rgb: Rgb, stitchCount: number, cm: number, strands: number,
  isBackground: boolean, isBackstitch: boolean,
): ThreadRow {
  const usableCmPerSection = Math.floor((SECTION_CM * FLOSS_STRANDS) / strands);
  const meters = cm / 100;
  const skeinsDecimal = meters / DMC_SKEIN_LENGTH_METERS;
  return {
    dmc_code: code,
    name,
    rgb: [rgb[0], rgb[1], rgb[2]],
    stitch_count: stitchCount,
    meters: round2(meters),
    skeins: Math.ceil(skeinsDecimal),
    skeins_decimal: round2(skeinsDecimal),
    sections_60cm: Math.ceil(cm / usableCmPerSection),
    is_background: isBackground,
    is_backstitch: isBackstitch,
  };
}
