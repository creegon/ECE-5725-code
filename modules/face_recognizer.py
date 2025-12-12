# modules/face_recognizer.py

from modules.face_detector import FaceDetector
from modules.face_aligner import FaceAligner
from modules.face_embedder import FaceEmbedder
from modules.face_database import FaceDatabase
from config import *

class FaceRecognizer:
    def __init__(self):
        # Initialize components
        self.detector = FaceDetector()
        self.aligner = FaceAligner()
        self.embedder = FaceEmbedder()
        self.database = FaceDatabase()
        
        if DEBUG:
            print("Face recognition system initialized")
            print(f"  Known persons: {self.database.get_person_count()}")
    
    def detect_and_recognize(self, frame):
        results = []
        
        # 1. Detect faces
        faces = self.detector.detect(frame)
        
        # 2. Recognize each face
        for face in faces:
            # Align face using landmarks
            aligned_face = self.aligner.align_from_detection(frame, face)
            
            # Extract embedding
            embedding = self.embedder.extract_embedding(aligned_face)
            
            # Search database
            person_name, similarity = self.database.search(embedding)
            
            results.append((face, person_name, similarity))
        
        return results
    
    def register_person(self, frame, person_name, num_samples=SAMPLES_PER_PERSON):
        # Detect faces
        faces = self.detector.detect(frame)
        
        if len(faces) == 0:
            return False, "No face detected"
        
        # Use the largest face only
        face = self.detector.get_largest_face(faces)
        
        # Align face
        aligned_face = self.aligner.align_from_detection(frame, face)
        
        # Extract embedding
        embedding = self.embedder.extract_embedding(aligned_face)
        
        # Add to database
        self.database.add_person(person_name, embedding)
        
        # Save database
        self.database.save()
        
        current_count = self.database.get_embedding_count(person_name)
        
        if current_count >= num_samples:
            return True, f"Registration complete! Total samples: {current_count}"
        else:
            return True, f"Collected {current_count}/{num_samples}"
    
    def get_known_persons(self):
        return self.database.get_all_persons()
    
    def detect_faces_only(self, frame):
        return self.detector.detect(frame)
    
    def remove_person(self, person_name):
        self.database.remove_person(person_name)
        self.database.save()