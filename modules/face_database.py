# modules/face_database.py

import pickle
import numpy as np
import os
from config import *

class FaceDatabase:
    def __init__(self, db_path=FACE_DATABASE_PATH):
        self.db_path = db_path
        
        # Data structure: {person_name: [embedding1, embedding2, ...]}
        self.database = {}
        
        # Load existing database
        self.load()
        
        if DEBUG:
            print("Face database initialized")
            print(f"  Known people: {len(self.database)}")
    
    def add_person(self, person_name, embedding):
        if person_name not in self.database:
            self.database[person_name] = []
        
        self.database[person_name].append(embedding)
        
        if DEBUG:
            print(f"  Added embedding: {person_name} (total: {len(self.database[person_name])})")
    
    def remove_person(self, person_name):
        if person_name in self.database:
            del self.database[person_name]
            if DEBUG:
                print(f"  Removed person: {person_name}")
    
    def get_all_persons(self):
        return list(self.database.keys())
    def get_person_count(self):
        return len(self.database)

    def get_embedding_count(self, person_name):
        if person_name in self.database:
            return len(self.database[person_name])
        return 0
    
    def search(self, query_embedding, threshold=RECOGNITION_THRESHOLD):
        if len(self.database) == 0:
            return None, 0.0
        
        best_match = None
        best_similarity = 0.0
        second_best_similarity = 0.0
        
        # Iterate over all people
        for person_name, embeddings in self.database.items():
            # Compute similarity against all embeddings and take the max for robustness
            person_best = 0.0
            for emb in embeddings:
                sim = self._cosine_similarity(query_embedding, emb)
                if sim > person_best:
                    person_best = sim
            
            # Update best and second-best
            if person_best > best_similarity:
                second_best_similarity = best_similarity
                best_similarity = person_best
                best_match = person_name
            elif person_best > second_best_similarity:
                second_best_similarity = person_best
        
        # Check threshold and margin against the second-best
        margin_ok = (best_similarity - second_best_similarity) >= RECOGNITION_MARGIN
        if len(self.database) <= 1:
            margin_ok = True  # No need for margin check with a single person
        
        # Debug output
        if DEBUG:
            print(
                f"[DEBUG] threshold={threshold:.2f}, best={best_similarity:.2f}, "
                f"second_best={second_best_similarity:.2f}, margin_ok={margin_ok}, match={best_match}"
            )
        
        if best_similarity >= threshold and margin_ok:
            return best_match, best_similarity
        else:
            return None, best_similarity
    
    @staticmethod
    def _cosine_similarity(emb1, emb2):
        emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-8)
        emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-8)
        similarity = np.dot(emb1_norm, emb2_norm)
        similarity = (similarity + 1) / 2  # Map to [0, 1]
        return float(similarity)
    
    def save(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Save
        with open(self.db_path, 'wb') as f:
            pickle.dump(self.database, f)
        
        if DEBUG:
            print(f"Database saved: {self.db_path}")
    
    def load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'rb') as f:
                    self.database = pickle.load(f)
                
                if DEBUG:
                    print(f"Database loaded: {self.db_path}")
                    for name, embs in self.database.items():
                        print(f"  - {name}: {len(embs)} embeddings")
            except Exception as e:
                print(f"Failed to load database: {e}")
                self.database = {}
        else:
            if DEBUG:
                print("Database file not found; creating a new database")
            self.database = {}
    
    def clear(self):
        """Clear the database."""
        self.database = {}
        if DEBUG:
            print("  Database cleared")
