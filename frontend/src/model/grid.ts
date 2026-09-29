/** Pure grid helpers. Grids are `grid[y][x]` legend indices; nothing here mutates its input. */

export interface Change {
  x: number;
  y: number;
  from: number;
  to: number;
}

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Cell {
  x: number;
  y: number;
}

export const cloneGrid = (grid: number[][]): number[][] => grid.map((row) => row.slice());

const inBounds = (grid: number[][], x: number, y: number) =>
  y >= 0 && y < grid.length && x >= 0 && x < (grid[y]?.length ?? 0);

/** 4-connected fill from (x, y) with `value`; empty when out of bounds or already that value. */
export function floodFill(grid: number[][], x: number, y: number, value: number): Change[] {
  if (!inBounds(grid, x, y)) return [];
  const from = grid[y][x];
  if (from === value) return [];
  const width = grid[0].length;
  const seen = new Uint8Array(width * grid.length);
  const stack: Cell[] = [{ x, y }];
  const changes: Change[] = [];
  while (stack.length) {
    const c = stack.pop()!;
    if (!inBounds(grid, c.x, c.y) || grid[c.y][c.x] !== from) continue;
    const i = c.y * width + c.x;
    if (seen[i]) continue;
    seen[i] = 1;
    changes.push({ x: c.x, y: c.y, from, to: value });
    stack.push({ x: c.x + 1, y: c.y }, { x: c.x - 1, y: c.y }, { x: c.x, y: c.y + 1 }, { x: c.x, y: c.y - 1 });
  }
  return changes;
}

/** Cells of a rect, row-major. */
export function rectCells(rect: Rect): Cell[] {
  const out: Cell[] = [];
  for (let y = rect.y; y < rect.y + rect.h; y++) {
    for (let x = rect.x; x < rect.x + rect.w; x++) out.push({ x, y });
  }
  return out;
}

/**
 * Move the cells of `rect` by (dx, dy): the source becomes `fill`, the destination takes the
 * source values, clipped to the grid. Changes are ordered so that applying them sequentially
 * (and each `from` recorded at that moment) gives the moved grid and stays invertible.
 */
export function moveRect(grid: number[][], rect: Rect, dx: number, dy: number, fill: number): Change[] {
  if (dx === 0 && dy === 0) return [];
  const work = cloneGrid(grid);
  const changes: Change[] = [];
  const set = (x: number, y: number, to: number) => {
    if (!inBounds(work, x, y)) return;
    const from = work[y][x];
    if (from === to) return;
    work[y][x] = to;
    changes.push({ x, y, from, to });
  };
  const cells = rectCells(rect).filter((c) => inBounds(grid, c.x, c.y));
  const values = cells.map((c) => grid[c.y][c.x]);
  for (const c of cells) set(c.x, c.y, fill);
  cells.forEach((c, i) => set(c.x + dx, c.y + dy, values[i]));
  return changes;
}

/** A new grid with `changes` applied in order; untouched rows keep their reference. */
export function applyChanges(grid: number[][], changes: Change[]): number[][] {
  const next = grid.slice();
  const copied = new Set<number>();
  for (const c of changes) {
    if (!inBounds(grid, c.x, c.y)) continue;
    if (!copied.has(c.y)) {
      next[c.y] = grid[c.y].slice();
      copied.add(c.y);
    }
    next[c.y][c.x] = c.to;
  }
  return next;
}

/** The changes that undo `changes`: reversed, with from/to swapped. */
export const invertChanges = (changes: Change[]): Change[] =>
  changes.map((c) => ({ x: c.x, y: c.y, from: c.to, to: c.from })).reverse();
