import os
from glob import glob
from math import ceil

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.windows import Window


# ============================
# NDHM generation function
# ============================
def generate_ndhm(dsm_file: str, dtm_file: str, output_ndhm_file: str) -> None:
    """
    DSM DTM used for NDHM (Normalized Digital Height Model)generation
    over 99.99th percentile becomes 0

    Args:
        dsm_file (str): DSM file directory
        dtm_file (str): DTM DSM file directory
        output_ndhm_file (str): output NDHM DSM file directory
    """
    with rasterio.open(dsm_file) as dsm, rasterio.open(dtm_file) as dtm:
        # DSM DTM read
        dsm_data = dsm.read(1)
        dtm_data = dtm.read(1)

        # NDHM generation
        ndhm_data = dsm_data - dtm_data
        ndhm_data[ndhm_data < 0] = 0  # negative value eliminated

        # 99.9th percentile calculation
        valid_ndhm_values = ndhm_data[ndhm_data > 0]  # only valid NDHM values used
        if valid_ndhm_values.size > 0:
            percentile_99_9 = np.percentile(valid_ndhm_values, 99.999)
            print(f"99.99th Percentile Height: {percentile_99_9}")

            # over 99.9th percentile becomes 0
            ndhm_data[ndhm_data > percentile_99_9] = 0
        else:
            print("No valid NDHM values found. Skipping percentile adjustment.")

        # output file saved
        profile = dsm.profile
        profile.update(dtype=rasterio.float32)

        with rasterio.open(output_ndhm_file, "w", **profile) as dst:
            dst.write(ndhm_data.astype(rasterio.float32), 1)

    print(f"NDHM generated with 99.99th percentile adjustment: {output_ndhm_file}")


# ============================
# patch split function (CHM & NAIP)
# ============================
def save_patches(
    image_path: str, output_dir: str, patch_size: int = 256, overlay: int = 0
) -> None:
    """
    patch split and saved
    Args:
        image_path (str): og image file directory
        output_dir (str): patch file directory
        patch_size (int): size of patch (default: 256)
        overlay (int): patch overlap (default: 0)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with rasterio.open(image_path) as src:
        height, width = src.height, src.width
        step = patch_size - overlay

        n_patches_height = ceil((height - overlay) / step)
        n_patches_width = ceil((width - overlay) / step)

        patch_id = 0
        for i in range(n_patches_height):
            for j in range(n_patches_width):
                row_start = i * step
                col_start = j * step
                if row_start + patch_size > height:
                    row_start = height - patch_size
                if col_start + patch_size > width:
                    col_start = width - patch_size

                window = Window(col_start, row_start, patch_size, patch_size)
                patch = src.read(1, window=window)

                patch_filename = f"patch_{patch_id}.tif"
                patch_filepath = os.path.join(output_dir, patch_filename)
                patch_transform = src.window_transform(window)  # ✅ patch transform

                profile = src.profile
                profile.update(
                    {
                        "height": patch_size,
                        "width": patch_size,
                        "count": 1,
                        "transform": patch_transform,  # ✅ individual patch transform applied
                    }
                )

                with rasterio.open(patch_filepath, "w", **profile) as dst:
                    dst.write(patch, 1)

                patch_id += 1
    print(f"Patches saved to: {output_dir}")


def save_combined_patches(
    chm_path: str,
    naip_path: str,
    output_dir: str,
    patch_size: int = 256,
    overlay: int = 0,
) -> None:
    """
    CHM(1band)과 NAIP(4band)image patch split and saved together
    saved into training data size (H, W, 5)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with rasterio.open(chm_path) as src_chm, rasterio.open(naip_path) as src_naip:
        height, width = src_chm.height, src_chm.width
        step = patch_size - overlay

        n_patches_height = ceil((height - overlay) / step)
        n_patches_width = ceil((width - overlay) / step)

        patch_id = 0
        for i in range(n_patches_height):
            for j in range(n_patches_width):
                row_start = i * step
                col_start = j * step
                if row_start + patch_size > height:
                    row_start = height - patch_size
                if col_start + patch_size > width:
                    col_start = width - patch_size

                window = Window(col_start, row_start, patch_size, patch_size)
                patch_transform = src_chm.window_transform(
                    window
                )  # ✅ patch transformaion

                # CHM (1band) patch
                chm_patch = src_chm.read(1, window=window)
                chm_patch = np.expand_dims(chm_patch, axis=-1)  # (H, W, 1)

                # NAIP (4band) patch
                naip_patch = np.moveaxis(
                    src_naip.read(list(range(1, 5)), window=window), 0, -1
                )  # (H, W, 4)

                # CHM + NAIP concatenated
                combined_patch = np.concatenate(
                    [chm_patch, naip_patch], axis=-1
                )  # (H, W, 5)

                patch_filename = f"patch_{patch_id}.tif"
                patch_filepath = os.path.join(output_dir, patch_filename)

                profile = src_chm.profile
                profile.update(
                    {
                        "count": 5,  # 5channel input (1band CHM + 4band NAIP)
                        "height": patch_size,
                        "width": patch_size,
                        "dtype": rasterio.float32,
                        "transform": patch_transform,
                        "nodata": None,  # Nodata value eliminated
                    }
                )

                with rasterio.open(patch_filepath, "w", **profile) as dst:
                    dst.write(
                        np.moveaxis(combined_patch, -1, 0)
                    )  # ✅ (H, W, 5) → (5, H, W) saved

                patch_id += 1

    print(f"✅ Combined patches saved to: {output_dir} (Stored in (H, W, 5) format)")


