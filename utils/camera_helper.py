# utils/camera_helper.py
"""
Camera helper functions.

Handles Raspberry Pi camera-specific configuration.
"""

import cv2
from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, DEBUG

def open_camera(index=None, width=None, height=None):
    """
    Open a camera (Raspberry Pi friendly).
    
    Args:
        index: Camera index. Defaults to CAMERA_INDEX.
        width: Frame width. Defaults to CAMERA_WIDTH.
        height: Frame height. Defaults to CAMERA_HEIGHT.
    
    Returns:
        A cv2.VideoCapture instance, or None on failure.
    """
    if index is None:
        index = CAMERA_INDEX
    if width is None:
        width = CAMERA_WIDTH
    if height is None:
        height = CAMERA_HEIGHT
    
    if DEBUG:
        print(f"Opening camera {index}...")
    
    # Method 1: V4L2 + MJPEG (recommended on Raspberry Pi)
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        
        # Set MJPEG format
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        # Reduce internal buffering to minimize latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Probe a frame
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                if DEBUG:
                    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"Camera opened successfully (V4L2+MJPEG): {actual_w}x{actual_h}")
                return cap
        
        cap.release()
    except Exception as e:
        if DEBUG:
            print(f"V4L2+MJPEG method failed: {e}")
    
    # Method 2: Default backend
    try:
        cap = cv2.VideoCapture(index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                if DEBUG:
                    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"Camera opened successfully (default backend): {actual_w}x{actual_h}")
                return cap
        
        cap.release()
    except Exception as e:
        if DEBUG:
            print(f"Default backend method failed: {e}")
    
    if DEBUG:
        print("Unable to open camera")
    return None
