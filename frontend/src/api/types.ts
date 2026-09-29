/** Wire shapes, mirroring `backend/app/schemas.py` and `Pattern.to_dict()` exactly. */

export type Rgb = [number, number, number];

export interface PatternMetadata {
  title: string;
  width: number;
  height: number;
  color_count: number;
  total_stitches: number;
  difficulty: string;
  fabric_count: number;
  fabric_width_inches: number;
  fabric_height_inches: number;
  source_image: string | null;
}

export interface LegendEntry {
  symbol: string;
  dmc_code: string;
  dmc_name: string;
  rgb: Rgb;
  stitch_count: number;
}

/** Backstitch segment in grid-corner coordinates. */
export interface Segment {
  start: [number, number];
  end: [number, number];
}

export interface OpCall {
  op: string;
  params: Record<string, unknown>;
}

export interface Pattern {
  metadata: PatternMetadata;
  legend: LegendEntry[];
  /** grid[y][x] = legend index */
  grid: number[][];
  backstitch: Segment[];
  background_index: number | null;
  recipe: OpCall[];
}

export type OpKind = 'image' | 'pixelate' | 'pattern';

/** A JSON Schema object (from pydantic's `model_json_schema`). */
export type JsonSchema = Record<string, unknown>;

export interface OpSchema {
  name: string;
  kind: OpKind;
  group: string;
  title: string;
  description: string;
  schema: JsonSchema;
}

export interface DesignSummary {
  slug: string;
  title: string;
  has_input: boolean;
  has_prompt: boolean;
  has_pattern: boolean;
  width: number | null;
  height: number | null;
  colors: number | null;
  stitches: number | null;
  /** Raw base64 PNG; see `pngSrc`. */
  thumbnail_png: string | null;
}

export interface DesignDetail {
  slug: string;
  title: string;
  prompt: string;
  has_input: boolean;
  pattern: Pattern | null;
  history: string;
  /** Opaque design.json version; sent back on save so a stale tab gets 409 instead of overwriting. */
  version: string | null;
}

export interface Step {
  name: string;
  params: Record<string, unknown>;
  kind: OpKind;
  /** Raw base64 PNG; see `pngSrc`. */
  preview_png: string;
  stats: Record<string, number>;
}

export interface RunResponse {
  pattern: Pattern;
  steps: Step[];
}

export interface ThreadRow {
  dmc_code: string;
  name: string;
  rgb: Rgb;
  stitch_count: number;
  meters: number;
  skeins: number;
  skeins_decimal: number;
  sections_60cm: number;
  is_background: boolean;
  is_backstitch: boolean;
}

export interface ThreadTotals {
  stitches: number;
  meters: number;
  skeins: number;
  sections_60cm: number;
}

export interface ThreadsResponse {
  rows: ThreadRow[];
  totals: ThreadTotals;
}

export interface DmcColour {
  code: string;
  name: string;
  rgb: Rgb;
}

export type ExportKind = 'sheet' | 'pdf' | 'png-color' | 'png-symbol' | 'json' | (string & {});
export type SheetLayout = 'a4' | 'a5';
