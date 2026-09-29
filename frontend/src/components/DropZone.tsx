/**
 * Drag-and-drop or click-to-choose zone for the Input image. Validates type and size itself and
 * shows the reason inline; only a valid file reaches `onFile`.
 */

import { useRef, useState, type DragEvent, type ChangeEvent, type ReactNode } from 'react';

export const INPUT_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
export const MAX_INPUT_BYTES = 20 * 1024 * 1024;

interface Props {
  onFile(file: File): void;
  /** Shown inside the zone; defaults to a drop/click prompt. */
  children?: ReactNode;
  /** Compact variant used next to an existing preview ("Replace"). */
  compact?: boolean;
  disabled?: boolean;
}

/** Why `file` cannot be an Input, or null when it can. */
export function rejectReason(file: File): string | null {
  if (!INPUT_TYPES.includes(file.type)) return 'Please choose a PNG, JPEG or WebP image.';
  if (file.size > MAX_INPUT_BYTES) return 'That file is over 20 MB; please use a smaller image.';
  return null;
}

export function DropZone({ onFile, children, compact = false, disabled = false }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const take = (file: File | undefined) => {
    if (!file) return;
    const reason = rejectReason(file);
    setError(reason);
    if (!reason) onFile(file);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setActive(false);
    if (disabled) return;
    take(e.dataTransfer.files[0]);
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (!disabled) setActive(true);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    take(e.target.files?.[0]);
    e.target.value = ''; // so choosing the same file again fires onChange
  };

  const openPicker = () => {
    if (!disabled) input.current?.click();
  };

  return (
    <>
      <div
        className={`dropzone${active ? ' active' : ''}${compact ? ' compact' : ''}`}
        data-testid="dropzone"
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled || undefined}
        aria-label={compact ? 'Replace the input image' : 'Choose an input image'}
        onClick={openPicker}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openPicker();
          }
        }}
        onDragOver={onDragOver}
        onDragLeave={() => setActive(false)}
        onDrop={onDrop}
      >
        {children ?? (
          <>
            <strong>{compact ? 'Replace' : 'Drop the image here'}</strong>
            <span className="muted small">{compact ? 'drop or click' : 'or click to choose · PNG, JPEG or WebP, up to 20 MB'}</span>
          </>
        )}
        <input
          ref={input}
          type="file"
          accept={INPUT_TYPES.join(',')}
          data-testid="input-file"
          hidden
          onChange={onChange}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      {error && (
        <p className="error small" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
