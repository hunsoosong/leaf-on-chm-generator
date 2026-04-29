import os
from glob import glob
from math import ceil

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import Window
from rasterio.warp import reproject, Resampling


# ============================
# NDHM 생성 함수
# ============================
def generate_ndhm(dsm_file: str, dtm_file: str, output_ndhm_file: str) -> None:
    """
    DSM과 DTM을 사용하여 NDHM (Normalized Digital Height Model)을 생성합니다.
    99.99th 백분위수를 초과하는 값은 0으로 설정합니다.

    Args:
        dsm_file (str): DSM 파일 경로
        dtm_file (str): DTM 파일 경로
        output_ndhm_file (str): 출력 NDHM 파일 경로
    """
    with rasterio.open(dsm_file) as dsm, rasterio.open(dtm_file) as dtm:
        # DSM과 DTM 데이터를 읽어옴
        dsm_data = dsm.read(1)
        dtm_data = dtm.read(1)

        # NDHM 생성
        ndhm_data = dsm_data - dtm_data
        ndhm_data[ndhm_data < 0] = 0  # 음수 값 제거

        # 99.9th 백분위수 계산
        valid_ndhm_values = ndhm_data[ndhm_data > 0]  # 유효한 NDHM 값만 사용
        if valid_ndhm_values.size > 0:
            percentile_99_9 = np.percentile(valid_ndhm_values, 99.999)
            print(f"99.99th Percentile Height: {percentile_99_9}")

            # 99.9th 백분위수 초과 값 0으로 설정
            ndhm_data[ndhm_data > percentile_99_9] = 0
        else:
            print("No valid NDHM values found. Skipping percentile adjustment.")

        # 출력 파일 저장
        profile = dsm.profile
        profile.update(dtype=rasterio.float32)

        with rasterio.open(output_ndhm_file, "w", **profile) as dst:
            dst.write(ndhm_data.astype(rasterio.float32), 1)

    print(f"NDHM generated with 99.99th percentile adjustment: {output_ndhm_file}")


# ============================
# 패치 분할 함수
# ============================
def save_patches(
    image_path: str, output_dir: str, patch_size: int = 256, overlay: int = 0
) -> None:
    """
    이미지를 작은 패치로 분할하고 저장합니다.
    Args:
        image_path (str): 원본 이미지 파일 경로
        output_dir (str): 패치를 저장할 폴더 경로
        patch_size (int): 각 패치의 크기
        overlay (int): 패치 간 오버랩 크기
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
                patch_transform = src.window_transform(window)

                profile = src.profile
                profile.update(
                    {
                        "height": patch_size,
                        "width": patch_size,
                        "count": 1,
                        "transform": patch_transform,
                    }
                )

                with rasterio.open(patch_filepath, "w", **profile) as dst:
                    dst.write(patch, 1)

                patch_id += 1
    print(f"Patches saved to: {output_dir}")


# ============================
# 패치 병합 함수
# ============================
def merge_patches(patch_dir: str, merged_image_path: str) -> None:
    """
    패치 파일들을 병합하여 하나의 이미지로 저장합니다.
    Args:
        patch_dir (str): 패치가 저장된 폴더 경로
        merged_image_path (str): 병합된 이미지를 저장할 경로
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
# 좌표 시스템 업데이트 함수
# ============================
def update_coordinate_system(src_dir: str, gen_dir: str, updated_gen_dir: str) -> None:
    """
    Source 패치의 좌표 시스템을 Generated 패치에 적용합니다.
    Args:
        src_dir (str): Source 패치 폴더 경로
        gen_dir (str): Generated 패치 폴더 경로
        updated_gen_dir (str): 좌표가 업데이트된 패치를 저장할 폴더 경로
    """
    if not os.path.exists(updated_gen_dir):
        os.makedirs(updated_gen_dir)

    src_patches = sorted(glob(os.path.join(src_dir, "*.tif")))
    gen_patches = sorted(glob(os.path.join(gen_dir, "*.tif")))

    if len(src_patches) != len(gen_patches):
        raise ValueError("The number of src and gen patches must be equal.")

    for src_patch, gen_patch in zip(src_patches, gen_patches):
        with rasterio.open(src_patch) as src_ds:
            src_transform = src_ds.transform
            src_crs = src_ds.crs
            profile = src_ds.profile

        with rasterio.open(gen_patch) as gen_ds:
            gen_data = gen_ds.read(1)

        profile.update({"transform": src_transform, "crs": src_crs})

        updated_gen_patch_path = os.path.join(
            updated_gen_dir, os.path.basename(gen_patch)
        )
        with rasterio.open(updated_gen_patch_path, "w", **profile) as dst:
            dst.write(gen_data, 1)
    print(f"Coordinate system updated patches saved to: {updated_gen_dir}")


def resample_to_reference(
    source_path, reference_path, output_path, resample_method="bilinear"
):
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
def remove_buildings_from_final(final_output_path, building_mask_path, output_path):
    """
    Replace pixels in the final output image with 0 where the building mask equals 1,
    and save the resulting image (with building information removed) to output_path.

    Args:
        final_output_path (str): File path of the original final output image.
        building_mask_path (str): File path of the resampled 2D building mask image (buildings=1, ground=0).
        output_path (str): File path to save the final output image with buildings removed.
    """
    import rasterio

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
    final_output_path, building_mask_path, building_3d_path, output_path, tolerance=2.0
):
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
    import rasterio
    import numpy as np

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
