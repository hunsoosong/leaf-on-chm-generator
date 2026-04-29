import os
import glob
import numpy as np
import rasterio

from keras.models import Model
from tqdm import tqdm
from tensorflow.keras.models import load_model


# ============================
# Pix2Pix 모델 로드 함수
# ============================
def load_trained_pix2pix_model(model_path: str) -> Model:
    """
    학습된 Pix2Pix 모델을 로드합니다.
    Args:
        model_path (str): 모델 파일 경로 (.h5 파일)
    Returns:
        keras.models.Model: 로드된 Pix2Pix 모델
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = load_model(model_path)
    print(f"Pix2Pix Model loaded successfully from {model_path}")
    return model


# ============================
# Pix2Pix 예측 및 이미지 저장 함수
# ============================
def generate_and_save_pix2pix_images(
    model: Model, input_dir: str, output_dir: str
) -> None:
    """
    Pix2Pix 모델을 사용하여 이미지를 예측하고 저장합니다.
    Args:
        model: 로드된 Pix2Pix 모델
        input_dir (str): 입력 이미지 폴더 경로
        output_dir (str): 출력 이미지 폴더 경로
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    input_files = sorted(glob.glob(os.path.join(input_dir, "*.tif")))

    print("Running Pix2Pix predictions...")
    for input_file in tqdm(input_files):
        with rasterio.open(input_file) as src:
            img = src.read(1)
            img = np.expand_dims(img, axis=(0, -1))  # Add batch and channel dimensions
            img = (img - 40) / 40  # Normalize to match Pix2Pix training range

            # 예측 수행
            generated_img = model.predict(img)
            generated_img = np.squeeze(generated_img)
            generated_img = (generated_img * 40) + 40  # Denormalize

            profile = src.profile
            profile.update(dtype=rasterio.float32, count=1)

            output_file = os.path.join(output_dir, os.path.basename(input_file))
            with rasterio.open(output_file, "w", **profile) as dst:
                dst.write(generated_img.astype(rasterio.float32), 1)

    print(f"Generated images saved to: {output_dir}")
