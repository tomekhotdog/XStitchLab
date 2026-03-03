# XStitchLabs Landing Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a simple static landing page for xstitchlabs.com featuring the first cross-stitch design.

**Architecture:** Single HTML file with inline CSS, no build tools or frameworks. Hosted on Railway.

**Tech Stack:** HTML, CSS, Google Fonts (UnifrakturCook)

---

### Task 1: Set up directory and copy assets

**Files:**
- Create: `website/` directory
- Copy: `docs/upwork/example_image_3_brothers_riga.png` → `website/three-brothers-riga.png`

**Step 1: Create directory and copy image**

```bash
mkdir -p website
cp docs/upwork/example_image_3_brothers_riga.png website/three-brothers-riga.png
```

**Step 2: Verify**

```bash
ls website/
```

Expected: `three-brothers-riga.png`

---

### Task 2: Create index.html

**Files:**
- Create: `website/index.html`

**Step 1: Write the HTML file**

Single file containing:

- `<head>`: Meta tags (charset, viewport, description), Google Fonts link for UnifrakturCook, inline `<style>` block
- **Hero section**: "XStitchLabs" brand in system sans-serif, "Hanseatic Collection" series label, tagline "Cross-stitch the cities of the Hansa"
- **Featured design section**: The Three Brothers preview image, "No. 01 — The Three Brothers, Riga" (design name in UnifrakturCook blackletter), description text, stats (1,182 stitches · 8 colours · Medium difficulty), kit contents
- **Footer**: "More designs coming soon", Instagram link (@hanseatic.tomek), xstitchlabs.com

**CSS requirements:**
- Mobile-first responsive layout (single column on mobile, centred with max-width on desktop)
- Colour palette from The Three Brothers: sage green (#9EA383), warm beige (#D4B896), muted terracotta (#C17B5F), coffee brown (#3E2B1E), light background (#F8F6F1)
- Lots of whitespace, clean typography
- System sans-serif stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif`
- UnifrakturCook for design name accent only
- Image should be nicely presented (subtle shadow or border, not full-bleed)

**Step 2: Open in browser to verify**

```bash
open website/index.html
```

Check: renders correctly, responsive on mobile (use browser dev tools), fonts load, image displays.

**Step 3: Commit**

```bash
git add website/
git commit -m "feat: add XStitchLabs landing page with Three Brothers design"
```
