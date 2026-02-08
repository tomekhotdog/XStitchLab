"""Streamlit GUI for XStitchLab cross-stitch pattern generation."""

import streamlit as st
from PIL import Image
import io
from pathlib import Path
import tempfile

from xstitchlab.core.image_input import load_image
from xstitchlab.core.pixelator import (
    pixelate,
    pixelate_predesigned,
    snap_to_dominant_colors,
    quantize_then_resize,
    get_color_indices,
    extract_unique_colors
)
from xstitchlab.core.color_mapper import ColorMapper
from xstitchlab.core.pattern import Pattern, PatternMetadata, ColorLegendEntry
from xstitchlab.core.adjuster import (
    AdjustmentSettings,
    adjust_pattern,
    indices_to_image
)
from xstitchlab.core.backstitch import (
    BackstitchSettings,
    generate_backstitch,
    render_backstitch,
    backstitch_instructions
)
import numpy as np

# Standard symbols for pattern display
SYMBOLS = [
    "●", "■", "▲", "◆", "★", "♦", "♣", "♠", "♥", "○",
    "□", "△", "◇", "☆", "◐", "◑", "◒", "◓", "⬟", "⬡",
    "⊕", "⊗", "⊙", "⊚", "⊛", "⊜", "⊝", "⧫", "⬢", "⬣",
    "▼", "◀", "▶", "▷", "◁", "⬤", "⬥", "⬦", "⬧", "⬨",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"
]
from xstitchlab.core.visualizer import (
    render_color_preview,
    render_symbol_grid,
    render_thread_realistic,
    render_legend,
    render_comparison
)
from xstitchlab.core.thread_calc import ThreadCalculator
from xstitchlab.export.png_exporter import PNGExporter
from xstitchlab.export.pdf_exporter import PDFExporter
from xstitchlab.prompts.templates import list_styles, get_suggestions, list_themes


def upscale_for_display(img: Image.Image, min_width: int = 300) -> Image.Image:
    """Upscale small images using NEAREST neighbor for pixel-perfect display.

    Streamlit uses smooth interpolation by default, which makes small
    pixelated images look blurry. This upscales them first.
    """
    if img.width < min_width:
        scale = min_width // img.width
        if scale > 1:
            new_size = (img.width * scale, img.height * scale)
            return img.resize(new_size, Image.Resampling.NEAREST)
    return img


