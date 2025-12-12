import time
from config import (
    DEBUG,
    SEARCH_ROTATE_SPEED, SEARCH_ROTATE_PAUSE, SEARCH_CYCLES,
    SEARCH_45DEG_DURATION,
    ROTATE_STEP_DURATION, ROTATE_STEP_PAUSE,
    FACE_CENTER_ENABLED, FACE_CENTER_TOLERANCE, FACE_CENTER_SPEED,
    FACE_CENTER_TIMEOUT, FACE_CENTER_STEP_DURATION, FACE_CENTER_STEP_PAUSE,
    CAMERA_WIDTH
)


class SearchController:
    def __init__(self):
        self.search_step = 0
        self.search_cycle = 0
        self.last_rotation_time = 0
        self.face_found_in_search = False
    
    def reset(self):
        self.search_step = 0
        self.search_cycle = 0
        self.last_rotation_time = 0
        self.face_found_in_search = False
    
    def is_in_rotation_pause(self):
        return time.time() - self.last_rotation_time < SEARCH_ROTATE_PAUSE
    
    def update_rotation_time(self):
        self.last_rotation_time = time.time()
    
    def get_next_search_action(self):
        # Step 0: rotate left 45 degrees
        if self.search_step == 0:
            return {
                'action': 'rotate_left',
                'duration': SEARCH_45DEG_DURATION,
                'message': 'Scan: rotate left 45 degrees'
            }
        
        # Step 1: rotate right 90 degrees (sweep)
        elif self.search_step == 1:
            return {
                'action': 'rotate_right',
                'duration': SEARCH_45DEG_DURATION * 2,
                'message': f'Scan: rotate right 90 degrees ({self.search_cycle + 1}/{SEARCH_CYCLES})'
            }
        
        # Step 2: rotate left 90 degrees (sweep back)
        elif self.search_step == 2:
            return {
                'action': 'rotate_left',
                'duration': SEARCH_45DEG_DURATION * 2,
                'message': f'Scan: rotate left 90 degrees ({self.search_cycle + 1}/{SEARCH_CYCLES})'
            }
        
        # Step 3: return to center (rotate right 45 degrees)
        elif self.search_step == 3:
            return {
                'action': 'rotate_right',
                'duration': SEARCH_45DEG_DURATION,
                'message': 'Scan: return to center'
            }
        
        else:
            return {
                'action': 'complete',
                'duration': 0,
                'message': 'Scan complete'
            }
    
    def advance_step(self):
        if self.search_step == 0:
            self.search_step = 1
        elif self.search_step == 1:
            self.search_step = 2
        elif self.search_step == 2:
            self.search_cycle += 1
            if self.search_cycle >= SEARCH_CYCLES:
                self.search_step = 3
            else:
                self.search_step = 1
        elif self.search_step == 3:
            self.search_step = 4  # Complete
    
    def is_search_complete(self):
        return self.search_step > 3
    
    def on_face_found(self):
        self.face_found_in_search = True
    
    def detect_face_in_search(self, camera, face_recognizer, motor=None):
        if camera is None or face_recognizer is None:
            return False
            
        # 1. Read a frame
        ret, frame = camera.read()
        if ret:
            # Detect faces only for better performance
            faces = face_recognizer.detect_faces_only(frame)
            if len(faces) > 0:
                self.on_face_found()
                return True
        return False
    
    def rotate_and_detect(self, direction, duration, motor, action_recorder, camera, face_recognizer):
        if DEBUG:
            print(f"Start smooth rotation: {direction}, target duration={duration:.2f}s")
        
        start_time = time.time()
        found_face = False
        
        # Start motors
        if motor is not None and motor.enabled:
            if direction == 'left':
                motor.turn_left(SEARCH_ROTATE_SPEED)
            else:
                motor.turn_right(SEARCH_ROTATE_SPEED)
        
        try:
            while time.time() - start_time < duration:
                # 1. Detect faces
                # Note: loop speed is limited by the camera frame rate
                if self.detect_face_in_search(camera, face_recognizer):
                    found_face = True
                    if DEBUG:
                        print("Face found during rotation; stopping immediately")
                    break
                
                # Process every frame at full speed
                
        finally:
            # Always stop motors (whether a face was found or an error occurred)
            if motor is not None and motor.enabled:
                motor.stop()
        
        actual_rotate_time = time.time() - start_time
        
        # Record actual rotation time
        if actual_rotate_time > 0.1: # Ignore actions that are too short
            action_recorder.record('rotate', direction, actual_rotate_time)
            if DEBUG:
                print(f"Search rotation finished: {direction} {actual_rotate_time:.2f}s")
                
        return found_face
    
    def _get_largest_face(self, results):
        if len(results) == 0:
            return None
        
        if len(results) == 1:
            return results[0]
        
        # Pick the face with the largest area
        largest = results[0]
        largest_area = largest[0]['box'][2] * largest[0]['box'][3]  # w * h
        
        for result in results[1:]:
            area = result[0]['box'][2] * result[0]['box'][3]
            if area > largest_area:
                largest = result
                largest_area = area
        
        if DEBUG:
            print(f"Detected {len(results)} faces; selecting the largest (area={largest_area}px^2)")
        
        return largest
    
    def center_face(self, face_rect, motor, camera, face_recognizer, action_recorder, display):
        if not FACE_CENTER_ENABLED:
            return True  # Feature disabled; treat as success
        
        if motor is None or not motor.enabled:
            if DEBUG:
                print("Motor not enabled; skipping face centering")
            return True  # No motor; skip centering
        
        # Frame width
        frame_width = CAMERA_WIDTH
        center_x = frame_width / 2
        tolerance = frame_width * FACE_CENTER_TOLERANCE
        
        MAX_CENTER_RETRIES = 3  # Max retries (reverse-correct after overshoot)
        
        for retry in range(MAX_CENTER_RETRIES):
            # Compute current offset
            box = face_rect['box']
            face_center_x = box[0] + box[2] / 2
            offset = face_center_x - center_x
            
            # If already centered, return
            if abs(offset) <= tolerance:
                print(
                    f"Face centered! offset={offset:.0f}px"
                    + (f" (attempt {retry+1})" if retry > 0 else "")
                )
                return True
            
            # Determine rotation direction
            if offset > 0:
                direction = 'right'
                if retry == 0:
                    print(f"Face is {offset:.0f}px to the right; rotating right...")
                else:
                    print(f"Correction {retry+1}: face is {offset:.0f}px to the right; rotating right...")
            else:
                direction = 'left'
                if retry == 0:
                    print(f"Face is {abs(offset):.0f}px to the left; rotating left...")
                else:
                    print(f"Correction {retry+1}: face is {abs(offset):.0f}px to the left; rotating left...")
            
            # Perform one centering rotation pass
            result = self._do_center_rotation(
                direction, motor, camera, face_recognizer, 
                action_recorder, display, center_x, tolerance
            )
            
            if result['centered']:
                return True
            
            if result['face_rect'] is None:
                print("Face lost during centering")
                return False
            
            # Update face location and continue to the next correction
            face_rect = result['face_rect']
            
            # Brief pause to stabilize motors
            time.sleep(0.1)
        
        print(f"Reached max corrections ({MAX_CENTER_RETRIES}); centering finished")
        return True  # Not perfectly centered, but do not block subsequent actions
    
    def _do_center_rotation(self, direction, motor, camera, face_recognizer, 
                            action_recorder, display, center_x, tolerance):
        max_rotate_time = FACE_CENTER_TIMEOUT
        step_duration = FACE_CENTER_STEP_DURATION
        pause_duration = FACE_CENTER_STEP_PAUSE
        max_steps = int(max_rotate_time / (step_duration + pause_duration))
        
        last_face_rect = None
        centered = False
        overshot = False
        actual_rotate_time = 0.0
        
        for step in range(max_steps):
            # Rotate one small step
            if direction == 'right':
                motor.turn_right(FACE_CENTER_SPEED)
            else:
                motor.turn_left(FACE_CENTER_SPEED)
            time.sleep(step_duration)
            motor.stop()
            actual_rotate_time += step_duration
            
            # Brief pause, then detect face
            time.sleep(pause_duration)
            
            # Read camera frame
            ret, frame = camera.read()
            if not ret:
                continue
            
            # Detect face (pick the largest)
            results = face_recognizer.detect_and_recognize(frame)
            largest = self._get_largest_face(results)
            if largest is None:
                continue  # Face lost; keep rotating to try to reacquire
            
            last_face_rect = largest[0]
            box = last_face_rect['box']
            face_center_x = box[0] + box[2] / 2
            offset = face_center_x - center_x
            
            if DEBUG:
                print(f"Centering: offset={offset:.0f}px, tolerance=±{tolerance:.0f}px")
            
            # Check if centered
            if abs(offset) <= tolerance:
                print(f"Face centered! offset={offset:.0f}px, time={actual_rotate_time:.2f}s")
                centered = True
                break
            
            # Check overshoot (direction changed)
            new_direction = 'right' if offset > 0 else 'left'
            if new_direction != direction:
                print("Overshoot detected; stopping and preparing reverse correction")
                overshot = True
                break
            
            # Update display
            display.update(delta_time=step_duration + pause_duration)
        
        # Record actual rotation time
        if actual_rotate_time > 0.1:
            action_recorder.record('rotate', direction, actual_rotate_time)
            if DEBUG:
                print(f"Centering rotation recorded: {direction} {actual_rotate_time:.2f}s")
        
        return {
            'centered': centered,
            'face_rect': last_face_rect,
            'overshot': overshot
        }
