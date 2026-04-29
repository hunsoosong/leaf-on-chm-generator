import glob
import os
import numpy as np
from typing import List, Tuple

import rasterio
from keras.models import Model
from tensorflow.keras.losses import MeanSquaredError
from tensorflow.keras.models import load_model
from tqdm import tqdm


def load_trained_model(model_path: str) -> Model:
    """
    load 5band unet model
    Args:
        model_path (str): model path (.h5)
    Returns:
        keras.models.Model: loaded model
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # model load (loss function MSE)
    custom_objects = {"mse": MeanSquaredError()}
    model = load_model(model_path, custom_objects=custom_objects)
    print(f"Model loaded successfully from {model_path}")
    return model


def load_test_images(chm_dir: str, naip_dir: str) -> Tuple[np.ndarray, List[str]]:
    """
    load CHM(1band), naip(4band) -> 5band input
    Args:
        chm_dir (str): CHM patch folder directory
        naip_dir (str): NAIP patch folder directory
    Returns:
        np.array: (N, H, W, 5) shape input data
        list: file name list
    """
    chm_files = sorted(glob.glob(chm_dir + "/*.tif"))
    naip_files = sorted(glob.glob(naip_dir + "/*.tif"))

    images = []
    file_names = []

    for chm_file, naip_file in zip(chm_files, naip_files):
        with rasterio.open(chm_file) as src_chm:
            chm_img = src_chm.read(1)  # (H, W)

        with rasterio.open(naip_file) as src_naip:
            naip_img = src_naip.read(list(range(2, 6)))  # (4, H, W)

        # CHM as first channel
        chm_img = np.expand_dims(chm_img, axis=0)  # (1, H, W)

        # CHM, NAIP concatenate
        combined_img = np.concatenate([chm_img, naip_img], axis=0)  # (5, H, W)

        images.append(combined_img)
        file_names.append(os.path.basename(chm_file))  # CHM saved as filename

    ndimages = np.array(images)  # (N, 5, H, W)
    ndimages = np.moveaxis(ndimages, 1, -1)  # (N, H, W, 5)

    print(f"Loaded {len(ndimages)} test images from {chm_dir} and {naip_dir}")
    return ndimages, file_names


def generate_and_save_images(
    model: Model,
    test_images: np.ndarray,
    file_names: List[str],
    input_dir: str,
    output_dir: str,
) -> None:
    """
    use 5band input to run model, save generated CHM
    Args:
        model: loaded unet model
        test_images (np.array): input image array (N, H, W, 5)
        file_names (list): input file name list
        input_dir (str): CHM patch folder directory
        output_dir (str): output image folder directory
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Running predictions...")
    generated_images = model.predict(test_images)

    for i, generated_img in enumerate(tqdm(generated_images)):
        output_file_path = os.path.join(output_dir, file_names[i])

        # copy input CHM patch metadata
        with rasterio.open(os.path.join(input_dir, file_names[i])) as src:
            profile = src.profile
            profile.update(dtype=rasterio.float32, count=1)

            # save generated CHM
            with rasterio.open(output_file_path, "w", **profile) as dst:
                dst.write(generated_img[:, :, 0], 1)

    print(f"Generated images saved to: {output_dir}")