# Page config
st.set_page_config(
    page_title="XStitchLab",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
    .pipeline-step {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .metric-card {
        background-color: white;
        border-radius: 5px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "original_image": None,
        "pattern": None,
        "processing_done": False,
        "pipeline_result": None,  # Full result from pipeline
        "image_type": None,  # "photo" or "predesigned"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def process_photo(
    img: Image.Image,
    title: str,
    grid_size: int,
    n_colors: int,
    use_dithering: bool,
    use_lab: bool,
    adjustment_settings: AdjustmentSettings | None = None,
    backstitch_settings: BackstitchSettings | None = None
) -> dict:
    """Photo pipeline: resize + quantize + adjust + map to DMC + backstitch.

    Returns dict with all results and pipeline stages for visualization.
    """
    result = {
        "stages": {},  # Each stage's output image
        "pipeline_info": [],  # Detailed info for each step
    }

    # Stage 1: Pixelate (LANCZOS resize + K-means quantization)
    pixelated, palette = pixelate(
        img,
        grid_width=grid_size,
        n_colors=n_colors,
        use_dithering=use_dithering
    )
    result["stages"]["pixelated"] = pixelated
    result["pipeline_info"].append({
        "name": "1. Pixelate",
        "description": "Resize with LANCZOS + K-means color quantization",
        "details": {
            "input_size": f"{img.width}×{img.height}",
            "output_size": f"{pixelated.width}×{pixelated.height}",
            "resize_method": "LANCZOS (smooth anti-aliasing)",
            "quantization": "K-means clustering",
            "target_colors": n_colors,
            "dithering": "Floyd-Steinberg" if use_dithering else "none",
        }
    })

    # Get color indices
    color_indices = get_color_indices(pixelated, palette)

    # Stage 2: XStitchLabs Adjustment (optional)
    if adjustment_settings is not None:
        color_indices, palette, adj_stats = adjust_pattern(
            color_indices, palette, adjustment_settings
        )
        adjusted = indices_to_image(color_indices, palette)
        result["stages"]["adjusted"] = adjusted
        result["adjustment_stats"] = adj_stats
        result["pipeline_info"].append({
            "name": "2. Adjust",
            "description": "XStitchLabs cleanup for stitchability",
            "details": {
                "pixels_changed": adj_stats["pixels_changed"],
                "operations": adj_stats["operations_applied"],
                "colors_after": len(palette),
            }
        })
    else:
        result["stages"]["adjusted"] = None
        result["adjustment_stats"] = None
        result["pipeline_info"].append({
            "name": "2. Adjust",
            "description": "Skipped",
            "details": {"skipped": True}
        })

    # Stage 3: Map to DMC
    mapper = ColorMapper(use_lab=use_lab)
    dmc_colors = mapper.map_palette(palette)

    color_mappings = []
    for orig_rgb, dmc in zip(palette, dmc_colors):
        color_mappings.append({
            "rgb": f"({orig_rgb[0]}, {orig_rgb[1]}, {orig_rgb[2]})",
            "dmc_code": dmc.code,
            "dmc_name": dmc.name,
        })

    result["pipeline_info"].append({
        "name": "3. Map to DMC",
        "description": f"Match colors to DMC threads ({'CIEDE2000' if use_lab else 'RGB'})",
        "details": {
            "method": "CIEDE2000 (perceptual)" if use_lab else "RGB Euclidean",
            "mappings": color_mappings,
        }
    })

    # Create pattern
    legend = []
    for i, dmc in enumerate(dmc_colors):
        symbol = SYMBOLS[i] if i < len(SYMBOLS) else str(i)
        legend.append(ColorLegendEntry(dmc_color=dmc, symbol=symbol, stitch_count=0))

    pattern = Pattern(
        grid=color_indices.tolist(),
        legend=legend,
        metadata=PatternMetadata(title=title)
    )
    pattern.count_stitches()

    result["pattern"] = pattern
    result["palette"] = palette

    # Stage 4: Backstitch (optional)
    if backstitch_settings is not None and backstitch_settings.enabled:
        segments, backstitch_info = generate_backstitch(
            color_indices, palette, backstitch_settings
        )
        result["backstitch_segments"] = segments
        result["backstitch_info"] = backstitch_info
        result["backstitch_settings"] = backstitch_settings
        result["pipeline_info"].append({
            "name": "4. Backstitch",
            "description": "Generate outline stitches along boundaries",
            "details": {
                "segment_count": backstitch_info["segment_count"],
                "total_length": f"{backstitch_info['total_length_stitches']} stitch units",
                "horizontal_segments": backstitch_info["horizontal_segments"],
                "vertical_segments": backstitch_info["vertical_segments"],
                "min_contrast": backstitch_settings.min_contrast,
                "color": backstitch_settings.color,
            }
        })
    else:
        result["backstitch_segments"] = []
        result["backstitch_info"] = None
        result["backstitch_settings"] = None
        result["pipeline_info"].append({
            "name": "4. Backstitch",
            "description": "Skipped",
            "details": {"skipped": True}
        })

    return result


def process_predesigned(
    img: Image.Image,
    title: str,
    use_lab: bool,
    n_colors: int = 12,
    grid_size: int | None = None,
    kmeans_init: str = "k-means++",
    adjustment_settings: AdjustmentSettings | None = None,
    backstitch_settings: BackstitchSettings | None = None
) -> dict:
    """Pre-designed pipeline: quantize colors (optionally resize) + adjust + map to DMC + backstitch.

    If grid_size is provided: K-means at full resolution, then NEAREST resize
    If grid_size is None: K-means at full resolution, no resize

    Returns dict with all results and pipeline stages for visualization.
    """
    from sklearn.cluster import KMeans
    from xstitchlab.core.pixelator import resize_to_grid

    result = {
        "stages": {},
        "pipeline_info": [],
    }

    # Stage 0: Analyze input
    _, all_colors = extract_unique_colors(img)
    result["pipeline_info"].append({
        "name": "0. Analyze Input",
        "description": f"Input image analysis",
        "details": {
            "input_dimensions": f"{img.width}×{img.height} pixels",
            "unique_colors_found": f"{len(all_colors):,}",
        }
    })

    # Stage 1: K-means quantization at FULL resolution
    arr = np.array(img)
    h, w = arr.shape[:2]
    pixels = arr.reshape(-1, 3).astype(np.float32)

    kmeans = KMeans(
        n_clusters=n_colors,
        random_state=42,
        n_init=10,
        init=kmeans_init
    )
    labels = kmeans.fit_predict(pixels)
    palette = kmeans.cluster_centers_.astype(np.uint8)

    # Full-res quantized image
    clean_pixels = palette[labels]
    clean_arr = clean_pixels.reshape(h, w, 3)
    quantized_full = Image.fromarray(clean_arr)
    result["stages"]["quantized_full"] = quantized_full

    result["pipeline_info"].append({
        "name": "1. Quantize (Full Res)",
        "description": f"K-means clustering at {w}×{h}",
        "details": {
            "colors_reduced": f"{len(all_colors):,} → {n_colors}",
            "init_method": kmeans_init,
            "dimensions": f"{w}×{h} (unchanged)",
        }
    })

    # Stage 2: Resize (optional)
    if grid_size is not None:
        from xstitchlab.core.pixelator import boundary_preserving_resize

        sample_rate = w / grid_size

        resized = boundary_preserving_resize(quantized_full, grid_size, mode="majority")
        result["stages"]["resized"] = resized

        result["pipeline_info"].append({
            "name": "2. Resize",
            "description": f"Downsample to {resized.width}×{resized.height}",
            "details": {
                "method": "majority voting",
                "reduction": f"{w}→{resized.width} ({sample_rate:.0f}×)",
                "output_size": f"{resized.width}×{resized.height} stitches",
            }
        })

        working_img = resized
    else:
        result["stages"]["resized"] = None
        result["pipeline_info"].append({
            "name": "2. Resize",
            "description": "Skipped (using full resolution)",
            "details": {
                "skipped": True,
                "output_size": f"{w}×{h} stitches",
            }
        })
        working_img = quantized_full

    result["stages"]["quantized"] = working_img  # For compatibility

    # Get color indices
    color_indices = get_color_indices(working_img, palette)

    # Stage 2: XStitchLabs Adjustment (optional)
    if adjustment_settings is not None:
        color_indices, palette, adj_stats = adjust_pattern(
            color_indices, palette, adjustment_settings
        )
        adjusted = indices_to_image(color_indices, palette)
        result["stages"]["adjusted"] = adjusted
        result["adjustment_stats"] = adj_stats
        result["pipeline_info"].append({
            "name": "2. Adjust",
            "description": "XStitchLabs cleanup for stitchability",
            "details": {
                "pixels_changed": adj_stats["pixels_changed"],
                "operations": adj_stats["operations_applied"],
                "colors_after": len(palette),
            }
        })
    else:
        result["stages"]["adjusted"] = None
        result["adjustment_stats"] = None
        result["pipeline_info"].append({
            "name": "2. Adjust",
            "description": "Skipped",
            "details": {"skipped": True}
        })

    # Stage 3: Map to DMC
    mapper = ColorMapper(use_lab=use_lab)
    dmc_colors = mapper.map_palette(palette)

    color_mappings = []
    for orig_rgb, dmc in zip(palette, dmc_colors):
        color_mappings.append({
            "rgb": f"({orig_rgb[0]}, {orig_rgb[1]}, {orig_rgb[2]})",
            "dmc_code": dmc.code,
            "dmc_name": dmc.name,
        })

    result["pipeline_info"].append({
        "name": "3. Map to DMC",
        "description": f"Match colors to DMC threads ({'CIEDE2000' if use_lab else 'RGB'})",
        "details": {
            "method": "CIEDE2000 (perceptual)" if use_lab else "RGB Euclidean",
            "mappings": color_mappings,
        }
    })

    # Create pattern
    legend = []
    for i, dmc in enumerate(dmc_colors):
        symbol = SYMBOLS[i] if i < len(SYMBOLS) else str(i)
        legend.append(ColorLegendEntry(dmc_color=dmc, symbol=symbol, stitch_count=0))

    pattern = Pattern(
        grid=color_indices.tolist(),
        legend=legend,
        metadata=PatternMetadata(title=title)
    )
    pattern.count_stitches()

    result["pattern"] = pattern
    result["palette"] = palette

    # Stage 4: Backstitch (optional)
    if backstitch_settings is not None and backstitch_settings.enabled:
        segments, backstitch_info = generate_backstitch(
            color_indices, palette, backstitch_settings
        )
        result["backstitch_segments"] = segments
        result["backstitch_info"] = backstitch_info
        result["backstitch_settings"] = backstitch_settings
        result["pipeline_info"].append({
            "name": "4. Backstitch",
            "description": "Generate outline stitches along boundaries",
            "details": {
                "segment_count": backstitch_info["segment_count"],
                "total_length": f"{backstitch_info['total_length_stitches']} stitch units",
                "horizontal_segments": backstitch_info["horizontal_segments"],
                "vertical_segments": backstitch_info["vertical_segments"],
                "min_contrast": backstitch_settings.min_contrast,
                "color": backstitch_settings.color,
            }
        })
    else:
        result["backstitch_segments"] = []
        result["backstitch_info"] = None
        result["backstitch_settings"] = None
        result["pipeline_info"].append({
            "name": "4. Backstitch",
            "description": "Skipped",
            "details": {"skipped": True}
        })

    return result


def main():
    """Main Streamlit app."""
    init_session_state()

    # Header
    st.title("🧵 XStitchLab")
    st.markdown("*Transform images into cross-stitch patterns*")

    # Sidebar - Input & Settings
    with st.sidebar:
        st.header("📥 Input")

        input_method = st.radio(
            "Input Method",
            ["Upload Image", "AI Generate"],
            horizontal=True
        )

        if input_method == "Upload Image":
            uploaded_file = st.file_uploader(
                "Choose an image",
                type=["png", "jpg", "jpeg", "gif", "bmp", "webp"]
            )

            if uploaded_file:
                st.session_state.original_image = Image.open(uploaded_file).convert("RGB")
                st.image(st.session_state.original_image, caption="Original", use_container_width=True)

        else:
            st.markdown("### AI Generation")

            # Check for API key
            api_key = st.text_input("OpenAI API Key", type="password", help="Required for DALL-E")

            theme = st.selectbox("Theme", ["custom"] + list_themes())

            if theme != "custom":
                suggestions = get_suggestions(theme)
                prompt = st.selectbox("Suggestion", [""] + suggestions)
                if not prompt:
                    prompt = st.text_input("Or enter custom prompt")
            else:
                prompt = st.text_input("Enter prompt")

            style = st.selectbox("Style", list_styles())

            if st.button("🎨 Generate Image", disabled=not (api_key and prompt)):
                with st.spinner("Generating image with DALL-E..."):
                    try:
                        from xstitchlab.core.ai_generator import AIGenerator
                        from xstitchlab.prompts.templates import get_template

                        generator = AIGenerator(api_key=api_key)
                        enhanced_prompt = get_template(style, prompt)

                        with tempfile.TemporaryDirectory() as tmpdir:
                            generator.output_dir = Path(tmpdir)
                            img_path = generator.generate(enhanced_prompt, add_style_suffix=False)
                            st.session_state.original_image = Image.open(img_path).convert("RGB")

                        st.success("Image generated!")
                        st.image(st.session_state.original_image, caption="Generated", use_container_width=True)
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

        st.divider()

        # Pattern Settings
        st.header("⚙️ Settings")

        title = st.text_input("Pattern Title", "My Pattern")

        # Image Type Selection
        st.markdown("##### Image Type")
        image_type = st.radio(
            "Image Type",
            ["predesigned", "photo"],
            format_func=lambda x: "Pre-designed (AI-generated cross-stitch)" if x == "predesigned" else "Photo/Artwork",
            horizontal=True,
            label_visibility="collapsed",
            help="Pre-designed: for images already designed for cross-stitch. Photo: for regular photos/artwork."
        )

        st.markdown("---")

        # Mode-specific settings
        if image_type == "photo":
            st.markdown("##### Photo Pipeline")
            st.caption("For photos & artwork: resize + quantize colors")

            grid_size = st.slider("Grid Width (stitches)", 20, 150, 40)
            n_colors = st.slider("Number of Colors", 2, 20, 8)
            use_dithering = st.checkbox("Enable Dithering", value=False,
                help="Floyd-Steinberg dithering for smoother gradients (more complex to stitch)")

            # Not used in photo mode
            snap_colors = False

        else:  # predesigned
            st.markdown("##### Pre-designed Pipeline")

            if st.session_state.original_image:
                img = st.session_state.original_image
                st.caption(f"Input: {img.width}×{img.height} pixels")

            with st.expander("Quantization Settings", expanded=True):
                n_colors = st.slider("Number of Colors", 2, 25, 12,
                    help="K-means finds this many distinct color clusters")

                kmeans_init = st.selectbox(
                    "K-means Initialization",
                    ["k-means++", "random"],
                    help="k-means++: smarter init (default), random: may find different clusters"
                )

            with st.expander("Resize Settings", expanded=True):
                needs_resize = st.checkbox(
                    "Resize pattern",
                    value=True,
                    help="Resize to a smaller stitch count"
                )

                if needs_resize:
                    grid_size = st.slider("Grid Width", 20, 80, 50,
                        help="Pattern width in cells (background is unstitched)")

                    if st.session_state.original_image:
                        ratio = img.width / grid_size
                        st.caption(f"Grid: {grid_size}×{grid_size} cells ({ratio:.0f}× reduction)")
                else:
                    grid_size = None
                    if st.session_state.original_image:
                        st.warning(f"Pattern will be **{img.width}×{img.height}** stitches (very large!)")

            # Not used in predesigned mode
            snap_colors = True
            use_dithering = False

        st.markdown("---")

        use_lab = st.checkbox("Use CIELAB Colors", value=True,
            help="Better perceptual color matching (recommended)")

        fabric_count = st.selectbox("Fabric Count", [14, 16, 18, 11], index=0)

        st.divider()

        # XStitchLabs Adjustment
        st.header("✨ XStitchLabs Adjustment")

        enable_adjustment = st.checkbox(
            "Enable Adjustment",
            value=True,
            help="Post-processing to improve stitchability"
        )

        adjustment_settings = None
        if enable_adjustment:
            with st.expander("Adjustment Parameters", expanded=False):
                fill_holes = st.checkbox(
                    "Fill Internal Holes",
                    value=True,
                    help="Fill stray pixels inside solid regions"
                )

                snap_diagonals = st.checkbox(
                    "Snap Diagonals to Stairs",
                    value=True,
                    help="Convert diagonal lines to stair-step patterns"
                )

                connect_lines = st.checkbox(
                    "Connect Broken Lines",
                    value=True,
                    help="Bridge 1px gaps in boundary lines"
                )

                rectangularize = st.checkbox(
                    "Rectangularize",
                    value=False,
                    help="Prefer rectangular shapes - completes corners, fills L-gaps (good for architecture)"
                )

                remove_isolated = st.checkbox(
                    "Remove Isolated Pixels",
                    value=False,
                    help="Remove pixels with no same-color neighbors"
                )

                min_region_size = st.slider(
                    "Min Region Size",
                    min_value=1,
                    max_value=10,
                    value=1,
                    help="Absorb regions smaller than this (1 = disabled)"
                )

                smoothing_iterations = st.slider(
                    "Smoothing Iterations",
                    min_value=0,
                    max_value=3,
                    value=0,
                    help="Majority-vote smoothing passes"
                )

                straighten_edges = st.checkbox(
                    "Straighten Edges",
                    value=False,
                    help="Prefer horizontal/vertical edges"
                )

            adjustment_settings = AdjustmentSettings(
                fill_holes=fill_holes,
                snap_diagonals=snap_diagonals,
                connect_lines=connect_lines,
                rectangularize=rectangularize,
                remove_isolated=remove_isolated,
                min_region_size=min_region_size,
                smoothing_iterations=smoothing_iterations,
                straighten_edges=straighten_edges
            )

        st.divider()

        # Backstitch Settings
        st.header("🪡 Backstitch")

        enable_backstitch = st.checkbox(
            "Enable Backstitch",
            value=True,
            help="Add outline stitches along color boundaries for better definition"
        )

        backstitch_settings = None
        if enable_backstitch:
            with st.expander("Backstitch Parameters", expanded=True):
                backstitch_color_option = st.selectbox(
                    "Backstitch Color",
                    ["Black", "Dark Gray", "Custom"],
                    help="Color for backstitch outlines"
                )

                if backstitch_color_option == "Black":
                    backstitch_color = (0, 0, 0)
                elif backstitch_color_option == "Dark Gray":
                    backstitch_color = (50, 50, 50)
                else:
                    backstitch_color = st.color_picker("Custom Color", "#000000")
                    # Convert hex to RGB tuple
                    backstitch_color = tuple(int(backstitch_color[i:i+2], 16) for i in (1, 3, 5))

                min_contrast = st.slider(
                    "Minimum Contrast",
                    min_value=0,
                    max_value=150,
                    value=50,
                    help="Minimum color difference to add backstitch (0 = all boundaries, higher = only high-contrast edges)"
                )

                include_diagonals = st.checkbox(
                    "Include Diagonal Segments",
                    value=False,
                    help="Also backstitch along diagonal boundaries (more complex)"
                )

            backstitch_settings = BackstitchSettings(
                enabled=True,
                color=backstitch_color,
                min_contrast=min_contrast,
                include_diagonals=include_diagonals
            )

        st.divider()

        # Process button
        process_disabled = st.session_state.original_image is None
        if st.button("🔄 Generate Pattern", type="primary", disabled=process_disabled):
            with st.spinner("Processing..."):
                if image_type == "photo":
                    result = process_photo(
                        st.session_state.original_image,
                        title=title,
                        grid_size=grid_size,
                        n_colors=n_colors,
                        use_dithering=use_dithering,
                        use_lab=use_lab,
                        adjustment_settings=adjustment_settings,
                        backstitch_settings=backstitch_settings
                    )
                else:
                    result = process_predesigned(
                        st.session_state.original_image,
                        title=title,
                        use_lab=use_lab,
                        n_colors=n_colors,
                        grid_size=grid_size if needs_resize else None,
                        kmeans_init=kmeans_init,
                        adjustment_settings=adjustment_settings,
                        backstitch_settings=backstitch_settings
                    )

                st.session_state.pattern = result["pattern"]
                st.session_state.pipeline_result = result
                st.session_state.image_type = image_type
                st.session_state.processing_done = True

            st.success("Pattern created!")

    # Main content area
    if not st.session_state.processing_done:
        # Show pipeline visualization when no pattern yet
        st.markdown("### Pipeline Overview")
        st.caption(f"Mode: **{'Pre-designed' if image_type == 'predesigned' else 'Photo/Artwork'}**")

        if image_type == "predesigned":
            # Pre-designed pipeline
            cols = st.columns(7)

            with cols[0]:
                st.markdown("#### 1️⃣ Input")
                st.markdown("AI-generated cross-stitch image")
                if st.session_state.original_image:
                    st.image(st.session_state.original_image, use_container_width=True)
                else:
                    st.info("No image")

            with cols[1]:
                st.markdown("#### 2️⃣ Quantize")
                st.markdown("K-means at full resolution")
                st.info("Waiting...")

            with cols[2]:
                st.markdown("#### 3️⃣ Resize")
                st.markdown("Boundary-preserving downsample")
                st.info("Waiting...")

            with cols[3]:
                st.markdown("#### 4️⃣ Adjust")
                st.markdown("XStitchLabs cleanup")
                st.info("Waiting...")

            with cols[4]:
                st.markdown("#### 5️⃣ Map DMC")
                st.markdown("Match to threads")
                st.info("Waiting...")

            with cols[5]:
                st.markdown("#### 6️⃣ Backstitch")
                st.markdown("Boundary outlines")
                st.info("Waiting...")

            with cols[6]:
                st.markdown("#### 7️⃣ Output")
                st.markdown("Export pattern")
                st.info("Waiting...")

        else:
            # Photo pipeline
            cols = st.columns(6)

            with cols[0]:
                st.markdown("#### 1️⃣ Input")
                st.markdown("Photo or artwork")
                if st.session_state.original_image:
                    st.image(st.session_state.original_image, use_container_width=True)
                else:
                    st.info("No image")

            with cols[1]:
                st.markdown("#### 2️⃣ Pixelate")
                st.markdown("LANCZOS resize + K-means")
                st.info("Waiting...")

            with cols[2]:
                st.markdown("#### 3️⃣ Adjust")
                st.markdown("XStitchLabs cleanup")
                st.info("Waiting...")

            with cols[3]:
                st.markdown("#### 4️⃣ Map DMC")
                st.markdown("Match to threads")
                st.info("Waiting...")

            with cols[4]:
                st.markdown("#### 5️⃣ Backstitch")
                st.markdown("Boundary outlines")
                st.info("Waiting...")

            with cols[5]:
                st.markdown("#### 6️⃣ Output")
                st.markdown("Export pattern")
                st.info("Waiting...")

    else:
        # Show results
        pattern = st.session_state.pattern

        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        # Calculate actual stitches (excluding background - most common color)
        grid_arr = np.array(pattern.grid)
        unique, counts = np.unique(grid_arr, return_counts=True)
        background_idx = unique[np.argmax(counts)]
        background_count = np.max(counts)
        actual_stitches = pattern.metadata.total_stitches - background_count

        # Find background color name
        if background_idx < len(pattern.legend):
            background_name = pattern.legend[background_idx].dmc_color.name
        else:
            background_name = f"Color {background_idx}"

        with col1:
            st.metric("Dimensions", f"{pattern.metadata.width}×{pattern.metadata.height}")
        with col2:
            st.metric("Colors", pattern.metadata.color_count)
        with col3:
            st.metric("Actual Stitches", f"{actual_stitches:,}",
                      help=f"Excludes background ({background_name})")
        with col4:
            st.metric("Difficulty", pattern.metadata.difficulty.capitalize())
        with col5:
            st.metric("Fabric Size", f'{pattern.metadata.fabric_width_inches:.1f}"×{pattern.metadata.fabric_height_inches:.1f}"')

        st.divider()

        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 Comparison",
            "🔧 Pipeline",
            "🎨 Color Preview",
            "✏️ Editor",
            "📝 Symbol Grid",
            "🧶 Thread List",
            "📥 Export"
        ])

        with tab1:
            st.markdown("### Pipeline Comparison")

            result = st.session_state.pipeline_result
            stages = result["stages"]
            is_predesigned = st.session_state.image_type == "predesigned"

            cell_size = max(4, 400 // pattern.metadata.width)

            if is_predesigned:
                # Pre-designed pipeline: Original → Quantized Full → Resized → Adjusted → Pattern → Backstitch
                st.caption("Pre-designed pipeline: K-means at full res → Boundary-preserving resize → Backstitch")

                stage_images = [("Original", st.session_state.original_image)]

                if stages.get("quantized_full") is not None:
                    stage_images.append(("Quantized", stages["quantized_full"]))

                if stages.get("resized") is not None:
                    stage_images.append(("Resized", stages["resized"]))

                if stages.get("adjusted") is not None:
                    stage_images.append(("Adjusted", stages["adjusted"]))

                pattern_preview = render_color_preview(pattern, cell_size=cell_size)
                stage_images.append(("DMC Colors", pattern_preview))

                # Add backstitch overlay if enabled
                if result.get("backstitch_settings") is not None:
                    if result.get("backstitch_segments") and len(result["backstitch_segments"]) > 0:
                        backstitch_color = result["backstitch_settings"].color
                        backstitch_preview = render_backstitch(
                            pattern_preview, result["backstitch_segments"],
                            cell_size=cell_size, color=backstitch_color, line_width=2
                        )
                        segment_count = len(result["backstitch_segments"])
                        stage_images.append((f"Backstitch ({segment_count} segments)", backstitch_preview))
                    else:
                        stage_images.append(("Backstitch (no boundaries)", pattern_preview))

            else:
                # Photo pipeline: Original → Pixelated → Adjusted → Pattern → Backstitch
                st.caption("Photo pipeline: LANCZOS resize + K-means quantization → Backstitch")

                stage_images = [("Original", st.session_state.original_image)]

                if stages.get("pixelated") is not None:
                    stage_images.append(("Pixelated", stages["pixelated"]))

                if stages.get("adjusted") is not None:
                    stage_images.append(("Adjusted", stages["adjusted"]))

                pattern_preview = render_color_preview(pattern, cell_size=cell_size)
                stage_images.append(("DMC Colors", pattern_preview))

                # Add backstitch overlay if enabled
                if result.get("backstitch_settings") is not None:
                    if result.get("backstitch_segments") and len(result["backstitch_segments"]) > 0:
                        backstitch_color = result["backstitch_settings"].color
                        backstitch_preview = render_backstitch(
                            pattern_preview, result["backstitch_segments"],
                            cell_size=cell_size, color=backstitch_color, line_width=2
                        )
                        segment_count = len(result["backstitch_segments"])
                        stage_images.append((f"Backstitch ({segment_count} segments)", backstitch_preview))
                    else:
                        stage_images.append(("Backstitch (no boundaries)", pattern_preview))

            # Display stages (upscale small images for pixel-perfect display)
            cols = st.columns(len(stage_images))
            for i, (label, stage_img) in enumerate(stage_images):
                with cols[i]:
                    st.markdown(f"**{label}**")
                    display_img = upscale_for_display(stage_img)
                    st.image(display_img, use_container_width=True)

            # Show stats
            if result.get("adjustment_stats"):
                stats = result["adjustment_stats"]
                st.markdown("---")
                st.markdown("#### Adjustment Statistics")

                stat_cols = st.columns(3)
                with stat_cols[0]:
                    st.metric("Pixels Changed", f"{stats['pixels_changed']:,}")
                with stat_cols[1]:
                    total_pixels = pattern.metadata.width * pattern.metadata.height
                    pct = (stats['pixels_changed'] / total_pixels) * 100
                    st.metric("Change Rate", f"{pct:.1f}%")
                with stat_cols[2]:
                    colors_removed = stats.get('colors_removed', 0)
                    st.metric("Colors Removed", colors_removed)

                if stats['operations_applied']:
                    st.markdown("**Operations applied:** " + " → ".join(stats['operations_applied']))

            # Show backstitch stats
            if result.get("backstitch_info"):
                bs_info = result["backstitch_info"]
                st.markdown("---")
                st.markdown("#### Backstitch Statistics")

                bs_cols = st.columns(4)
                with bs_cols[0]:
                    st.metric("Segments", bs_info["segment_count"])
                with bs_cols[1]:
                    st.metric("Total Length", f"{bs_info['total_length_stitches']} units")
                with bs_cols[2]:
                    st.metric("Horizontal", bs_info["horizontal_segments"])
                with bs_cols[3]:
                    st.metric("Vertical", bs_info["vertical_segments"])

        with tab2:
            st.markdown("### Pipeline Details")
            st.caption("Detailed breakdown of each processing step")

            result = st.session_state.pipeline_result
            if result and result.get("pipeline_info"):
                # Mode badge
                mode_label = "Pre-designed" if st.session_state.image_type == "predesigned" else "Photo/Artwork"
                st.markdown(f"**Mode:** `{mode_label}`")

                st.markdown("---")

                # Show each step
                for step in result["pipeline_info"]:
                    with st.expander(f"{step['name']}: {step['description']}", expanded=True):
                        details = step["details"]

                        if details.get("skipped"):
                            st.info("Skipped")
                        elif "mappings" in details:
                            # Special handling for DMC color mappings
                            st.markdown(f"**Method:** {details['method']}")

                            st.markdown("**Color Mappings:**")
                            mapping_data = []
                            for m in details["mappings"]:
                                mapping_data.append({
                                    "Original RGB": m["rgb"],
                                    "DMC Code": m["dmc_code"],
                                    "DMC Name": m["dmc_name"],
                                })
                            st.dataframe(mapping_data, hide_index=True, use_container_width=True)
                        elif "operations" in details:
                            # Adjustment step
                            st.markdown(f"**Pixels changed:** {details['pixels_changed']:,}")
                            st.markdown(f"**Colors after:** {details['colors_after']}")
                            if details["operations"]:
                                st.markdown("**Operations:**")
                                for op in details["operations"]:
                                    st.markdown(f"- {op}")
                        else:
                            # Generic details display
                            for key, value in details.items():
                                if key != "skipped":
                                    display_key = key.replace('_', ' ').title()
                                    st.markdown(f"**{display_key}:** {value}")
            else:
                st.warning("No pipeline info available")

        with tab3:
            st.markdown("### Color Preview")

            result = st.session_state.pipeline_result
            has_backstitch = result.get("backstitch_segments") and len(result["backstitch_segments"]) > 0

            col_view, col_backstitch = st.columns([2, 1])
            with col_view:
                view_type = st.radio("View Type", ["Color Blocks", "Thread Realistic"], horizontal=True)
            with col_backstitch:
                if has_backstitch:
                    show_backstitch = st.checkbox("Show Backstitch", value=True)
                else:
                    show_backstitch = False

            if view_type == "Color Blocks":
                preview_cell_size = 10
                img = render_color_preview(pattern, cell_size=preview_cell_size, show_grid=True)
            else:
                preview_cell_size = 8
                img = render_thread_realistic(pattern, cell_size=preview_cell_size)

            # Add backstitch overlay if requested
            if show_backstitch and has_backstitch:
                backstitch_color = result["backstitch_settings"].color
                img = render_backstitch(
                    img, result["backstitch_segments"],
                    cell_size=preview_cell_size, color=backstitch_color, line_width=2
                )

            st.image(img, use_container_width=True)

            # Legend
            st.markdown("### Color Legend")
            legend_img = render_legend(pattern)
            st.image(legend_img)

        with tab4:
            from streamlit_image_coordinates import streamlit_image_coordinates

            st.markdown("### Stitch Editor")
            st.markdown("**Click on the pattern** to select a stitch, then press a number key (0-9) or click a color to change it.")

            result = st.session_state.pipeline_result

            # Initialize edit tracking in session state
            if "stitch_edits" not in st.session_state:
                st.session_state.stitch_edits = []
            if "edited_grid" not in st.session_state:
                st.session_state.edited_grid = None
            if "selected_color_idx" not in st.session_state:
                st.session_state.selected_color_idx = 0
            if "edit_row" not in st.session_state:
                st.session_state.edit_row = 0
            if "edit_col" not in st.session_state:
                st.session_state.edit_col = 0

            # Get the pattern grid
            original_grid = np.array(pattern.grid)

            # Use edited grid if available
            if st.session_state.edited_grid is not None and st.session_state.edited_grid.shape == original_grid.shape:
                current_grid = st.session_state.edited_grid
            else:
                current_grid = original_grid.copy()
                st.session_state.edited_grid = current_grid

            h, w = current_grid.shape

            # Build palette info
            palette_colors = []
            for idx, entry in enumerate(pattern.legend):
                palette_colors.append({
                    "idx": idx,
                    "name": f"{entry.dmc_color.code} - {entry.dmc_color.name}",
                    "rgb": entry.dmc_color.rgb
                })

            # Color palette with number shortcuts
            st.markdown("#### Colors (press number to select)")
            color_cols = st.columns(min(len(palette_colors), 12))
            selected_color_idx = st.session_state.selected_color_idx

            for i, color_info in enumerate(palette_colors):
                col_idx = i % 12
                with color_cols[col_idx]:
                    rgb = color_info["rgb"]
                    hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    is_selected = color_info["idx"] == selected_color_idx
                    border = "3px solid red" if is_selected else "1px solid #ccc"
                    key_hint = i if i < 10 else ""

                    # Color swatch with number
                    if st.button(
                        f"{key_hint}",
                        key=f"color_btn_{i}",
                        help=color_info["name"],
                        use_container_width=True
                    ):
                        st.session_state.selected_color_idx = i
                        st.rerun()

                    st.markdown(
                        f'<div style="background-color:{hex_color}; height:25px; '
                        f'border:{border}; margin-top:-10px;"></div>',
                        unsafe_allow_html=True
                    )

            # Current selection info
            edit_row = st.session_state.edit_row
            edit_col = st.session_state.edit_col
            current_color = current_grid[edit_row, edit_col]
            current_color_name = next(
                (c["name"] for c in palette_colors if c["idx"] == current_color),
                f"Color {current_color}"
            )
            selected_color_name = next(
                (c["name"] for c in palette_colors if c["idx"] == selected_color_idx),
                f"Color {selected_color_idx}"
            )

            st.markdown(f"**Selected:** ({edit_row}, {edit_col}) = {current_color_name} | **Paint:** [{selected_color_idx}] {selected_color_name}")

            # Navigation controls - step size first so it's available
            step_col, pos_col = st.columns([1, 2])
            with step_col:
                step = st.selectbox("Step", [1, 5, 10], index=0, key="nav_step")
            with pos_col:
                r_col, c_col = st.columns(2)
                with r_col:
                    new_row = st.number_input("Row", 0, h-1, edit_row, key="manual_row")
                with c_col:
                    new_col = st.number_input("Col", 0, w-1, edit_col, key="manual_col")
                if new_row != edit_row or new_col != edit_col:
                    st.session_state.edit_row = new_row
                    st.session_state.edit_col = new_col
                    st.rerun()

            # Arrow navigation + apply
            c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 2])
            with c1:
                if st.button("↑", key="nav_up", use_container_width=True):
                    st.session_state.edit_row = max(0, edit_row - step)
                    st.rerun()
            with c2:
                if st.button("↓", key="nav_down", use_container_width=True):
                    st.session_state.edit_row = min(h - 1, edit_row + step)
                    st.rerun()
            with c3:
                if st.button("←", key="nav_left", use_container_width=True):
                    st.session_state.edit_col = max(0, edit_col - step)
                    st.rerun()
            with c4:
                if st.button("→", key="nav_right", use_container_width=True):
                    st.session_state.edit_col = min(w - 1, edit_col + step)
                    st.rerun()
            with c5:
                if st.button("Paint", key="nav_apply", type="primary", use_container_width=True):
                    old_color = current_grid[edit_row, edit_col]
                    new_color = selected_color_idx
                    if old_color != new_color:
                        current_grid[edit_row, edit_col] = new_color
                        st.session_state.edited_grid = current_grid
                        st.session_state.stitch_edits.append({
                            "id": len(st.session_state.stitch_edits),
                            "row": edit_row,
                            "col": edit_col,
                            "old": int(old_color),
                            "new": int(new_color)
                        })
                        st.rerun()

            # Create clickable preview image
            cell_size = 10
            preview = np.zeros((h * cell_size, w * cell_size, 3), dtype=np.uint8)

            for row in range(h):
                for col in range(w):
                    color_idx = current_grid[row, col]
                    rgb = next(
                        (c["rgb"] for c in palette_colors if c["idx"] == color_idx),
                        (128, 128, 128)
                    )
                    y1, y2 = row * cell_size, (row + 1) * cell_size
                    x1, x2 = col * cell_size, (col + 1) * cell_size
                    preview[y1:y2, x1:x2] = rgb

            # Highlight selected cell with red border
            y1, y2 = edit_row * cell_size, (edit_row + 1) * cell_size
            x1, x2 = edit_col * cell_size, (edit_col + 1) * cell_size
            preview[y1:y1+2, x1:x2] = [255, 0, 0]
            preview[y2-2:y2, x1:x2] = [255, 0, 0]
            preview[y1:y2, x1:x1+2] = [255, 0, 0]
            preview[y1:y2, x2-2:x2] = [255, 0, 0]

            preview_img = Image.fromarray(preview)

            # Clickable image
            st.markdown("#### Click to select stitch:")
            coords = streamlit_image_coordinates(preview_img, key="editor_click")

            if coords is not None:
                click_x = coords["x"]
                click_y = coords["y"]
                # Convert pixel coords to grid coords
                clicked_col = int(click_x / cell_size)
                clicked_row = int(click_y / cell_size)
                # Clamp to valid range
                clicked_row = max(0, min(h - 1, clicked_row))
                clicked_col = max(0, min(w - 1, clicked_col))

                # Update selection directly (rerun happens naturally on next interaction)
                st.session_state.edit_row = clicked_row
                st.session_state.edit_col = clicked_col
                # Show current click
                st.info(f"Clicked: row {clicked_row}, col {clicked_col}")

            # Edit history with delete buttons
            st.markdown("---")
            st.markdown("#### Edit History")

            if st.session_state.stitch_edits:
                # Show edits with delete buttons
                for i, edit in enumerate(reversed(st.session_state.stitch_edits[-10:])):
                    actual_idx = len(st.session_state.stitch_edits) - 1 - i
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        old_name = next((c["name"] for c in palette_colors if c["idx"] == edit["old"]), str(edit["old"]))
                        new_name = next((c["name"] for c in palette_colors if c["idx"] == edit["new"]), str(edit["new"]))
                        st.text(f"({edit['row']}, {edit['col']}): {old_name} → {new_name}")
                    with col2:
                        if st.button("↩️", key=f"undo_{actual_idx}", help="Undo this edit"):
                            # Revert this specific edit
                            current_grid[edit["row"], edit["col"]] = edit["old"]
                            st.session_state.edited_grid = current_grid
                            st.session_state.stitch_edits.pop(actual_idx)
                            st.rerun()

                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Clear All Edits"):
                        st.session_state.stitch_edits = []
                        st.session_state.edited_grid = original_grid.copy()
                        st.rerun()
                with col2:
                    total_edits = len(st.session_state.stitch_edits)
                    unique_cells = len(set((e["row"], e["col"]) for e in st.session_state.stitch_edits))
                    st.caption(f"{total_edits} edits, {unique_cells} cells")
                with col3:
                    import json
                    edit_json = json.dumps(st.session_state.stitch_edits, indent=2)
                    st.download_button(
                        "Export Log",
                        edit_json,
                        file_name="stitch_edits.json",
                        mime="application/json"
                    )
            else:
                st.info("No edits yet. Click on the pattern to select a stitch, then click a color number.")

        with tab5:
            st.markdown("### Symbol Grid")
            st.markdown("*Use this for stitching*")

            cell_size = st.slider("Cell Size", 10, 40, 20, key="symbol_cell_size")
            symbol_grid = render_symbol_grid(pattern, cell_size=cell_size)
            st.image(symbol_grid, use_container_width=True)

        with tab6:
            st.markdown("### Thread Shopping List")

            calc = ThreadCalculator(fabric_count=fabric_count)
            estimates = calc.estimate_all(pattern)

            # Summary
            total_skeins = sum(e["skeins"] for e in estimates)
            total_meters = sum(e["meters"] for e in estimates)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Skeins Needed", total_skeins)
            with col2:
                st.metric("Total Thread Length", f"{total_meters:.1f}m")

            # Table
            st.dataframe(
                estimates,
                column_config={
                    "dmc_code": st.column_config.TextColumn("DMC Code"),
                    "name": st.column_config.TextColumn("Color Name"),
                    "stitch_count": st.column_config.NumberColumn("Stitches", format="%d"),
                    "meters": st.column_config.NumberColumn("Meters", format="%.1f"),
                    "skeins": st.column_config.NumberColumn("Skeins"),
                },
                hide_index=True,
                use_container_width=True
            )

        with tab7:
            st.markdown("### Export Pattern")

            result = st.session_state.pipeline_result
            has_backstitch = result.get("backstitch_segments") and len(result["backstitch_segments"]) > 0

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### PNG Exports")

                # Color preview
                preview_png = render_color_preview(pattern, cell_size=10)
                buf = io.BytesIO()
                preview_png.save(buf, format="PNG")
                st.download_button(
                    "📷 Download Color Preview",
                    buf.getvalue(),
                    file_name=f"{pattern.metadata.title}_color.png",
                    mime="image/png"
                )

                # With backstitch overlay
                if has_backstitch:
                    backstitch_color = result["backstitch_settings"].color
                    preview_with_backstitch = render_backstitch(
                        preview_png, result["backstitch_segments"],
                        cell_size=10, color=backstitch_color, line_width=2
                    )
                    buf = io.BytesIO()
                    preview_with_backstitch.save(buf, format="PNG")
                    st.download_button(
                        "🪡 Download With Backstitch",
                        buf.getvalue(),
                        file_name=f"{pattern.metadata.title}_with_backstitch.png",
                        mime="image/png"
                    )

                # Symbol grid
                symbol_png = render_symbol_grid(pattern, cell_size=20)
                buf = io.BytesIO()
                symbol_png.save(buf, format="PNG")
                st.download_button(
                    "📝 Download Symbol Grid",
                    buf.getvalue(),
                    file_name=f"{pattern.metadata.title}_symbols.png",
                    mime="image/png"
                )

                # Realistic
                realistic_png = render_thread_realistic(pattern, cell_size=8)
                buf = io.BytesIO()
                realistic_png.save(buf, format="PNG")
                st.download_button(
                    "🧵 Download Realistic Preview",
                    buf.getvalue(),
                    file_name=f"{pattern.metadata.title}_realistic.png",
                    mime="image/png"
                )

            with col2:
                st.markdown("#### PDF & Data")

                # PDF export - generate on demand
                @st.cache_data
                def generate_pdf(pattern_dict, title):
                    """Generate PDF and return bytes."""
                    # Reconstruct pattern from dict for caching
                    from xstitchlab.core.pattern import Pattern
                    p = Pattern.from_dict(pattern_dict)

                    with tempfile.TemporaryDirectory() as tmpdir:
                        exporter = PDFExporter(tmpdir)
                        pdf_path = exporter.export_pattern(p, title)
                        with open(pdf_path, "rb") as f:
                            return f.read()

                pdf_bytes = generate_pdf(pattern.to_dict(), pattern.metadata.title)
                st.download_button(
                    "📄 Download PDF Pattern",
                    pdf_bytes,
                    file_name=f"{pattern.metadata.title}_pattern.pdf",
                    mime="application/pdf"
                )

                # JSON export
                import json
                json_data = json.dumps(pattern.to_dict(), indent=2)
                st.download_button(
                    "💾 Download Pattern Data (JSON)",
                    json_data,
                    file_name=f"{pattern.metadata.title}.json",
                    mime="application/json"
                )

                # Shopping list
                shopping_list = calc.get_shopping_list(pattern)
                st.download_button(
                    "🛒 Download Shopping List",
                    shopping_list,
                    file_name=f"{pattern.metadata.title}_shopping_list.txt",
                    mime="text/plain"
                )

                # Backstitch instructions
                if has_backstitch:
                    bs_instructions = backstitch_instructions(
                        result["backstitch_segments"],
                        color_name="Black" if result["backstitch_settings"].color == (0, 0, 0) else "Custom"
                    )
                    st.download_button(
                        "🪡 Download Backstitch Instructions",
                        bs_instructions,
                        file_name=f"{pattern.metadata.title}_backstitch.txt",
                        mime="text/plain"
                    )


if __name__ == "__main__":
    main()
