import fs from 'node:fs';
import path from 'node:path';
import { DESIGNS_DIR, REPO_ROOT, SLUG } from './paths';

const FILES = ['design.json', 'design.md', 'input.png', 'prompt.md', 'history.md'];

/** Fresh copy of the Riga design so the smoke test can save without touching `designs/`. */
export default function globalSetup() {
  fs.rmSync(DESIGNS_DIR, { recursive: true, force: true });
  const dest = path.join(DESIGNS_DIR, SLUG);
  fs.mkdirSync(dest, { recursive: true });
  for (const f of FILES) fs.copyFileSync(path.join(REPO_ROOT, 'designs', SLUG, f), path.join(dest, f));
}
