import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));

export const REPO_ROOT = path.resolve(here, '..', '..');
/** Throwaway design library the e2e backend serves (`XSTITCH_DESIGNS_DIR`); wiped on every run. */
export const DESIGNS_DIR = path.join(here, '.tmp-designs');
export const SLUG = '01-three-brothers-riga';
export const DESIGN_JSON = path.join(DESIGNS_DIR, SLUG, 'design.json');
