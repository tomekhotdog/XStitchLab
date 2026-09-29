import { beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { makePattern } from '@/test/tools';
import { useEditorStore } from '@/store/editorStore';
import { EXPORTS, ExportMenu } from './ExportMenu';

beforeEach(() => {
  useEditorStore.getState().reset();
  useEditorStore.setState({ slug: 'riga' });
});

const open = () => fireEvent.click(screen.getByTestId('export'));

describe('ExportMenu', () => {
  it('renders one entry per export kind with links to the export route', () => {
    useEditorStore.getState().setPattern(makePattern(2, 2));
    render(<ExportMenu />);
    expect(screen.queryByRole('menu')).toBeNull();
    open();
    const items = screen.getAllByRole('menuitem');
    expect(items).toHaveLength(EXPORTS.length);
    expect(items.map((i) => i.textContent)).toEqual(EXPORTS.map((e) => e.label));
    for (const item of items) {
      expect(item).toHaveAttribute('target', '_blank');
      expect(item).toHaveAttribute('rel', 'noopener');
      expect(item.getAttribute('href')).toMatch(/^\/api\/designs\/riga\/export\//);
    }
    expect(screen.getByText('Files are also written into the design folder')).toBeInTheDocument();
  });

  it('sheet entries carry the A4 and A5 layouts', () => {
    useEditorStore.getState().setPattern(makePattern(2, 2));
    render(<ExportMenu />);
    open();
    expect(screen.getByRole('menuitem', { name: 'Pattern sheet A4' })).toHaveAttribute('href', '/api/designs/riga/export/sheet?layout=a4');
    expect(screen.getByRole('menuitem', { name: 'Pattern sheet A5' })).toHaveAttribute('href', '/api/designs/riga/export/sheet?layout=a5');
    expect(screen.getByRole('menuitem', { name: 'JSON' })).toHaveAttribute('href', '/api/designs/riga/export/json');
  });

  it('entries are disabled without a pattern', () => {
    render(<ExportMenu />);
    open();
    for (const item of screen.getAllByRole('menuitem')) {
      expect(item).toHaveAttribute('aria-disabled', 'true');
      expect(item).not.toHaveAttribute('href');
    }
    expect(screen.getByText(/no pattern to export/i)).toBeInTheDocument();
  });

  it('closes on Escape and toggles from the button', () => {
    render(<ExportMenu />);
    open();
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).toBeNull();
    open();
    expect(screen.getByTestId('export')).toHaveAttribute('aria-expanded', 'true');
    open();
    expect(screen.queryByRole('menu')).toBeNull();
  });
});
