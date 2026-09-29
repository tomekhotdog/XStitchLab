/** Title-bar Save; the store's `save()` does the work and toasts the outcome (Ctrl/Cmd+S calls the same). */

import { useEditorStore } from '@/store/editorStore';

export function SaveButton() {
  const pattern = useEditorStore((s) => s.pattern);
  const dirty = useEditorStore((s) => s.dirty);
  const saving = useEditorStore((s) => s.saving);
  const save = useEditorStore((s) => s.save);
  return (
    <button
      type="button"
      className="primary save"
      data-testid="save"
      disabled={!pattern || !dirty || saving}
      title="Save (Ctrl/Cmd+S)"
      onClick={() => void save()}
    >
      {saving ? 'Saving…' : 'Save'}
    </button>
  );
}
