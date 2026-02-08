"""Prompt templates optimized for cross-stitch-friendly AI image generation."""


# Base style modifiers that work well for cross-stitch patterns
BASE_STYLE = (
    "Simple, flat illustration with clear outlines and solid colors. "
    "Minimal gradients, suitable for pixel art. "
    "Clean shapes, limited color palette."
)

# Style-specific templates
TEMPLATES = {
    "simple": {
        "prefix": "",
        "suffix": (
            "Simple, flat design with bold outlines. "
            "Solid colors, no gradients. "
            "Clean cartoon style, minimal details."
        )
    },

    "pixel_art": {
        "prefix": "Pixel art style ",
        "suffix": (
            "Retro pixel art aesthetic. "
            "Clear pixel grid, limited color palette. "
            "8-bit or 16-bit game art style."
        )
    },

    "christmas": {
        "prefix": "Christmas themed ",
        "suffix": (
            "Festive holiday design. "
            "Traditional Christmas colors (red, green, gold, white). "
            "Simple, cheerful illustration style. "
            "Suitable for cross-stitch pattern."
        )
    },

    "nature": {
        "prefix": "Nature illustration of ",
        "suffix": (
            "Simple botanical or wildlife illustration. "
            "Flat design with clear shapes. "
            "Earthy, natural color palette. "
            "Clean outlines, minimal detail."
        )
    },

    "pets": {
        "prefix": "Cute illustration of ",
        "suffix": (
            "Adorable, kawaii-style pet portrait. "
            "Simple shapes, big expressive eyes. "
            "Solid colors, clean outlines. "
            "Cartoon style suitable for crafts."
        )
    },

    "floral": {
        "prefix": "Floral design featuring ",
        "suffix": (
            "Simple flower illustration. "
            "Folk art or Scandinavian style. "
            "Bold colors, flat design. "
            "Symmetrical or repeating pattern elements."
        )
    },

    "geometric": {
        "prefix": "Geometric pattern with ",
        "suffix": (
            "Abstract geometric design. "
            "Clean lines, solid shapes. "
            "Limited color palette. "
            "Modern, minimalist style."
        )
    },

    "vintage": {
        "prefix": "Vintage style ",
        "suffix": (
            "Retro, nostalgic illustration. "
            "Muted color palette. "
            "Simple, classic design. "
            "Old-fashioned charm, cross-stitch sampler style."
        )
    },

    "kawaii": {
        "prefix": "Kawaii style ",
        "suffix": (
            "Cute Japanese kawaii aesthetic. "
            "Pastel colors, simple shapes. "
            "Big eyes, happy expressions. "
            "Chibi proportions, minimal details."
        )
    },

    "monochrome": {
        "prefix": "",
        "suffix": (
            "Monochromatic design. "
            "Single color with white background. "
            "Silhouette or line art style. "
            "High contrast, clear shapes."
        )
    },

    "sampler": {
        "prefix": "Traditional cross-stitch sampler design with ",
        "suffix": (
            "Classic sampler style with borders. "
            "Traditional motifs and alphabets. "
            "Folk art inspired, symmetrical design. "
            "Heritage craft aesthetic."
        )
    },

    "modern": {
        "prefix": "Modern minimalist ",
        "suffix": (
            "Contemporary, clean design. "
            "Minimal detail, bold shapes. "
            "Limited neutral color palette. "
            "Scandinavian design influence."
        )
    },
}


def get_template(style: str, prompt: str) -> str:
    """Get enhanced prompt using a style template.

    Args:
        style: Style name (e.g., "simple", "christmas", "pixel_art")
        prompt: User's base prompt

    Returns:
        Enhanced prompt with style modifiers
    """
    template = TEMPLATES.get(style.lower(), TEMPLATES["simple"])

    enhanced = f"{template['prefix']}{prompt}. {template['suffix']}"

    return enhanced


def list_styles() -> list[str]:
    """Get list of available style names."""
    return list(TEMPLATES.keys())


def get_style_description(style: str) -> str:
    """Get description of a style template.

    Args:
        style: Style name

    Returns:
        Description of the style
    """
    template = TEMPLATES.get(style.lower())
    if template:
        return template["suffix"]
    return "Unknown style"


# Seasonal and themed prompt suggestions
PROMPT_SUGGESTIONS = {
    "christmas": [
        "cute robin sitting on a holly branch",
        "cozy Christmas tree with ornaments",
        "Santa Claus face",
        "reindeer with red nose",
        "snowman with top hat and scarf",
        "Christmas stocking filled with gifts",
        "gingerbread house",
        "winter village scene",
        "candy cane and bow",
        "Christmas wreath with ribbon",
    ],

    "nature": [
        "butterfly on a flower",
        "oak tree with autumn leaves",
        "mountain landscape with pine trees",
        "sunflower in bloom",
        "mushroom in forest",
        "bird on a branch",
        "beach with palm tree",
        "cactus in desert",
        "waterfall scene",
        "moon and stars night sky",
    ],

    "pets": [
        "sleeping cat curled up",
        "happy golden retriever face",
        "playful kitten with yarn",
        "bunny with floppy ears",
        "parrot on a perch",
        "hamster eating seeds",
        "fish in a bowl",
        "puppy with a ball",
        "cat sitting in a window",
        "dog wearing a bow tie",
    ],

    "floral": [
        "rose in full bloom",
        "bouquet of wildflowers",
        "sunflower field",
        "cherry blossom branch",
        "lavender bunch",
        "tulips in a row",
        "daisy chain",
        "poppy flowers",
        "lotus flower",
        "wreath of mixed flowers",
    ],

    "kawaii": [
        "kawaii sushi roll with face",
        "cute boba tea with smile",
        "happy little cloud",
        "adorable ice cream cone",
        "smiling slice of pizza",
        "cute cactus in pot",
        "happy rainbow",
        "kawaii panda eating bamboo",
        "cute avocado",
        "smiling donut",
    ],
}


def get_suggestions(theme: str) -> list[str]:
    """Get prompt suggestions for a theme.

    Args:
        theme: Theme name

    Returns:
        List of prompt suggestions
    """
    return PROMPT_SUGGESTIONS.get(theme.lower(), [])


def list_themes() -> list[str]:
    """Get list of themes with suggestions."""
    return list(PROMPT_SUGGESTIONS.keys())
