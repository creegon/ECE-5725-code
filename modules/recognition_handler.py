import time
from config import (
    DEBUG, SIMULATION_MODE,
    EMOTION_CONFIRM_COUNT, NO_FACE_RESET_COUNT,
    RECOGNITION_INTERVAL, SAMPLE_INTERVAL, SAMPLES_PER_PERSON,
    REGISTRATION_COMPLETE_AUTO_RECOVERY
)


class RecognitionHandler:
    def __init__(self):
        self.recognition_counters = {
            "familiar": 0,
            "stranger": 0
        }
        self.recognition_active_label = None
        self.no_face_count = 0
        
        self.is_registering = False
        self.register_name = ""
        self.register_count = 0
    
    def update_counter(self, label):
        for key in self.recognition_counters:
            if key == label:
                self.recognition_counters[key] = min(
                    EMOTION_CONFIRM_COUNT,
                    self.recognition_counters[key] + 1
                )
            else:
                if self.recognition_counters[key] > 0:
                    self.recognition_counters[key] -= 1
    
    def reset_counters(self):
        for key in self.recognition_counters:
            self.recognition_counters[key] = 0
    
    def decay_counters(self):
        for key in self.recognition_counters:
            if self.recognition_counters[key] > 0:
                self.recognition_counters[key] -= 1
    
    def get_count(self, label):
        return self.recognition_counters.get(label, 0)

    def is_confirmed(self, label):
        return self.recognition_counters.get(label, 0) >= EMOTION_CONFIRM_COUNT

    def on_face_lost(self):
        self.no_face_count += 1
        self.decay_counters()
        
        if self.no_face_count >= NO_FACE_RESET_COUNT:
            self.recognition_active_label = None
            self.reset_counters()
            self.no_face_count = 0
            return True
        return False
    
    def on_face_detected(self):
        self.no_face_count = 0
    
    def set_active_label(self, label):
        self.recognition_active_label = label
        
    def get_active_label(self):
        return self.recognition_active_label

    def should_skip_recognition_frame(self, frame_count):
        return frame_count % RECOGNITION_INTERVAL != 0
    
    def should_skip_registration_frame(self, frame_count):
        return frame_count % SAMPLE_INTERVAL != 0
    
    def start_registration(self, name=None):
        if name:
            self.register_name = name
        else:
            self.register_name = f"person_{int(time.time())}"
        
        print(f"Start registration: {self.register_name}...")
        print(f"Target sample count: {SAMPLES_PER_PERSON}")
        print("Please face the camera.\n")
        
        self.is_registering = True
        self.register_count = 0
        return True
    
    def handle_registration(self, frame, face_recognizer, on_complete=None):
        success, message = face_recognizer.register_person(
            frame, self.register_name, num_samples=SAMPLES_PER_PERSON
        )
        
        if success:
            self.register_count += 1
            
            if DEBUG:
                print(f"  {message}")
            
            # Check whether registration is complete
            if self.register_count >= SAMPLES_PER_PERSON:
                print(f"\n{self.register_name} data collection complete!")
                self.is_registering = False
                self.register_name = ""
                self.register_count = 0
                
                if on_complete:
                    on_complete()
                
                return True
        else:
            if DEBUG:
                print(f"  {message}")
        
        return False
    
    def cancel_registration(self):
        self.is_registering = False
        self.register_name = ""
        self.register_count = 0
