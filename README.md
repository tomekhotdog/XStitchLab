# XStitchLab

A Python toolchain for end-to-end cross-stitch pattern generation.

**Image idea → AI generation → Pixelation → Color mapping → Pattern output → Visualization → Thread estimation**

## Features

- **Image Input**: Accept local images (PNG, JPG) or generate with AI (DALL-E 3)
- **Pixelation**: Resize to stitch grid with color quantization
- **DMC Color Mapping**: Map to real thread colors using perceptual color matching (CIELAB)
- **Pattern Generation**: Symbol grids, color legends, stitch counts
- **Thread Estimation**: Calculate thread requirements per color
- **Multiple Outputs**: PNG previews, printable PDF patterns, JSON data

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd XStitchLab

# Install with uv
uv sync

# Or with pip
pip install -e .
```

## Quick Start

### CLI Usage

```bash
# Convert an image to a cross-stitch pattern
uv run xstitch convert image.png --size 40 --colors 8

# Get information about an image
uv run xstitch info image.png

# Generate pattern with AI
uv run xstitch generate "cute robin on holly branch" --style christmas

# Estimate thread requirements
uv run xstitch estimate pattern.json --fabric 14
```

## Pipeline Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   INPUT     │ →  │  PIXELATE   │ →  │  MAP COLORS │ →  │   OUTPUT    │
│             │    │             │    │             │    │             │
│ Upload or   │    │ Grid size   │    │ DMC palette │    │ PDF + PNG   │
│ Generate    │    │ + quantize  │    │ + controls  │    │ + shopping  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Project Structure

```
xstitchlab/
├── cli.py                    # CLI entry point
├── core/
│   ├── image_input.py        # Load/validate images
│   ├── ai_generator.py       # OpenAI DALL-E integration
│   ├── pixelator.py          # Resize + quantize
│   ├── color_mapper.py       # RGB → DMC mapping
│   ├── pattern.py            # Pattern data structure
│   ├── thread_calc.py        # Thread estimation
│   └── visualizer.py         # Render previews
├── data/
│   └── dmc_colors.json       # DMC thread database
├── export/
│   ├── pdf_exporter.py       # PDF pattern generation
│   └── png_exporter.py       # Image export
└── prompts/
    └── templates.py          # DALL-E prompt templates
```

## Configuration

### OpenAI API Key (Optional)

An API key is **only required for AI image generation**. All other features work without it:

| Feature | Needs API Key? |
|---------|---------------|
| Convert existing images | No |
| View DMC palette | No |
| Export PDF/PNG | No |
| Thread estimation | No |
| Generate images from text | Yes |

To use AI generation, either:
- Set the environment variable:
  ```bash
  export OPENAI_API_KEY=sk-your-key-here
  ```

### Fabric Sizes

The tool supports common Aida fabric counts:
- 14-count (standard, recommended for beginners)
- 16-count (finer detail)
- 18-count (finest detail)

## Running Tests

```bash
uv run pytest tests/
```

## License

MIT
