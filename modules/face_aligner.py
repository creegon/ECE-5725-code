# modules/face_aligner.py

import cv2
import numpy as np
from config import *

class FaceAligner:
    def __init__(self):
        # Standard landmark positions (112x112 image)
        # These are the canonical locations expected by the SFace model
        self.standard_landmarks = np.array([
            [38.2946, 51.6963],  # right eye
            [73.5318, 51.5014],  # left eye
            [56.0252, 71.7366],  # nose tip
            [41.5493, 92.3655],  # right mouth corner
            [70.7299, 92.2041]   # left mouth corner
        ], dtype=np.float32)
        
        if DEBUG:
            print("Face aligner initialized")
    
    def align(self, face_img, landmarks, target_size=SFACE_INPUT_SIZE):
        # Convert landmarks to float32
        src_landmarks = np.array(landmarks, dtype=np.float32)
        
        # Compute affine transform matrix
        # Use a similarity transform (rotation/scale/translation only)
        transform_matrix = cv2.estimateAffinePartial2D(
            src_landmarks,
            self.standard_landmarks
        )[0]
        
        # Apply affine transform
        aligned = cv2.warpAffine(
            face_img,
            transform_matrix,
            target_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0
        )
        
        return aligned
    
    def align_from_detection(self, frame, face, target_size=SFACE_INPUT_SIZE):
        landmarks = face['landmarks']
        
        # Compute affine transform matrix
        src_landmarks = np.array(landmarks, dtype=np.float32)
        transform_matrix = cv2.estimateAffinePartial2D(
            src_landmarks,
            self.standard_landmarks
        )[0]
        
        # Apply transform
        aligned = cv2.warpAffine(
            frame,
            transform_matrix,
            target_size,
            flags=cv2.INTER_LINEAR
        )
        
        return aligned
    
    def preprocess_for_model(self, aligned_face):
        # SFace uses standard ImageNet preprocessing
        # Convert to blob format (for OpenCV DNN)
        blob = cv2.dnn.blobFromImage(
            aligned_face,
            scalefactor=1.0/127.5,      # Normalize to [-1, 1]
            size=SFACE_INPUT_SIZE,
            mean=(127.5, 127.5, 127.5), # Subtract mean
            swapRB=True,                 # BGR -> RGB
            crop=False
        )
        
        return blob