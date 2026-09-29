/** Centre of the editor for a Design without a Pattern: the three-step path, tab shortcuts, and a first-upload drop zone. */

import { inputUrl } from '@/api/client';
import { useEditorStore } from '@/store/editorStore';
import { DropZone } from './DropZone';

export function EmptyState() {
  const slug = useEditorStore((s) => s.slug);
  const hasInput = useEditorStore((s) => s.hasInput);
  const inputVersion = useEditorStore((s) => s.inputVersion);
  const setPanel = useEditorStore((s) => s.setPanel);
  const uploadInput = useEditorStore((s) => s.uploadInput);

  return (
    <div className="empty-state centre">
      <h2>No pattern yet</h2>
      <ol className="empty-steps">
        <li>Write the brief and paste it into your image generator</li>
        <li className={hasInput ? 'done' : undefined}>Drop the PNG here</li>
        <li>Run a recipe</li>
      </ol>
      <div className="empty-actions">
        <button type="button" onClick={() => setPanel('brief')}>Go to Brief</button>
        <button type="button" className={hasInput ? 'primary' : undefined} onClick={() => setPanel('recipe')}>Go to Recipe</button>
      </div>
      {hasInput && slug && (
        <figure className="input-preview">
          <img src={`${inputUrl(slug)}?v=${inputVersion}`} alt="Input image" />
          <figcaption className="muted small">Input ready. Switch to Recipe and run.</figcaption>
        </figure>
      )}
      <DropZone compact={hasInput} onFile={(file) => void uploadInput(file)} />
    </div>
  );
}
