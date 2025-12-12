# modules/face_detector.py

import cv2
import numpy as np
from config import *

# Get minimum face size config (default 60)
try:
    from config import MIN_FACE_SIZE
except ImportError:
    MIN_FACE_SIZE = 60

class FaceDetector:
    def __init__(self):
        import os
        
        # Check model file exists
        if not os.path.exists(YUNET_MODEL_PATH):
            raise FileNotFoundError(
                f"YuNet model file not found: {YUNET_MODEL_PATH}\n"
                f"Please run: python utils/download_model.py"
            )
        
        # Create YuNet detector
        self.detector = cv2.FaceDetectorYN.create(
            model=YUNET_MODEL_PATH,
            config="",
            input_size=YUNET_INPUT_SIZE,
            score_threshold=YUNET_CONF_THRESHOLD,
            nms_threshold=YUNET_NMS_THRESHOLD,
            top_k=YUNET_TOP_K
        )
        
        if DEBUG:
            print("YuNet face detector initialized")
    
    def detect(self, frame):
        # Set input size (adjust dynamically based on frame size)
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        
        # Detect faces
        _, faces = self.detector.detect(frame)
        
        if faces is None:
            return []
        
        # Parse detection results
        result = []
        for face in faces:
            # face contains 15 values:
            # [0-3]: x, y, w, h (bounding box)
            # [4-13]: x,y coords for 5 keypoints
            # [14]: confidence score
            
            x, y, w, h = face[:4].astype(int)
            landmarks = face[4:14].reshape(5, 2).astype(int)
            confidence = face[14]
            
            # Return only high-confidence and sufficiently large detections
            if confidence >= YUNET_CONF_THRESHOLD and w >= MIN_FACE_SIZE and h >= MIN_FACE_SIZE:
                result.append({
                    'box': (x, y, w, h),
                    'landmarks': landmarks,
                    'confidence': confidence
                })
        
        return result
    
    def get_largest_face(self, faces):
        if not faces:
            return None
        
        # Return the largest by area
        largest = max(faces, key=lambda f: f['box'][2] * f['box'][3])
        return largest
    
    def extract_face_roi(self, frame, face, target_size=None):
        x, y, w, h = face['box']
        
        # Clamp to frame bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, frame.shape[1] - x)
        h = min(h, frame.shape[0] - y)
        
        # Extract face ROI
        face_img = frame[y:y+h, x:x+w]
        
        # Resize if needed
        if target_size is not None:
            face_img = cv2.resize(face_img, target_size, interpolation=cv2.INTER_LINEAR)
        
        return face_img
    
    def draw_face_box(self, frame, face, label=None, color=(0, 255, 0), thickness=2):
        x, y, w, h = face['box']
        landmarks = face['landmarks']
        
        # Draw bounding box
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
        
        # Draw landmarks
        for i, (lx, ly) in enumerate(landmarks):
            # Use different colors for different landmarks
            if i < 2:  # eyes
                point_color = (255, 0, 0)  # blue
            elif i == 2:  # nose
                point_color = (0, 255, 0)  # green
            else:  # mouth
                point_color = (0, 0, 255)  # red
            
            cv2.circle(frame, (lx, ly), 2, point_color, -1)
        
        # Draw label (if provided)
        if label:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, font_thickness
            )
            
            # Draw background
            cv2.rectangle(
                frame,
                (x, y - text_height - baseline - 5),
                (x + text_width, y),
                color,
                -1
            )
            
            # Draw text
            cv2.putText(
                frame,
                label,
                (x, y - 5),
                font,
                font_scale,
                (255, 255, 255),
                font_thickness
            )