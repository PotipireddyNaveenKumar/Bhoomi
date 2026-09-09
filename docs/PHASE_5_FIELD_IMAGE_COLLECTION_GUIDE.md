# BHOOMI V2 — Phase 5 Field Image Collection Guide

**Target Audience**: Krishi Vigyan Kendra (KVK) Extension Officers, Field Agronomists, Village Agricultural Assistants, Pilot Lead Farmers  
**Document Purpose**: Practical Field Guide for Capturing Realistic Smartphone Images for Real-World Computer Vision Evaluation  

---

## 1. Why Controlled Photography Must Be Avoided

When photographing plants for BHOOMI V2's Phase 5 Field Validation:
- **DO NOT pluck the leaf and place it on white paper, cardboard, or a clean desk**.
- **DO NOT shade the leaf with a studio umbrella or use artificial studio lights**.
- **DO NOT wipe the leaf clean with a cloth before taking the photo**.

The express objective of Phase 5 is to measure and harden BHOOMI against real on-farm conditions. If field scouts submit artificial laboratory-style images, the validation exercise becomes meaningless.

---

## 2. Practical Photography Recommendations

### A. Camera Distance & Framing (The Three Distance Tiers)

For every diseased plant identified in the field, capture three standard perspectives:

1. **Tier 1: Close-up / Macro (10–15 cm)**:
   - Focus sharply on the active lesion margin (where green healthy tissue meets diseased necrotic tissue).
   - Ensure individual lesion details (concentric rings, chlorotic halos, fungal sporulation) are resolved.
2. **Tier 2: Moderate Leaf Span (25–35 cm)**:
   - Capture the entire single leaf blade along with its petiole attached to the plant stem.
   - Shows the overall pattern of disease spread (apical curling, marginal necrosis, interveinal chlorosis).
3. **Tier 3: Canopy Context (50–80 cm)**:
   - Capture 3–5 neighboring leaves and the immediate stem/soil background.
   - Tests model robustness against background leaf clutter, soil, and drip lateral pipes.

### B. Natural Lighting Variations

Capture images across the full spectrum of natural Indian daylight conditions:
- **Morning Diffuse Light (07:00 – 09:30)**: High moisture, natural dew sheen, soft shadows.
- **Midday Direct Sun (11:30 – 14:00)**: Harsh overhead tropical sunlight, sharp shadows, high contrast.
- **Late Afternoon (16:00 – 17:30)**: Warm golden-hour illumination, elongated lateral shadows.
- **Overcast / Monsoon Days**: Diffuse, low-contrast illumination with wet leaf surfaces and raindrops.

### C. Natural Agricultural Backgrounds

Leave the leaf in its natural canopy setting:
- Allow bare soil, mulch straw, weed patches, drip lines, or wooden support stakes to remain in the background.
- Include photographs where neighboring leaves cast natural shadows across the target leaf.
- Include leaves naturally coated with fine red/black field dust or dried Bordeaux/copper spray residues.

### D. Device Heterogeneity

Use diverse real-world mobile devices commonly used by farmers:
- Budget Android smartphones ($< \text{INR } 10,000$ / Redmi 9A, Realme C11, Samsung M02).
- Mid-range devices (Redmi Note 12, Samsung Galaxy M34, Vivo Y20).
- Vary camera lens conditions (test with lightly fingerprinted camera glass to simulate realistic farmer phone handling).

---

## 3. What to Include in Every Submission

For every photo session, the field scout must record:
1. `image_id`: Pre-generated sequential tag (e.g. `FLD_TOM_001.jpg`).
2. `crop`: Target crop species.
3. `camera_device`: Phone model used (e.g. `Redmi_9A`).
4. `crop_stage`: Vegetative, flowering, fruiting, or maturity.
5. `lighting_condition`: Direct sunlight, diffuse daylight, overcast, or shaded.
6. `leaf_condition`: Fresh attached, dust coated, wet raindrops, or chemical residue.
7. `expert_label`: Primary disease identified by KVK specialist.
8. `annotation_state`: `CONFIRMED` (laboratory/definitive) or `PROBABLE`.

---

## 4. Submission Checklist for Field Teams

- [ ] Camera lens wiped of major mud, but natural field dust intact.
- [ ] Autofocus tapped directly on the diseased lesion area.
- [ ] Image resolution at least $1080 \times 1080$ (native camera capture without digital zoom).
- [ ] No farmer faces, vehicle license plates, or house address boards visible in background.
- [ ] Both healthy leaves and diseased leaves captured from the same plot to evaluate false alarm rates.
