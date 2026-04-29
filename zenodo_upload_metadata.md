# Zenodo upload — metadata to fill in

This file contains the values to paste into the Zenodo upload form. After
publishing, replace `10.5281/zenodo.xxxxxxx` placeholders in `README.md`,
`CITATION.cff`, `data_availability_statement.tex`, and `cas-refs.bib` with
the final assigned DOI.

---

## Resource type
**Software**

## Title
Source code and supporting materials for "Transforming Leaf-off LiDAR to Leaf-on Canopy Height Models Using Deep Learning"

## Creators (in this order)
1. Kim, Yeonjae — Lyles School of Civil Engineering, Purdue University
2. Song, Hunsoo — Department of Civil Engineering, Chungbuk National University (ORCID if available)
3. Fei, Songlin — Department of Forestry & Natural Resources, Purdue University
4. Jung, Jinha — Lyles School of Civil Engineering, Purdue University

## Description (paste into Zenodo description box)

This Zenodo record archives the source code, deep learning model architectures, and inference pipeline supporting the manuscript:

**Kim, Y., Song, H., Fei, S., & Jung, J. (2026). Transforming Leaf-off LiDAR to Leaf-on Canopy Height Models Using Deep Learning. *GIScience & Remote Sensing*.**

The archive contains the complete source code for the interactive *Leaf-on CHM Generator* web application (https://log.d2s.org), including:

- Frontend (React + Vite + TypeScript) for area-of-interest selection, dataset visualization, and result download.
- Backend (FastAPI + Celery) handling task orchestration and inference dispatch.
- Inference pipeline implementing the two deep learning configurations described in the manuscript:
  - **Pix2Pix GAN (CHM-only):** transforms leaf-off LiDAR-derived canopy height models into leaf-on CHMs.
  - **U-Net (CHM + NAIP):** integrates leaf-off LiDAR with NAIP multispectral imagery for enhanced canopy height estimation.
- LiDAR processing pipeline (PDAL-based) for DTM/DSM generation, NDHM derivation, patch tiling, and building artifact removal.
- Reverse proxy and Docker Compose orchestration for development and production deployment.

Trained model weights are not included in this archive; they are accessible through the deployed web application at https://log.d2s.org and can be obtained from the corresponding author for academic, non-commercial reproducibility purposes.

The original development repository is hosted at https://github.com/gdslab/leaf-on-generator. This archived snapshot is maintained at https://github.com/hunsoosong/leaf-on-chm-generator for citation stability.

**Public input data sources used in the study:**
- USGS 3D Elevation Program (3DEP)
- National Ecological Observatory Network (NEON)
- USDA National Agriculture Imagery Program (NAIP)

## Keywords
canopy height model; airborne LiDAR; deep learning; Pix2Pix; U-Net; leaf-off; leaf-on; 3DEP; NEON; NAIP; remote sensing; forest structure

## License
**MIT License** (matches the LICENSE file in the repository)

## Funding (Zenodo "Funding" section, optional but recommended)
- USDA National Institute of Food and Agriculture (NIFA) — Award No. 2023-68012-38992
- Natural Resources Conservation Service (NRCS) — Award No. NR233A750004G044
- National Research Foundation of Korea (NRF) — Award No. RS-2026-25499133

## Related identifiers
- **isSupplementTo** — the manuscript DOI (add once the article is accepted and assigned a DOI)
- **isDerivedFrom** — https://github.com/gdslab/leaf-on-generator (URL)

## Version
1.0.0

## Publication date
(date of Zenodo publish)

---

## Upload contents (the actual ZIP)

Recommended structure for the ZIP you upload:

```
leaf-on-chm-generator-v1.0.0/
├── LICENSE
├── README.md
├── CITATION.cff
├── docker-compose.yml
├── docker-compose.prod.yml
├── .backend.env.example
├── backend/
├── frontend/
└── proxy/
```

i.e. the entire repository minus `.git/`, `node_modules/`, `__pycache__/`,
local `.env` files with real secrets, and any large binary you don't want
to ship.

**Pre-flight check before zipping:**
- [ ] No real `.env` files (only `.example` ones)
- [ ] No real Mapbox tokens, API keys, SECRET_KEY values
- [ ] `LICENSE` present
- [ ] `README.md` updated (paper info, citation, data sources)
- [ ] `CITATION.cff` present
- [ ] `.git/` excluded (or use `git archive HEAD --format=zip -o leaf-on-chm-generator-v1.0.0.zip`)

---

## After publishing

1. Copy the assigned DOI (e.g. `10.5281/zenodo.12345678`).
2. Replace `10.5281/zenodo.xxxxxxx` in:
   - `README.md` (two places)
   - `CITATION.cff` (one place)
   - `data_availability_statement.tex` (one place)
   - `cas-refs.bib` (the new `@misc{kim2026leafonchmcode, ...}` entry)
3. Update the GitHub repo with the final README/CITATION.cff containing the DOI.
4. Resubmit the manuscript through the T&F Author Submission Portal.
