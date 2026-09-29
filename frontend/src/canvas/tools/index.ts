/** The editing tools by store `tool` name. */

import type { Tool } from '@/store/editorStore';
import { backstitch } from './backstitch';
import { eyedropper } from './eyedropper';
import { fill } from './fill';
import { paint } from './paint';
import { select } from './select';
import type { CanvasTool } from './types';

export const tools: Record<Tool, CanvasTool> = { paint, fill, select, eyedropper, backstitch };

export type { CanvasTool, ToolContext, ToolEvent } from './types';
