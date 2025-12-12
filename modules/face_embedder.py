# modules/face_embedder.py

import cv2
import numpy as np
from config import *

class FaceEmbedder:
    def __init__(self, model_path=SFACE_MODEL_PATH):
        import os
        
        # Check whether the model file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"SFace model file not found: {model_path}\n"
                f"Please run: python utils/download_model.py"
            )
        
        # Create SFace recognizer (OpenCV FaceRecognizerSF)
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=model_path,
            config=""
        )
        
        if DEBUG:
            print("SFace embedder loaded successfully")
            print(f"  Model path: {model_path}")
    
    def extract_embedding(self, aligned_face):
        # SFace extracts embeddings via the feature() method.
        # Input must be a 112x112 BGR image.
        feature = self.recognizer.feature(aligned_face)
        
        # Normalize (L2)
        embedding = feature.flatten()
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def get_embedding_from_aligned_face(self, aligned_face, aligner=None):
        return self.extract_embedding(aligned_face)
    
    @staticmethod
    def cosine_similarity(emb1, emb2):
        # Ensure normalized vectors
        emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-8)
        emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-8)
        
        # Cosine similarity
        similarity = np.dot(emb1_norm, emb2_norm)
        
        return similarity