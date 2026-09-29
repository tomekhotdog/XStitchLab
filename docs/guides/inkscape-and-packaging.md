# Inkscape & Packaging Guide

Quick reference for working with Inkscape and the kit packaging workflow.

---

## Inkscape Basics

### Adding text
1. Press **T** (Text tool), click on canvas, type
2. Change font/size in the top toolbar
3. Change colour by clicking the palette bar at the bottom
4. Press **Esc** or **F1** to switch back to Select tool

### Resize an image (keep proportions)
- Select the image, click the **lock icon** between W and H in the top toolbar so it's locked
- Change one dimension, the other follows

### Crop to a square
1. Draw a square with Rectangle tool (**R**), hold **Ctrl** for perfect square
2. Select both image and square (Shift+click)
3. **Object → Clip → Set**
4. To undo: **Object → Clip → Release**

### Export a section as PDF
1. Select all objects for that section
2. **File → Export** (Shift+Ctrl+E)
3. Choose **Selection**, set format to **PDF**, export

### Change units to mm
- Select an object, change the **units dropdown** next to W/H in the toolbar from `px` to `mm`
- Or set default in **File → Document Properties**

### Text converted to curves
- "Curves" (aka outlines/paths) means text is no longer editable — it's vector shapes
- Designers do this for print-ready files so the recipient doesn't need the fonts installed
- **You can't convert back** — delete the curved text and retype with the Text tool

---

## Fonts Used on Packaging

All free from Google Fonts. Installed in `~/Library/Fonts/`.

| Font | Usage |
|------|-------|
| **Cinzel Decorative Bold** | Brand name, collection title |
| **Cormorant Garamond Italic** | Tagline, descriptions (substitute for Literaturnaya — better Unicode support for ü, ń, etc.) |
| **Barlow** | Kit contents, metadata |

---

## Sticker Dimensions

| Label | Box size | Sticker size (2mm inset) |
|-------|----------|--------------------------|
| Front | 173 × 125mm | **169 × 121mm** |
| Back | 60 × 125mm | **56 × 121mm** |

The 2mm inset provides alignment tolerance when applying stickers to the box — a thin border of white box is visible around the edge. Looks intentional and clean.

---

## Postal Constraint

Assembled kit must qualify as a **Royal Mail Large Letter**:
- Max: 353 × 250 × **25mm**, up to 750g
- Cost: ~£2.50 (2nd class)
- The A6 box is 173 × 125 × 20mm — fits comfortably

Next size down (Letter) is max 0.5cm depth — too thin for a kit.

---

## Thread Calculations

Each kit includes pre-cut **60cm sections of 6-strand DMC thread**.

The stitcher separates strands:
- **Cross stitch (2 strands):** one 60cm section → 3 usable lengths → 180cm of stitching thread
- **Backstitch (1 strand):** one 60cm section → 6 usable lengths → 360cm of stitching thread

**Formula:**
- Cross stitch: `sections = ceil(stitches × 1.5cm / 180cm)`
- Backstitch: `sections = ceil(segments × 1.0cm / 360cm)`

The 1.5cm and 1.0cm per-stitch estimates include ~20% wastage. Rounding up to whole sections adds further buffer. For colours with tight margins (<10% buffer), consider adding an extra section.

---

## HP OfficeJet 250 Capabilities

| Media type | Weight range |
|-----------|-------------|
| Plain paper | 60–120 gsm |
| Cards | up to ~300 gsm |
| Envelopes | 75–205 gsm |

Good for: pattern sheets, instruction sheets, labels/wraps on lighter card.
Not reliable for: box-weight card stock (250-350gsm) — at the limit, likely to jam.

---

## Useful Suppliers (UK)

**Boxes:**
- [Tiny Box Company](https://www.tinyboxcompany.co.uk) — current box: Luxury Thin A6 Gift Box

**Stickers:**
- [Discount Sticker Printing](https://www.discountstickerprinting.co.uk)
- [StickerShop](https://www.stickershop.co.uk)
- [Sticker It](https://www.stickerit.co)

**Spec when ordering stickers:** Self-adhesive paper, matte finish, full colour, custom size. Match finish to box (matte box = matte sticker).
