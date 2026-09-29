import fs from 'node:fs';
import { expect, test } from '@playwright/test';
import { DESIGN_JSON, SLUG } from './paths';

type Grid = number[][];

const diffCells = (a: Grid, b: Grid) => {
  let n = 0;
  for (let y = 0; y < Math.max(a.length, b.length); y++)
    for (let x = 0; x < Math.max(a[y]?.length ?? 0, b[y]?.length ?? 0); x++) if (a[y]?.[x] !== b[y]?.[x]) n++;
  return n;
};

/**
 * The whole loop a stitcher relies on: open a design, re-run its recipe, paint one cell, save —
 * and the edit (and only the edit) lands in design.json on disk.
 */
test('library → run recipe → paint → save persists the edit', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: /Three Brothers, Riga/ }).click();
  await expect(page).toHaveURL(new RegExp(`/d/${SLUG}$`));
  const canvas = page.getByTestId('pattern-canvas');
  await expect(canvas).toBeVisible();

  await page.getByRole('tab', { name: 'Recipe' }).click();
  const run = page.getByTestId('run');
  await expect(run).toBeEnabled();
  const runResponse = page.waitForResponse((r) => r.url().endsWith(`/api/designs/${SLUG}/run`) && r.request().method() === 'POST', {
    timeout: 90_000,
  });
  await run.click();
  const response = await runResponse;
  expect(response.ok(), `run failed: ${response.status()} ${await response.text()}`).toBe(true);
  const ranGrid: Grid = (await response.json()).pattern.grid;
  await expect(page.getByRole('region', { name: 'Recipe steps' }).locator('.step-thumb')).toHaveCount(3);
  await expect(run).toBeEnabled();

  const save = page.getByTestId('save');
  await expect(save).toBeDisabled();

  // Paint with the second legend colour somewhere inside the grid (a fitted 45×45 grid is centred).
  await page.locator('body').press('b');
  await page.locator('body').press('2');
  const box = await canvas.boundingBox();
  if (!box) throw new Error('canvas has no bounding box');
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height * 0.4);

  await expect(save).toBeEnabled();
  await save.click();
  await expect(page.getByRole('status').filter({ hasText: 'Saved' })).toBeVisible();

  const savedGrid: Grid = JSON.parse(fs.readFileSync(DESIGN_JSON, 'utf8')).grid;
  const changed = diffCells(ranGrid, savedGrid);
  expect(changed).toBeGreaterThanOrEqual(1);
  expect(changed).toBeLessThanOrEqual(4);

  // The saved pattern is what the editor loads back.
  await page.reload();
  await expect(canvas).toBeVisible();
  await expect(save).toBeDisabled();
});
