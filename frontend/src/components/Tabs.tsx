/** Minimal accessible tabs: `role=tablist`, Left/Right/Home/End move between tabs. Inactive panels stay mounted (hidden) so their local state survives. */

import { useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface TabItem<Id extends string> {
  id: Id;
  label: string;
  content: ReactNode;
}

interface Props<Id extends string> {
  items: TabItem<Id>[];
  active: Id;
  onChange(id: Id): void;
  /** Accessible name for the tab list. */
  label: string;
}

export function Tabs<Id extends string>({ items, active, onChange, label }: Props<Id>) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const current = items.find((t) => t.id === active) ?? items[0];

  const onKeyDown = (e: KeyboardEvent, index: number) => {
    const last = items.length - 1;
    let next: number | null = null;
    if (e.key === 'ArrowRight') next = index === last ? 0 : index + 1;
    else if (e.key === 'ArrowLeft') next = index === 0 ? last : index - 1;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = last;
    if (next === null) return;
    e.preventDefault();
    onChange(items[next].id);
    buttons.current[next]?.focus();
  };

  return (
    <div className="tabs">
      <div className="tab-list" role="tablist" aria-label={label}>
        {items.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              buttons.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={t.id === current.id}
            aria-controls={`panel-${t.id}`}
            tabIndex={t.id === current.id ? 0 : -1}
            className="tab"
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {items.map((t) => (
        <div
          key={t.id}
          className="tab-panel"
          role="tabpanel"
          id={`panel-${t.id}`}
          aria-labelledby={`tab-${t.id}`}
          hidden={t.id !== current.id}
        >
          {t.content}
        </div>
      ))}
    </div>
  );
}
