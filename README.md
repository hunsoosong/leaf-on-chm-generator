# Leaf-on CHM Generator

This repository contains the source code for the **Leaf-on Canopy Height Model (CHM) Generator** web application, the Pix2Pix and U-Net model architectures, and the inference pipeline supporting the manuscript:

> Kim, Y., Song, H., Fei, S., & Jung, J. (2026). *Transforming Leaf-off LiDAR to Leaf-on Canopy Height Models Using Deep Learning.* GIScience & Remote Sensing.

The deployed web application is available at:

**https://log.d2s.org**

The source code and supporting materials are archived on Zenodo:

**https://doi.org/10.5281/zenodo.19876738**

The trained model weights used in the study are publicly available through GitHub Release v1.1.0:

**https://github.com/hunsoosong/leaf-on-chm-generator/releases/tag/v1.1.0**

## Citation

If you use this software, model architecture, trained model weights, or web application in your research, please cite both the manuscript and the archived materials:

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
  doi       = {10.5281/zenodo.19876738},
  url       = {https://doi.org/10.5281/zenodo.19876738}
}
```

## What this repository contains

| Component | Path or location | Description |
|---|---|---|
| Frontend | `frontend/` | React + Vite + TypeScript web client for area-of-interest selection, dataset visualization, and result download. |
| Backend | `backend/app/` | FastAPI server handling requests, inference orchestration, and Celery-based task management. |
| LiDAR-only inference pipeline | `backend/app/ml/lidar/` | DTM/DSM generation from 3DEP EPT, NDHM derivation, patch-based Pix2Pix inference, and building artifact removal. |
| LiDAR + NAIP inference pipeline | `backend/app/ml/lidar_and_naip/` | U-Net inference using a LiDAR-derived CHM and NAIP multispectral imagery. |
| Building raster utilities | `backend/app/ml/building_raster.py` | Building-footprint processing used to remove building structures from canopy outputs. |
| Reverse proxy | `proxy/` | Nginx configuration for development and production deployment. |
| Container orchestration | `docker-compose.yml`, `docker-compose.prod.yml` | Service definitions for local and production deployment. |
| Trained model weights | [GitHub Release v1.1.0](https://github.com/hunsoosong/leaf-on-chm-generator/releases/tag/v1.1.0) | Publicly downloadable Pix2Pix and U-Net model weights used in the study. |

## Trained model weights

The trained model weights used in the study are openly available through GitHub Release v1.1.0 under the Creative Commons Attribution 4.0 International License (CC BY 4.0):

**https://github.com/hunsoosong/leaf-on-chm-generator/releases/tag/v1.1.0**

The release includes:

- `pix2pix.h5`: trained weights for the CHM-only Pix2Pix model
- `unet.h5`: trained weights for the CHM + NAIP U-Net model

The files are publicly downloadable without login or access approval.

For local execution, the current inference pipeline expects the following filenames in `backend/app/ml/`:

| Downloaded file | Local filename expected by the pipeline |
|---|---|
| `pix2pix.h5` | `test_oct2_.h5` |
| `unet.h5` | `best_naip_unet_model.h5` |

After downloading, place the files in `backend/app/ml/` and rename them as indicated above.

## Model details

The training procedure, dataset splits, and evaluation methodology are described in full in the manuscript. Briefly:

- **Inputs:** USGS 3DEP leaf-off airborne LiDAR. The U-Net configuration additionally uses USDA NAIP four-band multispectral imagery.
- **Reference:** NEON leaf-on airborne LiDAR.
- **Patch size:** 256 m × 256 m at 1 m spatial resolution.
- **Pix2Pix, CHM-only:** U-Net generator with a PatchGAN discriminator; adversarial loss plus 100 × L1 loss; Adam optimizer; learning rate = 0.001; batch size = 1; maximum 100 epochs; validation-selected epoch = 31.
- **U-Net, CHM + NAIP:** Encoder depth of 4; MSE loss; Adam optimizer; learning rate = 0.0001; batch size = 8; maximum 200 epochs; validation-selected epoch = 113.
- **Training data:** 2,907 non-overlapping patches from seven sites across three U.S. states.
- **Test data:** 744 non-overlapping patches from four independent test sites across two U.S. states.

## Running locally with Docker Compose

1. Download the trained model weights from GitHub Release v1.1.0:

   **https://github.com/hunsoosong/leaf-on-chm-generator/releases/tag/v1.1.0**

   Place the files in `backend/app/ml/` using the following filenames:

   - `pix2pix.h5` → `test_oct2_.h5`
   - `unet.h5` → `best_naip_unet_model.h5`

2. Copy `.backend.env.example` to `.backend.env` and configure:

   - `AOI_AREA_LIMIT`: maximum allowable user-drawn area in square meters
   - `SECRET_KEY`: a unique and secure secret key

3. Copy `frontend/.env.development.example` to `frontend/.env.development` and configure:

   - `VITE_AOI_AREA_LIMIT`: should match the backend value
   - `VITE_MAPBOX_ACCESS_TOKEN`: a Mapbox access token for displaying the basemap

4. Build and start the services from the repository root:

   ```bash
   docker compose build
   docker compose up -d
   ```

5. Access the application at:

   ```text
   http://localhost:8001
   ```

6. Stop the services with:

   ```bash
   docker compose down
   ```

## Public data sources used in this study

- **Leaf-off airborne LiDAR:** USGS 3D Elevation Program (3DEP)  
  https://www.usgs.gov/3d-elevation-program

- **Leaf-on airborne LiDAR:** National Ecological Observatory Network (NEON)  
  https://www.neonscience.org/

- **Multispectral imagery:** USDA National Agriculture Imagery Program (NAIP)  
  https://naip-usdaonline.hub.arcgis.com/

## License

The source code, documentation, trained model weights, and supporting materials made available through this repository are licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0).

The public input datasets used by the pipeline, including 3DEP, NEON, and NAIP data, remain subject to the terms and policies of their respective data providers.

## Acknowledgements

Funding for this project was provided by the USDA National Institute of Food and Agriculture (NIFA) under Award No. 2023-68012-38992, the Natural Resources Conservation Service (NRCS) under Award No. NR233A750004G044, and the National Research Foundation of Korea (NRF) grants funded by the Korean government (MSIT) (Award Nos. RS-2025-24803224 and RS-2026-25499133).
