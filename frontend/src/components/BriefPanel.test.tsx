import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import * as client from '@/api/client';
import { useEditorStore } from '@/store/editorStore';
import { useToast } from '@/store/toast';
import { makePattern } from '@/test/tools';
import { BriefPanel } from './BriefPanel';

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  return { ...actual, promptTemplate: vi.fn() };
});

const TEMPLATE = 'Create a pixel art illustration of [SUBJECT].';
const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(client.promptTemplate).mockResolvedValue(TEMPLATE);
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
  useToast.getState().clear();
  useEditorStore.getState().reset();
  useEditorStore.setState({
    slug: 'riga',
    prompt: 'Draw the Three Brothers',
    historyText: 'Built in 1490',
    savePrompt: vi.fn().mockResolvedValue(true),
    saveHistory: vi.fn().mockResolvedValue(true),
    uploadInput: vi.fn().mockResolvedValue(true),
    setPanel: vi.fn(),
  });
});

const brief = () => screen.getByTestId<HTMLTextAreaElement>('brief-text');

describe('BriefPanel', () => {
  it('renders the prompt and history from the store', () => {
    render(<BriefPanel />);
    expect(screen.getByRole('heading', { name: 'Brief' })).toBeInTheDocument();
    expect(brief()).toHaveValue('Draw the Three Brothers');
    expect(screen.getByLabelText('History')).toHaveValue('Built in 1490');
    expect(screen.getByRole('button', { name: 'Save brief' })).toBeDisabled();
  });

  it('Insert template fills an empty textarea with the fetched template', async () => {
    useEditorStore.setState({ prompt: '' });
    render(<BriefPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'Insert template' }));
    await waitFor(() => expect(brief()).toHaveValue(TEMPLATE));
    expect(client.promptTemplate).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(screen.getByRole('button', { name: 'Save brief' })).toBeEnabled();
  });

  it('Insert template asks before replacing a non-empty brief, and replaces on confirm', async () => {
    render(<BriefPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'Insert template' }));
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Replace the current brief with the template?');
    expect(brief()).toHaveValue('Draw the Three Brothers');
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(brief()).toHaveValue('Draw the Three Brothers');

    fireEvent.click(screen.getByRole('button', { name: 'Insert template' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Replace' }));
    await waitFor(() => expect(brief()).toHaveValue(TEMPLATE));
    expect(client.promptTemplate).toHaveBeenCalledTimes(1); // fetched once, reused
  });

  it('Save brief calls the store action with the textarea value', async () => {
    render(<BriefPanel />);
    fireEvent.change(brief(), { target: { value: 'A new brief' } });
    const save = screen.getByRole('button', { name: 'Save brief' });
    expect(save).toBeEnabled();
    fireEvent.click(save);
    await waitFor(() => expect(useEditorStore.getState().savePrompt).toHaveBeenCalledWith('A new brief'));
  });

  it('Save history calls the store action with the textarea value', async () => {
    render(<BriefPanel />);
    const history = screen.getByLabelText('History');
    expect(screen.getByRole('button', { name: 'Save history' })).toBeDisabled();
    fireEvent.change(history, { target: { value: 'Rebuilt in 1600' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save history' }));
    await waitFor(() => expect(useEditorStore.getState().saveHistory).toHaveBeenCalledWith('Rebuilt in 1600'));
  });

  it('Copy writes the brief to the clipboard and toasts', async () => {
    render(<BriefPanel />);
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
    expect(writeText).toHaveBeenCalledWith('Draw the Three Brothers');
    await waitFor(() => expect(useToast.getState().message).toBe('Brief copied'));
  });

  it('shows the drop zone without an input, and the preview with a Replace zone once there is one', () => {
    const { rerender } = render(<BriefPanel />);
    expect(screen.getByRole('button', { name: 'Choose an input image' })).toBeInTheDocument();
    expect(screen.queryByRole('img')).toBeNull();
    act(() => useEditorStore.setState({ hasInput: true, inputVersion: 3 }));
    rerender(<BriefPanel />);
    expect(screen.getByRole('img', { name: 'Input image' })).toHaveAttribute('src', '/api/designs/riga/input.png?v=3');
    expect(screen.getByRole('button', { name: 'Replace the input image' })).toBeInTheDocument();
  });

  it('a dropped file goes to uploadInput; without a pattern the hint points at Recipe', async () => {
    render(<BriefPanel />);
    const file = new File(['x'], 'in.png', { type: 'image/png' });
    fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files: [file], types: ['Files'] } });
    await waitFor(() => expect(useEditorStore.getState().uploadInput).toHaveBeenCalledWith(file));
    act(() => useEditorStore.setState({ hasInput: true }));
    expect(screen.getByText('Now switch to Recipe and run')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Go to Recipe' }));
    expect(useEditorStore.getState().setPanel).toHaveBeenCalledWith('recipe');
  });

  it('no Recipe hint when a pattern already exists', () => {
    useEditorStore.setState({ hasInput: true, pattern: makePattern(2, 2) });
    render(<BriefPanel />);
    expect(screen.queryByText('Now switch to Recipe and run')).toBeNull();
  });

  it('re-syncs the textarea when the store prompt changes (e.g. a new design loads)', () => {
    render(<BriefPanel />);
    act(() => useEditorStore.setState({ prompt: 'Other design' }));
    expect(brief()).toHaveValue('Other design');
  });
});
