/**
 * One control for one JSON Schema property (pydantic output): number input (+ slider when bounded),
 * switch, segmented control / select for enums, text input, and a "default" checkbox for optional
 * (`anyOf [..., null]`) fields. Emits values with the right JS type.
 */

import { useId } from 'react';
import type { JsonSchema } from '@/api/types';

interface Props {
  name: string;
  schema: JsonSchema;
  value: unknown;
  onChange(key: string, value: unknown): void;
}

const SEGMENTED_MAX = 4;

export const humanise = (key: string) => {
  const words = key.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
};

/** Splits `anyOf: [inner, {type:'null'}]` into its inner schema; otherwise the schema itself. */
function unwrap(schema: JsonSchema): { inner: JsonSchema; nullable: boolean } {
  const anyOf = schema.anyOf;
  if (Array.isArray(anyOf)) {
    const options = anyOf as JsonSchema[];
    const nullable = options.some((o) => o.type === 'null');
    const inner = options.find((o) => o.type !== 'null') ?? {};
    if (nullable) return { inner, nullable: true };
  }
  return { inner: schema, nullable: false };
}

const num = (v: unknown) => (typeof v === 'number' ? v : undefined);

/** Value to switch to when the user turns "default" off. */
function concreteDefault(inner: JsonSchema): unknown {
  if (inner.default !== undefined && inner.default !== null) return inner.default;
  if (Array.isArray(inner.enum)) return inner.enum[0];
  switch (inner.type) {
    case 'integer':
    case 'number':
      return num(inner.minimum) ?? 0;
    case 'boolean':
      return false;
    default:
      return '';
  }
}

export function ParamField({ name, schema, value, onChange }: Props) {
  const id = useId();
  const { inner, nullable } = unwrap(schema);
  const label = typeof schema.title === 'string' ? schema.title : humanise(name);
  const description = typeof schema.description === 'string' ? schema.description : undefined;
  const isDefault = nullable && (value === null || value === undefined);
  const shown = isDefault ? (inner.default ?? concreteDefault(inner)) : value;

  return (
    <div className="field">
      <div className="field-head">
        <label htmlFor={id}>{label}</label>
        {nullable && (
          <label className="field-auto small">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => onChange(name, e.target.checked ? null : concreteDefault(inner))}
            />
            default
          </label>
        )}
      </div>
      <Control id={id} name={name} schema={inner} value={shown} disabled={isDefault} onChange={onChange} />
      {description && <p className="field-help muted small">{description}</p>}
    </div>
  );
}

interface ControlProps {
  id: string;
  name: string;
  schema: JsonSchema;
  value: unknown;
  disabled: boolean;
  onChange(key: string, value: unknown): void;
}

function Control({ id, name, schema, value, disabled, onChange }: ControlProps) {
  if (Array.isArray(schema.enum)) {
    const options = schema.enum as (string | number)[];
    if (options.length <= SEGMENTED_MAX) {
      return (
        <div className="segmented" role="group" aria-labelledby={id} id={id}>
          {options.map((o) => (
            <button
              key={String(o)}
              type="button"
              aria-pressed={value === o}
              disabled={disabled}
              onClick={() => onChange(name, o)}
            >
              {String(o)}
            </button>
          ))}
        </div>
      );
    }
    return (
      <select
        id={id}
        value={String(value ?? '')}
        disabled={disabled}
        onChange={(e) => onChange(name, options.find((o) => String(o) === e.target.value) ?? e.target.value)}
      >
        {options.map((o) => (
          <option key={String(o)} value={String(o)}>{String(o)}</option>
        ))}
      </select>
    );
  }

  if (schema.type === 'integer' || schema.type === 'number') {
    const isInt = schema.type === 'integer';
    const min = num(schema.minimum);
    const max = num(schema.maximum);
    const step = isInt ? 1 : 0.01;
    const emit = (raw: string) => {
      if (raw === '') return;
      const n = Number(raw);
      if (Number.isFinite(n)) onChange(name, isInt ? Math.round(n) : n);
    };
    const current = num(value);
    return (
      <div className="field-number">
        <input
          id={id}
          type="number"
          value={current ?? ''}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          onChange={(e) => emit(e.target.value)}
        />
        {min !== undefined && max !== undefined && (
          <input
            type="range"
            aria-label={`${name} slider`}
            value={current ?? min}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            onChange={(e) => emit(e.target.value)}
          />
        )}
      </div>
    );
  }

  if (schema.type === 'boolean') {
    return (
      <label className="switch">
        <input id={id} type="checkbox" checked={value === true} disabled={disabled} onChange={(e) => onChange(name, e.target.checked)} />
        <span className="switch-track" aria-hidden="true" />
      </label>
    );
  }

  return (
    <input
      id={id}
      type="text"
      value={typeof value === 'string' ? value : value === undefined || value === null ? '' : String(value)}
      disabled={disabled}
      onChange={(e) => onChange(name, e.target.value)}
    />
  );
}
