import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { humanise, ParamField } from './ParamField';

describe('ParamField', () => {
  it('bounded integer: number input plus slider, emits a number', () => {
    const onChange = vi.fn();
    render(<ParamField name="n_colors" schema={{ type: 'integer', minimum: 2, maximum: 64, default: 8 }} value={8} onChange={onChange} />);
    expect(screen.getByText('N colors')).toBeInTheDocument();
    const number = screen.getByRole('spinbutton');
    const slider = screen.getByRole('slider');
    expect(number).toHaveValue(8);
    expect(slider).toHaveAttribute('min', '2');
    expect(slider).toHaveAttribute('max', '64');
    expect(slider).toHaveAttribute('step', '1');
    fireEvent.change(number, { target: { value: '12' } });
    expect(onChange).toHaveBeenCalledWith('n_colors', 12);
    fireEvent.change(slider, { target: { value: '20' } });
    expect(onChange).toHaveBeenCalledWith('n_colors', 20);
  });

  it('unbounded number: number input only, step 0.01, shows the description', () => {
    render(<ParamField name="ratio" schema={{ type: 'number', description: 'How much.' }} value={0.5} onChange={() => {}} />);
    expect(screen.queryByRole('slider')).toBeNull();
    expect(screen.getByRole('spinbutton')).toHaveAttribute('step', '0.01');
    expect(screen.getByText('How much.')).toBeInTheDocument();
  });

  it('boolean: checkbox emits a boolean', () => {
    const onChange = vi.fn();
    render(<ParamField name="dither" schema={{ type: 'boolean', default: false }} value={false} onChange={onChange} />);
    const box = screen.getByRole('checkbox');
    expect(box).not.toBeChecked();
    fireEvent.click(box);
    expect(onChange).toHaveBeenCalledWith('dither', true);
  });

  it('enum with 3 options renders a segmented control', () => {
    const onChange = vi.fn();
    render(<ParamField name="method" schema={{ type: 'string', enum: ['kmeans', 'median_cut', 'unique'] }} value="kmeans" onChange={onChange} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(3);
    expect(buttons[0]).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(buttons[1]);
    expect(onChange).toHaveBeenCalledWith('method', 'median_cut');
  });

  it('enum with 6 options renders a select', () => {
    const onChange = vi.fn();
    render(<ParamField name="mode" schema={{ type: 'string', enum: ['a', 'b', 'c', 'd', 'e', 'f'] }} value="a" onChange={onChange} />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
    const select = screen.getByRole('combobox');
    expect(select).toHaveValue('a');
    fireEvent.change(select, { target: { value: 'e' } });
    expect(onChange).toHaveBeenCalledWith('mode', 'e');
  });

  it('string: text input', () => {
    const onChange = vi.fn();
    render(<ParamField name="dmc_code" schema={{ type: 'string', default: 'auto' }} value="auto" onChange={onChange} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '310' } });
    expect(onChange).toHaveBeenCalledWith('dmc_code', '310');
  });

  it('optional integer: "default" checkbox emits null when checked and the inner value when unchecked', () => {
    const onChange = vi.fn();
    const schema = { anyOf: [{ type: 'integer', minimum: 1, maximum: 400 }, { type: 'null' }], default: null, title: 'Height' };
    const { rerender } = render(<ParamField name="height" schema={schema} value={40} onChange={onChange} />);
    const auto = screen.getByRole('checkbox', { name: /default/i });
    expect(auto).not.toBeChecked();
    expect(screen.getByRole('spinbutton')).toHaveValue(40);
    fireEvent.click(auto);
    expect(onChange).toHaveBeenLastCalledWith('height', null);

    rerender(<ParamField name="height" schema={schema} value={undefined} onChange={onChange} />);
    expect(screen.getByRole('checkbox', { name: /default/i })).toBeChecked();
    expect(screen.getByRole('spinbutton')).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox', { name: /default/i }));
    expect(onChange).toHaveBeenLastCalledWith('height', 1);
  });
});

describe('humanise', () => {
  it('capitalises and replaces underscores', () => {
    expect(humanise('n_colors')).toBe('N colors');
    expect(humanise('dmc_code')).toBe('Dmc code');
    expect(humanise('width')).toBe('Width');
  });
});
