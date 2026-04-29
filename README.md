# Leaf-on CHM Generator

This repository contains the source code of the **Leaf-on Canopy Height Model (CHM) Generator** web application, the deep learning model architectures (Pix2Pix and U-Net), and the inference pipeline supporting the manuscript:

> Kim, Y., Song, H., Fei, S., & Jung, J. (2026). *Transforming Leaf-off LiDAR to Leaf-on Canopy Height Models Using Deep Learning.* GIScience & Remote Sensing.

The deployed web application is available at: **https://log.d2s.org**

This repository is archived on Zenodo with DOI: **[10.5281/zenodo.xxxxxxx](https://doi.org/10.5281/zenodo.xxxxxxx)** *(replace with the final DOI after publishing the Zenodo record)*

> Note: This repository is a snapshot maintained for archival and reproducibility purposes. The original development repository is at <https://github.com/gdslab/leaf-on-generator>.

## Citation

If you use this software, model architecture, or web application in your research, please cite both the manuscript and the archive:

```bibtex
@article{kim2026leafonchm,
  title   = {Transforming Leaf-off LiDAR to Leaf-on Canopy Height Models Using Deep Learning},
  author  = {Kim, Yeonjae and Song, Hunsoo and Fei, Songlin and Jung, Jinha},
  journal = {GIScience \& Remote Sensing},
  year    = {2026}
}

@misc{kim2026leafonchmcode,
  title     = {Source code and supporting materials for ``Transforming Leaf-off LiDAR to Leaf-on Canopy Height Models Using Deep Learning''},
  author    = {Kim, Yeonjae and Song, Hunsoo and Fei, Songlin and Jung, Jinha},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.xxxxxxx}
}
```

## What this repository contains

| Component | Path | Description |
|---|---|---|
| Frontend | `frontend/` | React + Vite + TypeScript web client. AOI selection, dataset visualization, result download. |
| Backend | `backend/app/` | FastAPI server. Handles requests, orchestrates the inference pipeline, manages tasks via Celery. |
| Inference pipeline (LiDAR-only, Pix2Pix) | `backend/app/ml/lidar/` | DTM/DSM generation from 3DEP EPT, NDHM derivation, patch-based Pix2Pix inference, building artifact removal. |
| Inference pipeline (LiDAR + NAIP, U-Net) | `backend/app/ml/lidar_and_naip/` | Combined pipeline using LiDAR-derived CHM and NAIP multispectral imagery. |
| Building raster utilities | `backend/app/ml/building_raster.py` | Building footprint extraction used to remove building structures from canopy outputs. |
| Reverse proxy | `proxy/` | Nginx configuration for development and production. |
| Container orchestration | `docker-compose.yml`, `docker-compose.prod.yml` | Service definitions for local and production deployment. |

## Trained model weights

Trained weights are **not bundled in this repository**. They are accessible through the deployed web application at <https://log.d2s.org>, which exposes the pre-trained Pix2Pix and U-Net models for on-demand leaf-on CHM generation across the United States.

For local execution, the inference pipeline expects the following weight files in `backend/app/ml/`:

- `test_oct2_.h5` — Pix2Pix generator trained on leaf-off CHM → leaf-on CHM (LiDAR-only)
- `best_naip_unet_model.h5` — U-Net trained on (leaf-off CHM + NAIP imagery) → leaf-on CHM

Please contact the corresponding author (`hunsoo.song@cbnu.ac.kr`) for access to the trained weights for academic, non-commercial reproducibility purposes.

## Model details (summary)

The training procedure, dataset splits, and evaluation methodology are described in full in the manuscript. Briefly:

- **Inputs:** USGS 3DEP leaf-off airborne LiDAR (Quality Level 2). Optional: USDA NAIP 4-band multispectral imagery (RGB + NIR).
- **Reference:** NEON leaf-on airborne LiDAR.
- **Patch size:** 256 m × 256 m at 1 m resolution.
- **Pix2Pix (CHM-only):** U-Net generator + PatchGAN discriminator. L1 + adversarial loss. ADAM, lr = 0.001, batch size = 1, 100 epochs.
- **U-Net (CHM + NAIP):** Encoder depth 4. MSE loss. ADAM, lr = 0.001, batch size = 16, 100 epochs.
- **Training data:** 2,907 non-overlapping patches from 7 sites across 3 U.S. states.
- **Test data:** 744 non-overlapping patches from 4 independent sites across 2 U.S. states.

## Running locally with Docker Compose

1. Place the trained weights in `backend/app/ml/`:
   - `test_oct2_.h5`
   - `best_naip_unet_model.h5`

2. Copy `.backend.env.example` to `.backend.env` and configure:
   - `AOI_AREA_LIMIT` (integer): maximum allowable user-drawn area in square meters.
   - `SECRET_KEY` (string): your own unique, strong secret key.

3. Copy `frontend/.env.development.example` to `frontend/.env.development` and configure:
   - `VITE_AOI_AREA_LIMIT` (integer): should match the backend value.
   - `VITE_MAPBOX_ACCESS_TOKEN` (string): your Mapbox access token for displaying the basemap.

4. Build and start the services from the repository root:
   ```bash
   docker compose build
   docker compose up -d
   ```

5. Access the application at `http://localhost:8001`.

6. Stop with:
   ```bash
   docker compose down
   ```

## Public data sources used in this study

- **Leaf-off airborne LiDAR:** USGS 3D Elevation Program (3DEP) — https://www.usgs.gov/3d-elevation-program
- **Leaf-on airborne LiDAR:** National Ecological Observatory Network (NEON) — https://www.neonscience.org/
- **Multispectral imagery:** USDA National Agriculture Imagery Program (NAIP) — https://naip-usdaonline.hub.arcgis.com/

## License

This software is released under the MIT License. See [`LICENSE`](LICENSE).

The inputs to and outputs from the deep learning pipeline are derived from publicly available data sources (3DEP, NEON, NAIP), each governed by its own usage terms.

## Acknowledgements

Funding for this project was provided by the USDA National Institute of Food and Agriculture (NIFA) (Award No. 2023-68012-38992), the Natural Resources Conservation Service (NRCS) (Award No. NR233A750004G044), and the National Research Foundation of Korea (NRF) grant funded by the Korean government (MSIT) (Award No. RS-2026-25499133).
