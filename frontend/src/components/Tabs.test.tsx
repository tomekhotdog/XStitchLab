import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Tabs } from './Tabs';

const items = [
  { id: 'brief', label: 'Brief', content: <p>brief body</p> },
  { id: 'recipe', label: 'Recipe', content: <p>recipe body</p> },
] as const;

describe('Tabs', () => {
  it('renders a tablist, marks the active tab, and shows only its panel', () => {
    render(<Tabs items={[...items]} active="recipe" onChange={() => {}} label="Editor panels" />);
    expect(screen.getByRole('tablist', { name: 'Editor panels' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Recipe' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Brief' })).toHaveAttribute('aria-selected', 'false');
    expect(screen.getByRole('tabpanel')).toHaveTextContent('recipe body');
    expect(screen.getByText('brief body')).not.toBeVisible();
  });

  it('click and arrow keys change the tab (wrapping), moving focus', () => {
    const onChange = vi.fn();
    render(<Tabs items={[...items]} active="brief" onChange={onChange} label="Editor panels" />);
    fireEvent.click(screen.getByRole('tab', { name: 'Recipe' }));
    expect(onChange).toHaveBeenCalledWith('recipe');
    const brief = screen.getByRole('tab', { name: 'Brief' });
    fireEvent.keyDown(brief, { key: 'ArrowRight' });
    expect(onChange).toHaveBeenLastCalledWith('recipe');
    expect(screen.getByRole('tab', { name: 'Recipe' })).toHaveFocus();
    fireEvent.keyDown(brief, { key: 'ArrowLeft' });
    expect(onChange).toHaveBeenLastCalledWith('recipe'); // wraps from first to last
    fireEvent.keyDown(brief, { key: 'Home' });
    expect(onChange).toHaveBeenLastCalledWith('brief');
  });
});
