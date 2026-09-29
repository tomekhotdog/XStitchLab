/** Left column: "Start from" chooser, the ordered OpCards, AddOpMenu, and the Run button. */

import { useEffect, useState } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { AddOpMenu } from './AddOpMenu';
import { ConfirmDialog } from './ConfirmDialog';
import { OpCard } from './OpCard';
import { useToast } from './Toast';

const STARTS: { name: string; label: string }[] = [
  { name: 'predesigned', label: 'Predesigned' },
  { name: 'photo', label: 'Photo' },
];

interface Pending {
  message: string;
  confirmLabel: string;
  run(): void;
}

export function RecipePanel() {
  const loadOps = useEditorStore((s) => s.loadOps);
  const opSchemas = useEditorStore((s) => s.opSchemas);
  const defaults = useEditorStore((s) => s.defaults);
  const recipe = useEditorStore((s) => s.recipe);
  const design = useEditorStore((s) => s.design);
  const hasInput = useEditorStore((s) => s.hasInput);
  const dirty = useEditorStore((s) => s.dirty);
  const running = useEditorStore((s) => s.running);
  const runError = useEditorStore((s) => s.runError);
  const loadDefault = useEditorStore((s) => s.loadDefault);
  const runRecipe = useEditorStore((s) => s.runRecipe);
  const show = useToast((s) => s.show);
  const [pending, setPending] = useState<Pending | null>(null);
  const [opsError, setOpsError] = useState<string | null>(null);

  useEffect(() => {
    loadOps().catch((e: unknown) => setOpsError(e instanceof Error ? e.message : String(e)));
  }, [loadOps]);

  const recipeJson = JSON.stringify(recipe);
  const activeStart = STARTS.find((s) => defaults[s.name] && JSON.stringify(defaults[s.name]) === recipeJson)?.name;

  const run = async () => {
    await runRecipe();
    const err = useEditorStore.getState().runError;
    if (err && err.step_index === undefined) show(err.message);
  };

  const onRun = () => {
    if (dirty) {
      setPending({ message: 'Running replaces your unsaved edits. Run anyway?', confirmLabel: 'Run anyway', run: () => void run() });
    } else {
      void run();
    }
  };

  const onStart = (name: string) => {
    if (recipe.length > 0 && activeStart !== name) {
      setPending({
        message: `Replace the current recipe with the ${name} default?`,
        confirmLabel: 'Replace',
        run: () => loadDefault(name),
      });
    } else {
      loadDefault(name);
    }
  };

  return (
    <div className="recipe-panel">
      <div className="recipe-head">
        <h2>Recipe</h2>
        <div className="recipe-start">
          <span className="muted small">Start from:</span>
          <div className="segmented" role="group" aria-label="Start from">
            {STARTS.map((s) => (
              <button key={s.name} type="button" aria-pressed={activeStart === s.name} disabled={!defaults[s.name]} onClick={() => onStart(s.name)}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {opsError && <p className="error small">Could not load operations: {opsError}</p>}

      {recipe.length === 0 ? (
        <p className="muted small">No operations yet. Start from a default or add an operation.</p>
      ) : (
        <div className="op-list">
          {recipe.map((call, i) => (
            <OpCard
              key={i}
              index={i}
              call={call}
              count={recipe.length}
              schema={opSchemas.find((s) => s.name === call.op)}
              error={runError?.step_index === i ? runError.message : undefined}
            />
          ))}
        </div>
      )}

      <AddOpMenu />

      <div className="recipe-run">
        <button type="button" className="primary" data-testid="run" disabled={running || !hasInput || recipe.length === 0} onClick={onRun}>
          {running ? 'Running…' : 'Run recipe'}
        </button>
        {!hasInput && design && <span className="muted small">Add an input image first</span>}
      </div>

      {pending && (
        <ConfirmDialog
          message={pending.message}
          confirmLabel={pending.confirmLabel}
          onCancel={() => setPending(null)}
          onConfirm={() => {
            setPending(null);
            pending.run();
          }}
        />
      )}
    </div>
  );
}
