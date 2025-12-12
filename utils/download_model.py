# utils/download_model.py
"""
Downloader for YuNet and SFace models.
"""

import os
import urllib.request
import sys

# Model download URLs (OpenCV official)
MODEL_URLS = {
    "yunet": {
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "path": "../models/face_detection_yunet_2023mar.onnx",
        "size": "~300KB"
    },
    "sface": {
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "path": "../models/face_recognition_sface_2021dec.onnx",
        "size": "~40MB"
    }
}

def download_file(url, save_path):
    """Download a file."""
    print(f"\nDownloading: {url}")
    print(f"Saving to: {save_path}")
    
    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(downloaded / total_size * 100, 100)
                mb_downloaded = downloaded / 1024 / 1024
                mb_total = total_size / 1024 / 1024
                print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.2f}/{mb_total:.2f} MB)", end='')
            else:
                print(f"\r  Downloaded: {downloaded/1024/1024:.2f} MB", end='')
        
        urllib.request.urlretrieve(url, save_path, progress)
        print()  # Newline
        
        # Basic sanity check on file size
        file_size = os.path.getsize(save_path) / 1024 / 1024
        if file_size < 0.1:
            print("Unexpected file size")
            return False
        
        print(f"Download complete! File size: {file_size:.2f} MB")
        return True
        
    except Exception as e:
        print(f"\nDownload failed: {e}")
        return False

def download_models():
    """Download all required models."""
    print("="*60)
    print("YuNet + SFace Model Downloader")
    print("="*60)
    
    # Ensure output directory exists
    os.makedirs("../models", exist_ok=True)
    
    success_count = 0
    
    for model_name, info in MODEL_URLS.items():
        print(f"\n{'='*60}")
        print(f"Model: {model_name.upper()}")
        print(f"Expected size: {info['size']}")
        print(f"{'='*60}")
        
        # Skip download if the model already exists (unless overwrite is requested)
        if os.path.exists(info['path']):
            file_size = os.path.getsize(info['path']) / 1024 / 1024
            print("Model already exists")
            print(f"  Path: {info['path']}")
            print(f"  Size: {file_size:.2f} MB")
            
            overwrite = input("\nRe-download? (y/n): ").strip().lower()
            if overwrite != 'y':
                print("Keeping existing model")
                success_count += 1
                continue
        
        # Download
        if download_file(info['url'], info['path']):
            success_count += 1
    
    # Summary
    print("\n" + "="*60)
    if success_count == len(MODEL_URLS):
        print("All models are ready!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run: python face_register.py  # Register faces")
        print("2. Run: python face_test.py      # Test recognition")
        print("3. Run: python main.py           # Full system")
        return True
    else:
        print(f"Some model downloads failed ({success_count}/{len(MODEL_URLS)})")
        print("="*60)
        print("\nManual download:")
        print("1. Visit: https://github.com/opencv/opencv_zoo")
        print("2. Open the target model folder")
        print("3. Download the .onnx file")
        print("4. Put it into the models/ directory")
        return False

if __name__ == "__main__":
    success = download_models()
    sys.exit(0 if success else 1)