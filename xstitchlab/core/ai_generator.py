"""AI image generation using OpenAI DALL-E for cross-stitch patterns."""

import os
from pathlib import Path
from typing import Optional
import base64
import httpx
from PIL import Image
import io


class AIGeneratorError(Exception):
    """Raised when AI generation fails."""
    pass


class AIGenerator:
    """Generate images using OpenAI DALL-E API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        output_dir: Optional[Path | str] = None,
        model: str = "dall-e-3"
    ):
        """Initialize the AI generator.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            output_dir: Directory to save generated images
            model: DALL-E model to use ("dall-e-3" or "dall-e-2")
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise AIGeneratorError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "generated"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = model

        # Default style modifiers for cross-stitch friendly output
        self.style_suffix = (
            "Simple, flat design with clear outlines and solid colors. "
            "Minimal gradients. Suitable for pixel art conversion. "
            "Clean, cartoonish style with bold shapes."
        )

    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        add_style_suffix: bool = True,
        save_as: Optional[str] = None
    ) -> Path:
        """Generate an image from a text prompt.

        Args:
            prompt: Description of the image to generate
            size: Image size ("1024x1024", "1792x1024", "1024x1792")
            quality: Quality level ("standard" or "hd")
            add_style_suffix: Whether to add cross-stitch style modifiers
            save_as: Custom filename (without extension)

        Returns:
            Path to the generated image file
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise AIGeneratorError(
                "OpenAI package not installed. Install with: uv add openai"
            )

        # Enhance prompt for cross-stitch friendly output
        full_prompt = prompt
        if add_style_suffix:
            full_prompt = f"{prompt}. {self.style_suffix}"

        client = OpenAI(api_key=self.api_key)

        try:
            response = client.images.generate(
                model=self.model,
                prompt=full_prompt,
                size=size,
                quality=quality,
                response_format="url",
                n=1
            )

            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], "revised_prompt", None)

            # Download the image
            image_response = httpx.get(image_url, follow_redirects=True)
            image_response.raise_for_status()

            # Save to file
            filename = save_as or self._generate_filename(prompt)
            output_path = self.output_dir / f"{filename}.png"

            img = Image.open(io.BytesIO(image_response.content))
            img.save(output_path, "PNG")

            # Save metadata
            meta_path = self.output_dir / f"{filename}_meta.txt"
            with open(meta_path, "w") as f:
                f.write(f"Original prompt: {prompt}\n")
                f.write(f"Full prompt: {full_prompt}\n")
                if revised_prompt:
                    f.write(f"Revised prompt: {revised_prompt}\n")
                f.write(f"Model: {self.model}\n")
                f.write(f"Size: {size}\n")
                f.write(f"Quality: {quality}\n")

            return output_path

        except Exception as e:
            raise AIGeneratorError(f"Image generation failed: {e}")

    def generate_batch(
        self,
        prompts: list[str],
        **kwargs
    ) -> list[Path]:
        """Generate multiple images from prompts.

        Args:
            prompts: List of prompts to generate
            **kwargs: Additional arguments passed to generate()

        Returns:
            List of paths to generated images
        """
        paths = []
        for i, prompt in enumerate(prompts):
            save_as = f"batch_{i:03d}"
            path = self.generate(prompt, save_as=save_as, **kwargs)
            paths.append(path)
        return paths

    def _generate_filename(self, prompt: str) -> str:
        """Generate a filename from the prompt."""
        import re
        import time

        # Clean prompt for filename
        clean = re.sub(r"[^\w\s-]", "", prompt.lower())
        clean = re.sub(r"\s+", "_", clean)[:30]

        timestamp = int(time.time())
        return f"{clean}_{timestamp}"


def generate_for_pattern(
    prompt: str,
    style: str = "simple",
    api_key: Optional[str] = None
) -> Path:
    """Quick function to generate an image optimized for cross-stitch.

    Args:
        prompt: Description of the image
        style: Style preset ("simple", "pixel_art", "detailed")
        api_key: Optional OpenAI API key

    Returns:
        Path to generated image
    """
    from ..prompts.templates import get_template

    generator = AIGenerator(api_key=api_key)

    # Get enhanced prompt from template
    enhanced_prompt = get_template(style, prompt)

    return generator.generate(
        enhanced_prompt,
        size="1024x1024",
        quality="standard",
        add_style_suffix=False  # Template already includes style
    )


def check_api_key() -> bool:
    """Check if OpenAI API key is configured.

    Returns:
        True if API key is available
    """
    return bool(os.environ.get("OPENAI_API_KEY"))
