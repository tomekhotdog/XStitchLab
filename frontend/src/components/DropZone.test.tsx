import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { DropZone, MAX_INPUT_BYTES } from './DropZone';

const drop = (el: HTMLElement, file: File) => fireEvent.drop(el, { dataTransfer: { files: [file], types: ['Files'] } });

describe('DropZone', () => {
  it('drop of a PNG calls onFile', () => {
    const onFile = vi.fn();
    render(<DropZone onFile={onFile} />);
    const file = new File(['x'], 'in.png', { type: 'image/png' });
    drop(screen.getByTestId('dropzone'), file);
    expect(onFile).toHaveBeenCalledWith(file);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('drop of a text file shows an error and does not call onFile', () => {
    const onFile = vi.fn();
    render(<DropZone onFile={onFile} />);
    drop(screen.getByTestId('dropzone'), new File(['hi'], 'notes.txt', { type: 'text/plain' }));
    expect(onFile).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/PNG, JPEG or WebP/);
  });

  it('rejects a file over the size limit', () => {
    const onFile = vi.fn();
    render(<DropZone onFile={onFile} />);
    const big = new File([''], 'big.png', { type: 'image/png' });
    Object.defineProperty(big, 'size', { value: MAX_INPUT_BYTES + 1 });
    drop(screen.getByTestId('dropzone'), big);
    expect(onFile).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/20 MB/);
  });

  it('clicking opens the hidden file input, and choosing a file calls onFile', () => {
    const onFile = vi.fn();
    render(<DropZone onFile={onFile} />);
    const input = screen.getByTestId<HTMLInputElement>('input-file');
    const click = vi.spyOn(input, 'click');
    fireEvent.click(screen.getByTestId('dropzone'));
    expect(click).toHaveBeenCalled();
    const file = new File(['x'], 'in.jpg', { type: 'image/jpeg' });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onFile).toHaveBeenCalledWith(file);
  });

  it('marks itself active while a drag is over it', () => {
    render(<DropZone onFile={() => {}} />);
    const zone = screen.getByTestId('dropzone');
    fireEvent.dragOver(zone, { dataTransfer: { types: ['Files'] } });
    expect(zone).toHaveClass('active');
    fireEvent.dragLeave(zone);
    expect(zone).not.toHaveClass('active');
  });
});
