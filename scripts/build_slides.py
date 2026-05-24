"""
Build the PowerPoint slide deck for the eiGroup presentation.

Produces: presentation/eigroup_reservoir_analytics.pptx

Every slide is built from scratch using python-pptx primitives, so once
opened in PowerPoint, every text box, image, and shape can be freely edited,
resized, recoloured, or replaced.

Slide structure (consistent across the deck):
    - Title bar (top, blue)
    - Optional subtitle (italic, grey)
    - Body: text bullets and/or one chart image
    - Takeaway line (bottom, bold, dark blue)
    - Slide number (bottom-right, small grey)

Usage:
    pip install python-pptx
    python scripts/build_slides.py

Output:
    presentation/eigroup_reservoir_analytics.pptx
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# =============================================================================
# Style — brand colours matched to the field-view charts
# =============================================================================
COLOR_PRIMARY = RGBColor(0x00, 0x72, 0xB2)    # blue (Zone B colour)
COLOR_TEXT_DARK = RGBColor(0x22, 0x22, 0x22)
COLOR_TEXT_GREY = RGBColor(0x66, 0x66, 0x66)
COLOR_TAKEAWAY = RGBColor(0x00, 0x5A, 0x8E)   # darker blue
COLOR_ACCENT_WARN = RGBColor(0xD5, 0x5E, 0x00)   # red — for "warning" findings
COLOR_ACCENT_GOOD = RGBColor(0x00, 0x9E, 0x73)   # green — for positive findings

# Repo root
REPO = Path(__file__).resolve().parent.parent
FIGS = REPO / "outputs" / "figures"


# =============================================================================
# Helper functions
# =============================================================================

def add_title(slide, text, top=Inches(0.3)):
    """Blue title bar at top of slide."""
    tx = slide.shapes.add_textbox(Inches(0.4), top, Inches(12.5), Inches(0.7))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = COLOR_PRIMARY
    return tx


def add_subtitle(slide, text, top=Inches(1.0)):
    tx = slide.shapes.add_textbox(Inches(0.4), top, Inches(12.5), Inches(0.4))
    tf = tx.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(14)
    run.font.italic = True
    run.font.color.rgb = COLOR_TEXT_GREY
    return tx


def add_bullets(slide, bullets, left=Inches(0.4), top=Inches(1.5),
                width=Inches(7.0), height=Inches(5.0), font_size=Pt(16)):
    """Add a bulleted list. Each item is either a string or a dict with
    'text' and optional 'highlight' (bool) keys."""
    tx = slide.shapes.add_textbox(left, top, width, height)
    tf = tx.text_frame
    tf.word_wrap = True

    for i, item in enumerate(bullets):
        if isinstance(item, dict):
            text = item.get("text", "")
            highlight = item.get("highlight", False)
        else:
            text = str(item)
            highlight = False

        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(4)
        p.space_after = Pt(4)

        # Bullet character + content
        run = p.add_run()
        run.text = "•  " + text
        run.font.size = font_size
        run.font.bold = highlight
        run.font.color.rgb = COLOR_ACCENT_WARN if highlight else COLOR_TEXT_DARK

    return tx


def add_takeaway(slide, text):
    """Bold takeaway line near the bottom of the slide."""
    tx = slide.shapes.add_textbox(Inches(0.4), Inches(6.5), Inches(12.5), Inches(0.6))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = "→  " + text
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.italic = True
    run.font.color.rgb = COLOR_TAKEAWAY
    return tx


def add_image(slide, image_path, left, top, width=None, height=None):
    """Add an image to the slide if it exists, else add a placeholder text."""
    if image_path is None or not Path(image_path).exists():
        tx = slide.shapes.add_textbox(left, top,
                                      width or Inches(5), height or Inches(3))
        tf = tx.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = f"[ image missing: {Path(image_path).name if image_path else '?'} ]"
        run.font.italic = True
        run.font.color.rgb = COLOR_TEXT_GREY
        return tx
    if width and height:
        return slide.shapes.add_picture(str(image_path), left, top,
                                        width=width, height=height)
    if width:
        return slide.shapes.add_picture(str(image_path), left, top, width=width)
    return slide.shapes.add_picture(str(image_path), left, top, height=height)


def add_slide_number(slide, n, total):
    tx = slide.shapes.add_textbox(Inches(12.3), Inches(7.05), Inches(1.0), Inches(0.3))
    tf = tx.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = f"{n} / {total}"
    run.font.size = Pt(10)
    run.font.color.rgb = COLOR_TEXT_GREY


def add_horizontal_divider(slide, y=Inches(1.05)):
    """A thin blue line below the title."""
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.4), y, Inches(12.5), Inches(0.04),
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_PRIMARY
    line.line.fill.background()


# =============================================================================
# Slide builders — one function per slide
# =============================================================================

def slide_1_title(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    # Big centered title
    tx = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.3), Inches(1.5))
    tf = tx.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "Reservoir-Volume Characterization"
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = COLOR_PRIMARY

    # Subtitle
    tx2 = slide.shapes.add_textbox(Inches(1), Inches(3.7), Inches(11.3), Inches(0.8))
    tf2 = tx2.text_frame
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = "Method, findings, and a defensible field strategy across 7 wells"
    run2.font.size = Pt(20)
    run2.font.italic = True
    run2.font.color.rgb = COLOR_TEXT_GREY

    # Author strip
    tx3 = slide.shapes.add_textbox(Inches(1), Inches(5.8), Inches(11.3), Inches(0.5))
    tf3 = tx3.text_frame
    p3 = tf3.paragraphs[0]
    p3.alignment = PP_ALIGN.CENTER
    run3 = p3.add_run()
    run3.text = "Kamil Muradli   ·   eiGroup Associate Data Scientist assessment   ·   May 2026"
    run3.font.size = Pt(14)
    run3.font.color.rgb = COLOR_TEXT_DARK
    return slide


def slide_2_qc_findings(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Three QC findings that shape every downstream decision")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Caught at load-time, surfaced in every metric")
    bullets = [
        "well_3: 78 NaN porosity samples (4%) → excluded from net, counted separately",
        "well_5: logged at 0.5 m spacing; others at 0.2 m → dz computed per-well",
        {"text": "ALL 7 wells: 15-30% of samples at the 15,000 mD permeability cap",
         "highlight": True},
        " ",
        "Saturation matters most: it makes kh estimates a LOWER BOUND, not a best estimate",
        "Each finding surfaces as a counter column in every downstream metric",
        "QC is not paperwork — it drives the credibility of every number that follows",
    ]
    add_bullets(slide, bullets, top=Inches(1.4), width=Inches(12.5))
    add_takeaway(slide, "The QC step is the source of every caveat in this analysis.")


def slide_3_per_zone(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Net-to-Gross by zone tells the geological story")
    add_horizontal_divider(slide)
    add_image(slide, FIGS / "02_kh_stacked_bar.png",
              left=Inches(0.4), top=Inches(1.3), width=Inches(7.5))
    bullets = [
        "Zone B dominates: 93% NTG, 10× the kh of any other zone",
        "Zone D: 10% NTG everywhere — tight rock, not reservoir",
        "Zone C: silent second story (84% NTG, 680K mD·m)",
        "Same pattern in all 7 wells — geology is reproducible",
        " ",
        "Field volume = sum of (zone × well) kh contributions",
        "Operational ranking: B → C → E → A → D",
    ]
    add_bullets(slide, bullets, left=Inches(8.2), top=Inches(1.4),
                width=Inches(5.0), font_size=Pt(14))
    add_takeaway(slide, "NTG is more diagnostic than any single permeability number.")


def slide_4_sensitivity(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Cutoff sensitivity tells us which volumes are brittle")
    add_horizontal_divider(slide)
    add_image(slide, FIGS / "04_ntg_sensitivity.png",
              left=Inches(0.4), top=Inches(1.3), width=Inches(7.5))
    bullets = [
        "Zone B NTG: stable across the full sweep (range only 0.11)",
        "Zone A NTG: highly sensitive (0.15 → 0.95 across 0.30-0.70 cutoffs)",
        "Knee for all zones at vsh ≈ 0.35 (same in all 7 wells)",
        "Default cutoff (0.5) sits on the flat part of each curve",
        " ",
        {"text": "Zone B is the MOST defensible volume estimate in the field",
         "highlight": True},
    ]
    add_bullets(slide, bullets, left=Inches(8.2), top=Inches(1.4),
                width=Inches(5.0), font_size=Pt(14))
    add_takeaway(slide, "Zone B's volume estimate doesn't depend on cutoff choice — that's robustness.")


def slide_5_lorenz(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "When 'homogeneous' is an instrument artefact")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Lorenz curves expose tool censoring")
    add_image(slide, FIGS / "05_lorenz_curves.png",
              left=Inches(0.4), top=Inches(1.5), width=Inches(6.5))
    bullets = [
        "Zone C: L = 0.65 — genuinely heterogeneous, top 30% delivers 80% of kh",
        "Zone E: L = 0.52, Zone A: L = 0.46 — moderate heterogeneity",
        {"text": "Zone B: L = 0.00 — but this is a TOOL ARTEFACT, not homogeneity",
         "highlight": True},
        " ",
        "88% of Zone B samples are at the 15,000 mD cap",
        "The Lorenz curve flattens into the 45° diagonal mechanically",
        "Lesson: don't interpret Lorenz on censored data",
    ]
    add_bullets(slide, bullets, left=Inches(7.3), top=Inches(1.5),
                width=Inches(5.8), font_size=Pt(14))
    add_takeaway(slide, "The strongest signal of saturation isn't a number — it's a flat Lorenz curve.")


def slide_6_well_ranking(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Saturation pollutes well rankings")
    add_horizontal_divider(slide)
    add_image(slide, FIGS / "01_kh_heatmap.png",
              left=Inches(0.4), top=Inches(1.3), width=Inches(7.5))
    bullets = [
        "well_7 ranks #1 by kh (2.59 M) — but 30% tool-capped",
        "well_1 ranks #2 (2.27 M) — 25% tool-capped",
        "wells 2/4/5/6 at 14-15% saturation — more defensible 'best wells'",
        " ",
        {"text": "⚠ marker in heatmap = saturation count per (well, zone)",
         "highlight": False},
        " ",
        "Production fix: saturation-weighted kh ranking",
        "Long-term fix: uncensored perm tool + core calibration",
    ]
    add_bullets(slide, bullets, left=Inches(8.2), top=Inches(1.4),
                width=Inches(5.0), font_size=Pt(14))
    add_takeaway(slide, "The highest-kh well may just be the most censored well.")


def slide_7_zone_d(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Zone D should be bypassed")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Tight rock, not reservoir — fails on porosity, not shale")
    bullets = [
        "Zone D NTG never exceeds 32% — even at the loosest cutoff (vsh ≤ 0.7)",
        "avg phit in Zone D = 0.092 — right at the phit cutoff (0.08)",
        "Samples fail the POROSITY test, not the shale test",
        "No matter how generous the shale tolerance, Zone D is not reservoir",
        " ",
        "All 7 wells: same finding",
        "Operational implication: skip Zone D in volume calculations",
        "Don't drill into it; don't model it; document the bypass decision",
    ]
    add_bullets(slide, bullets, top=Inches(1.5), width=Inches(12.5))
    add_takeaway(slide, "Bypassing Zone D is unambiguous. The geology says so.")


def slide_8_bootstrap(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Where our kh estimates are most uncertain")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Bootstrap confidence intervals: precision vs accuracy")
    bullets = [
        "Method: 200 resamples per (well, zone) group, 90% percentile CI",
        "Most groups: tight CIs (high sample counts, low variance)",
        "Zone D: wide CI relative to point estimate — but magnitudes are tiny",
        "Zone B: tight CI — but high SAMPLING precision doesn't fix saturation BIAS",
        " ",
        "Bootstrap measures sampling uncertainty, not measurement bias",
        "A censored tool is a measurement bias the bootstrap can't see",
        "Saturation remains the dominant uncertainty in Zone B kh",
    ]
    add_bullets(slide, bullets, top=Inches(1.5), width=Inches(12.5))
    add_takeaway(slide,
                 "Our numbers are PRECISE. Whether they're ACCURATE depends on the tool — different problem.")


def slide_9_clustering_choice(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Two clustering attempts: Zone B failed (instructive), Zone C worked")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Method awareness: knowing when not to trust your own model")

    # Left column — Zone B
    tx1 = slide.shapes.add_textbox(Inches(0.4), Inches(1.5), Inches(6.2), Inches(0.5))
    p1 = tx1.text_frame.paragraphs[0]
    r1 = p1.add_run()
    r1.text = "Zone B (initial target)"
    r1.font.size = Pt(18)
    r1.font.bold = True
    r1.font.color.rgb = COLOR_ACCENT_WARN

    b1 = [
        "Highest kh, highest NTG — obvious first choice",
        "Silhouette peaks at k=2 (0.65), drops at k=3",
        "But: two clusters have IDENTICAL centroids",
        "  – vsh 0.243 vs 0.233 (Δ = 0.01)",
        "  – log_perm 4.17 vs 4.16",
        "  – 96% saturated in EVERY sub-zone",
        "LOWO ARI = 0.97 — reproducibly meaningless",
    ]
    add_bullets(slide, b1, left=Inches(0.4), top=Inches(2.0),
                width=Inches(6.2), font_size=Pt(13))

    # Right column — Zone C
    tx2 = slide.shapes.add_textbox(Inches(7.0), Inches(1.5), Inches(6.0), Inches(0.5))
    p2 = tx2.text_frame.paragraphs[0]
    r2 = p2.add_run()
    r2.text = "Zone C (re-targeted)"
    r2.font.size = Pt(18)
    r2.font.bold = True
    r2.font.color.rgb = COLOR_ACCENT_GOOD

    b2 = [
        "<1% saturation — clean signal",
        "Real Lorenz = 0.65 (Slide 5)",
        "NTG 84%, kh 680K, all 7 wells",
        "3 sub-zones with 5× perm separation",
        "Same vertical stack in every well",
        "LOWO ARI = 0.97 — meaningfully reproducible",
    ]
    add_bullets(slide, b2, left=Inches(7.0), top=Inches(2.0),
                width=Inches(6.0), font_size=Pt(13))

    add_takeaway(slide,
                 "Clustering can only see what the tool measures. When tools are censored, clusters reproduce the censoring.")


def slide_10_zone_c_clusters(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Zone C splits into 3 reproducible sub-zones")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Three rock types, one geological column, 7 wells")
    add_image(slide, FIGS / "06_zonec_clusters_log.png",
              left=Inches(0.4), top=Inches(1.5), width=Inches(7.0))
    bullets = [
        "Sub-zone 0: tight  (~200 mD, phit 0.14, vsh 0.45)",
        "Sub-zone 1: mid    (~700 mD, phit 0.21, vsh 0.34)",
        {"text": "Sub-zone 2: best  (~1,100 mD, phit 0.23, vsh 0.29)", "highlight": True},
        " ",
        "Vertical stack consistent across all 7 wells:",
        "  – Best on top  ·  tight in middle  ·  mid at base",
        "LOWO Adjusted Rand Index = 0.95–0.99",
    ]
    add_bullets(slide, bullets, left=Inches(7.8), top=Inches(1.5),
                width=Inches(5.5), font_size=Pt(14))
    add_takeaway(slide, "Three orders of magnitude separation. Same stack in every well. Real geology.")


def slide_11_drilling_target(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Sub-zone 2 is the drilling target")
    add_horizontal_divider(slide)
    add_subtitle(slide, "29% of Zone C thickness — 48% of Zone C flow capacity")
    bullets = [
        "Sub-zone 2 thickness: 315.6 m total across 7 wells (29% of Zone C)",
        "Sub-zone 2 kh:        350 K mD·m         (48% of Zone C)",
        "Geological location: TOP of Zone C in every well",
        "Saturation:           <1% — the 1,100 mD estimate is defensible",
        " ",
        {"text": "Completion implication: place perforations in the top third of Zone C",
         "highlight": True},
        " ",
        "Drilling implication: vertical wells targeting Zone C should land at sub-zone 2 depth",
        "Risk: minimal — geology reproduces across all 7 wells",
    ]
    add_bullets(slide, bullets, top=Inches(1.5), width=Inches(12.5))
    add_takeaway(slide, "The clearest operational recommendation in this whole analysis.")


def slide_12_k_choice(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "k=3 by geological intuition, not by silhouette pick")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Choosing the number of clusters — defensibly")
    add_image(slide, FIGS / "07_zonec_silhouette.png",
              left=Inches(0.4), top=Inches(1.5), width=Inches(7.0))
    bullets = [
        "Silhouette ranks k=2 highest in both zones (0.65 / 0.39)",
        "BIC monotonically prefers higher k (GMM overfits noise)",
        " ",
        "We chose k=3 for geological reasons:",
        "  – Three lithology classes standard in clastics",
        "  – At k=3 Zone C centroids separate 5× in perm",
        "  – At k=2 two real lithologies collapse together",
        "  – At k=4 we'd be splitting noise",
        " ",
        "Post-hoc validation: log_perm centroids 1.92, 2.44, 2.65",
    ]
    add_bullets(slide, bullets, left=Inches(7.6), top=Inches(1.5),
                width=Inches(5.7), font_size=Pt(13))
    add_takeaway(slide, "Don't outsource the lithology count to a silhouette score.")


def slide_13_engineering(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Production-ready engineering")
    add_horizontal_divider(slide)
    add_subtitle(slide, "Single-command reproducible pipeline, fully tested")
    add_image(slide, FIGS / "00_architecture.png",
              left=Inches(0.4), top=Inches(1.5), width=Inches(8.5))
    bullets = [
        "105 pytest tests across 6 modules",
        "96-100% coverage on hot paths",
        "  – metrics: 99%, sensitivity: 96%",
        "  – clustering: 97%, viz: 100%",
        " ",
        "Single-command CLI:",
        "  quality → metrics → sweep → field → subzones",
        " ",
        "Every chart: matplotlib PNG + Plotly HTML",
        "Reproducible from raw CSVs in 5 commands",
    ]
    add_bullets(slide, bullets, left=Inches(9.2), top=Inches(1.5),
                width=Inches(4.0), font_size=Pt(12))
    add_takeaway(slide, "This is a pipeline, not a notebook — re-runnable when new wells arrive.")


def slide_14_summary(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Five decisions this analysis supports")
    add_horizontal_divider(slide)

    bullets = [
        {"text": "Treat Zone B kh as a CONSERVATIVE LOWER BOUND — not a best estimate",
         "highlight": True},
        " ",
        {"text": "BYPASS Zone D — it's tight rock, not reservoir",
         "highlight": True},
        " ",
        {"text": "TARGET sub-zone 2 (top of Zone C) for drilling and completion",
         "highlight": True},
        " ",
        {"text": "RE-RANK wells using saturation-weighted kh, not raw kh",
         "highlight": True},
        " ",
        {"text": "CALIBRATE Zone A and Zone C cutoffs to core data before publishing volumes",
         "highlight": True},
    ]
    add_bullets(slide, bullets, top=Inches(1.5), width=Inches(12.5), font_size=Pt(18))
    add_takeaway(slide,
                 "Happy to go deep on any of these — and to discuss what I'd do differently with more data.")


# =============================================================================
# Backup slides
# =============================================================================

def slide_B1_bootstrap_detail(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Backup: bootstrap method details")
    add_horizontal_divider(slide)
    bullets = [
        "Per (well, zone) group, 200 resamples with replacement",
        "Within each resample: apply same net cutoffs (vsh ≤ 0.5, phit ≥ 0.08)",
        "kh = Σ(perm × dz) on the resampled net interval",
        "Report kh mean + 5th/95th percentiles = 90% CI",
        "Seed = 42 for reproducibility",
        " ",
        "Cost: 35 groups × 200 resamples × 3 cutoffs ≈ 21,000 kh calculations (~10s)",
        "Optional via CLI: python -m src.cli sweep --bootstrap",
    ]
    add_bullets(slide, bullets, top=Inches(1.5), width=Inches(12.5))


def slide_B2_smoothing(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Backup: clustering smoothing rationale")
    add_horizontal_divider(slide)
    bullets = [
        "Problem: sample-level clustering produces 1-sample label flips",
        "Real geological units are continuous, metres-thick",
        " ",
        "Step 1 — rolling mode (window=11, ~2.2 m at 0.2 m sampling):",
        "  Each sample's label is the mode of itself and ±5 neighbours",
        " ",
        "Step 2 — absorb short runs (min_run_length=5):",
        "  Any uninterrupted run shorter than 5 samples (1 m)",
        "  is merged into the longer neighbouring run",
        " ",
        "Per-well processing — depth ordering doesn't cross well boundaries",
    ]
    add_bullets(slide, bullets, top=Inches(1.4), width=Inches(12.5), font_size=Pt(15))


def slide_B3_pooled(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Backup: why pooled clustering, not per-well")
    add_horizontal_divider(slide)
    bullets = [
        "Alternative: cluster each well independently, then 'match' labels",
        "Problem: KMeans 'cluster 0' in well 1 is unrelated to 'cluster 0' in well 2",
        "Matching requires Hungarian algorithm or similar — complex, brittle",
        " ",
        "Pooled approach: fit ONE model on all wells' Zone C samples",
        "Every sample gets a label in the same space",
        "Cluster ID = rock type, globally",
        " ",
        "Cross-well consistency tested via leave-one-well-out (ARI)",
        "Trade-off: assumes the same rock types exist in every well",
        "  – validated by the 0.97 LOWO ARI",
    ]
    add_bullets(slide, bullets, top=Inches(1.4), width=Inches(12.5), font_size=Pt(15))


def slide_B4_label_reorder(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Backup: stable label ordering via log_perm")
    add_horizontal_divider(slide)
    bullets = [
        "KMeans labels are arbitrary — re-running may swap labels",
        "Without reordering: 'sub-zone 2' could be tight in one run, best in next",
        " ",
        "Solution: after fitting, compute mean log_perm per cluster",
        "Relabel so cluster 0 = lowest mean log_perm, k-1 = highest",
        " ",
        "Guarantees: across runs, across LOWO folds, the same",
        "  cluster ID corresponds to the same rock type",
        " ",
        "Simpler than Hungarian-assignment matching",
        "Stable when features include log_perm (which they do)",
    ]
    add_bullets(slide, bullets, top=Inches(1.4), width=Inches(12.5), font_size=Pt(15))


def slide_B5_extensions(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(slide, "Backup: what I'd add with more data")
    add_horizontal_divider(slide)
    bullets = [
        "Core measurements at saturated depths:",
        "  – Calibrate the 15,000 mD cap → uncensored perm distribution",
        "  – Lab phit / vsh check → calibrate net cutoffs",
        " ",
        "Production data:",
        "  – Correlate kh estimates with measured production rates",
        "  – Validate sub-zone 2 as drilling target empirically",
        " ",
        "Seismic horizons:",
        "  – Geological correlation across wells",
        "  – Confirm sub-zone vertical stacking is geological, not statistical",
        " ",
        "Censored regression to recover real perm from (phit, vsh) in saturated samples",
    ]
    add_bullets(slide, bullets, top=Inches(1.4), width=Inches(12.5), font_size=Pt(14))


# =============================================================================
# Main
# =============================================================================

def main():
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slides_main = [
        slide_1_title,
        slide_2_qc_findings,
        slide_3_per_zone,
        slide_4_sensitivity,
        slide_5_lorenz,
        slide_6_well_ranking,
        slide_7_zone_d,
        slide_8_bootstrap,
        slide_9_clustering_choice,
        slide_10_zone_c_clusters,
        slide_11_drilling_target,
        slide_12_k_choice,
        slide_13_engineering,
        slide_14_summary,
    ]
    slides_backup = [
        slide_B1_bootstrap_detail,
        slide_B2_smoothing,
        slide_B3_pooled,
        slide_B4_label_reorder,
        slide_B5_extensions,
    ]
    all_slides = slides_main + slides_backup
    total = len(all_slides)

    for i, builder in enumerate(all_slides, start=1):
        builder(prs)
        # Add slide number to every slide except title
        if i > 1:
            add_slide_number(prs.slides[i - 1], i, total)

    out_dir = REPO / "presentation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "eigroup_reservoir_analytics.pptx"
    prs.save(str(out_path))
    print(f"Wrote {out_path}")
    print(f"  Main slides:   {len(slides_main)}")
    print(f"  Backup slides: {len(slides_backup)}")


if __name__ == "__main__":
    main()
