import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { OpSchema } from '@/api/types';
import { OpCard } from './OpCard';

const schema: OpSchema = {
  name: 'quantize_to_dmc_palette',
  kind: 'pattern',
  group: 'Colour',
  title: 'Quantize to a fixed DMC palette with perceptual matching',
  description: 'Maps every cell to its nearest DMC thread.',
  schema: { type: 'object', properties: {} },
};

describe('OpCard', () => {
  // The panel is narrow; the user must be able to read which step this is, so the title is
  // rendered whole (CSS wraps it) rather than cut to "1 Q…" by the header's badges.
  it('renders the full op title, with badges outside the title element', () => {
    render(<OpCard index={0} call={{ op: schema.name, params: {} }} schema={schema} count={1} />);
    const title = screen.getByText(schema.title, { exact: false });
    expect(title).toHaveClass('op-title');
    expect(title.textContent).toContain(schema.title);
    expect(title).not.toHaveTextContent('Colour');
    expect(screen.getByText('Colour')).toHaveClass('badge');
    expect(screen.getByText('Colour').parentElement).toHaveClass('op-badges');
  });
});