# ============================
# patch merge function
# ============================
def merge_patches(patch_dir: str, merged_image_path: str) -> None:
    """
    patch file merge and save
    Args:
        patch_dir (str): patch file directory
        merged_image_path (str): merged image file path
    """
    patch_files = glob(os.path.join(patch_dir, "*.tif"))
    if len(patch_files) == 0:
        raise FileNotFoundError("No patch files found in the specified directory.")

    datasets = [rasterio.open(patch) for patch in patch_files]
    merged_array, merged_transform = merge(datasets)

    out_meta = datasets[0].meta.copy()
    out_meta.update(
        {
            "height": merged_array.shape[1],
            "width": merged_array.shape[2],
            "transform": merged_transform,
        }
    )

    with rasterio.open(merged_image_path, "w", **out_meta) as dst:
        dst.write(merged_array)

    for dataset in datasets:
        dataset.close()

    print(f"Merged image saved to: {merged_image_path}")


# ============================
# (to match 1m chm resolution)
# ============================


def resample_to_reference(
    source_path: str,
    reference_path: str,
    output_path: str,
    resample_method: str = "bilinear",
) -> None:
    """
    source_path의 raster 파일을 reference_path의 해상도, 좌표계, 크기에 맞게 리샘플링하여 output_path에 저장합니다.

    Args:
        source_path (str): 리샘플링할 원본 파일 경로
        reference_path (str): 기준이 되는 파일 경로 (해상도, 좌표계, 크기 참조)
        output_path (str): 리샘플링된 파일을 저장할 경로
        resample_method (str): 리샘플링 방식 (예: 'nearest', 'bilinear', 'cubic')
    """
    # choose resampling method
    resampling_methods = {
        "nearest": Resampling.nearest,
        "bilinear": Resampling.bilinear,
        "cubic": Resampling.cubic,
        "lanczos": Resampling.lanczos,
        "average": Resampling.average,
        "mode": Resampling.mode,
    }
    resampling_enum = resampling_methods.get(resample_method, Resampling.bilinear)

    # reference file metadata
    with rasterio.open(reference_path) as ref:
        dst_transform = ref.transform
        dst_crs = ref.crs
        dst_width = ref.width
        dst_height = ref.height

    # open reference file and resample
    with rasterio.open(source_path) as src:
        src_data = src.read(1)
        src_transform = src.transform
        src_crs = src.crs

        # profile generation using ref metadata
        profile = src.profile.copy()
        profile.update(
            {
                "crs": dst_crs,
                "transform": dst_transform,
                "width": dst_width,
                "height": dst_height,
            }
        )

        # save resampled result
        dst_data = np.empty((dst_height, dst_width), dtype=src_data.dtype)

        reproject(
            source=src_data,
            destination=dst_data,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=resampling_enum,
        )

    # save resampled result
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(dst_data, 1)

    print(f"Resampled file saved to: {output_path}")


# ============================
# remove buildings from final output using 3d building raster
# ============================
def remove_buildings_from_final(
    final_output_path: str, building_mask_path: str, output_path: str
) -> None:
    """
    Replace pixels in the final output image with 0 where the building mask equals 1,
    and save the resulting image (with building information removed) to output_path.

    Args:
        final_output_path (str): File path of the original final output image.
        building_mask_path (str): File path of the resampled 2D building mask image (buildings=1, ground=0).
        output_path (str): File path to save the final output image with buildings removed.
    """
    # Read the final output file
    with rasterio.open(final_output_path) as final_ds:
        final_data = final_ds.read(1)
        profile = final_ds.profile

    # Read the building mask file
    with rasterio.open(building_mask_path) as mask_ds:
        mask_data = mask_ds.read(1)

    # Replace pixels with value 1 in the building mask with 0 in the final output image
    final_data_no_building = final_data.copy()
    final_data_no_building[mask_data == 1] = 0

    # Save the result
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(final_data_no_building, 1)

    print(f"Final output with buildings removed saved to: {output_path}")


def remove_buildings_from_final2(
    final_output_path: str,
    building_mask_path: str,
    building_3d_path: str,
    output_path: str,
    tolerance: float = 2.0,
) -> None:
    """
    In the NDHM (final output) image, for areas where the 2D building mask equals 1,
    replace pixels with 0 only if the difference between the NDHM value and the 3D building map value
    is within the specified tolerance (e.g., 1m). Save the resulting image to output_path.

    Args:
        final_output_path (str): File path of the original NDHM/CHM image.
        building_mask_path (str): File path of the resampled 2D building mask image (buildings=1, ground=0).
        building_3d_path (str): File path of the 3D building map image.
        output_path (str): File path to save the final output image with buildings removed.
        tolerance (float): Tolerance value (in meters). If the difference between NDHM and the 3D building map
                           is within this value, the pixel is considered a building.
    """
    # Read the NDHM (final output) image
    with rasterio.open(final_output_path) as ndhm_ds:
        ndhm_data = ndhm_ds.read(1)
        profile = ndhm_ds.profile

    # Read the 2D building mask image
    with rasterio.open(building_mask_path) as mask_ds:
        mask_data = mask_ds.read(1)

    # Read the 3D building map image
    with rasterio.open(building_3d_path) as b3d_ds:
        b3d_data = b3d_ds.read(1)

    # Remove buildings from NDHM:
    # For pixels where the building mask is 1 and the difference (NDHM - 3D) is within the tolerance,
    # set the pixel value to 0.
    ndhm_no_building = ndhm_data.copy()
    removal_condition = (mask_data == 1) & ((ndhm_data - b3d_data) <= tolerance)
    ndhm_no_building[removal_condition] = 0

    # save results
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(ndhm_no_building, 1)

    print(f"Final output with refined building removal saved to: {output_path}")
