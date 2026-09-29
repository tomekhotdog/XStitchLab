/**
 * Left-column "Brief" tab: the prompt (with template insert, copy, save), the Input image drop
 * zone with preview, and the History paragraph printed on the Pattern Sheet.
 */

import { useEffect, useRef, useState } from 'react';
import { inputUrl, promptTemplate } from '@/api/client';
import { useEditorStore } from '@/store/editorStore';
import { ConfirmDialog } from './ConfirmDialog';
import { DropZone } from './DropZone';
import { useToast } from './Toast';

const MIN_ROWS = 12;
const rowsFor = (text: string, min: number) => Math.max(min, text.split('\n').length + 1);

export function BriefPanel() {
  const slug = useEditorStore((s) => s.slug);
  const prompt = useEditorStore((s) => s.prompt);
  const historyText = useEditorStore((s) => s.historyText);
  const hasInput = useEditorStore((s) => s.hasInput);
  const inputVersion = useEditorStore((s) => s.inputVersion);
  const pattern = useEditorStore((s) => s.pattern);
  const savePrompt = useEditorStore((s) => s.savePrompt);
  const saveHistory = useEditorStore((s) => s.saveHistory);
  const uploadInput = useEditorStore((s) => s.uploadInput);
  const setPanel = useEditorStore((s) => s.setPanel);
  const show = useToast((s) => s.show);

  const [text, setText] = useState(prompt);
  const [history, setHistory] = useState(historyText);
  const [confirmTemplate, setConfirmTemplate] = useState(false);
  const [busy, setBusy] = useState<'prompt' | 'history' | 'template' | null>(null);
  /** The template is fetched at most once per mounted panel. */
  const template = useRef<Promise<string> | null>(null);

  useEffect(() => setText(prompt), [prompt]);
  useEffect(() => setHistory(historyText), [historyText]);

  const insertTemplate = async () => {
    setBusy('template');
    try {
      template.current ??= promptTemplate();
      setText(await template.current);
    } catch (e) {
      template.current = null;
      show(`Could not load the template: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(null);
    }
  };

  const onInsertTemplate = () => {
    if (text.trim() === '') void insertTemplate();
    else setConfirmTemplate(true);
  };

  const onCopy = () => {
    navigator.clipboard
      .writeText(text)
      .then(() => show('Brief copied'))
      .catch(() => show('Could not copy; select the text and copy it by hand.'));
  };

  const onSavePrompt = async () => {
    setBusy('prompt');
    await savePrompt(text);
    setBusy(null);
  };

  const onSaveHistory = async () => {
    setBusy('history');
    await saveHistory(history);
    setBusy(null);
  };

  return (
    <div className="brief">
      <section className="brief-section">
        <h2>Brief</h2>
        <p className="muted small">Paste this into your image generator; the result becomes the Input.</p>
        <textarea
          className="brief-text mono"
          data-testid="brief-text"
          aria-label="Brief"
          rows={rowsFor(text, MIN_ROWS)}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe the building: subject, proportions, colours, what to leave out…"
        />
        <div className="brief-actions">
          <button type="button" disabled={busy === 'template'} onClick={onInsertTemplate}>Insert template</button>
          <button type="button" disabled={text === ''} onClick={onCopy}>Copy</button>
          <button type="button" className="primary" disabled={text === prompt || busy === 'prompt'} onClick={() => void onSavePrompt()}>
            {busy === 'prompt' ? 'Saving…' : 'Save brief'}
          </button>
        </div>
      </section>

      <section className="brief-section">
        <h2>Input image</h2>
        {hasInput && slug && (
          <figure className="input-preview">
            <img src={`${inputUrl(slug)}?v=${inputVersion}`} alt="Input image" />
          </figure>
        )}
        <DropZone compact={hasInput} onFile={(file) => void uploadInput(file)} />
        {hasInput && !pattern && (
          <p className="hint-next small">
            <span>Now switch to Recipe and run</span>
            <button type="button" className="primary" onClick={() => setPanel('recipe')}>Go to Recipe</button>
          </p>
        )}
      </section>

      <section className="brief-section">
        <h2>
          <label htmlFor="history-text">History</label>
        </h2>
        <p className="muted small">A short paragraph printed on the pattern sheet.</p>
        <textarea
          id="history-text"
          className="history-text"
          rows={rowsFor(history, 4)}
          value={history}
          onChange={(e) => setHistory(e.target.value)}
        />
        <div className="brief-actions">
          <button type="button" className="primary" disabled={history === historyText || busy === 'history'} onClick={() => void onSaveHistory()}>
            {busy === 'history' ? 'Saving…' : 'Save history'}
          </button>
        </div>
      </section>

      {confirmTemplate && (
        <ConfirmDialog
          message="Replace the current brief with the template?"
          confirmLabel="Replace"
          onCancel={() => setConfirmTemplate(false)}
          onConfirm={() => {
            setConfirmTemplate(false);
            void insertTemplate();
          }}
        />
      )}
    </div>
  );
}
