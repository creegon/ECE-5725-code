import time
import cv2
import numpy as np
from config import *

class BehaviorController:
    def __init__(self, motor, camera, ultrasonic, face_recognizer, action_recorder, display, audio):
        self.motor = motor
        self.camera = camera
        self.ultrasonic = ultrasonic
        self.face_recognizer = face_recognizer
        self.action_recorder = action_recorder
        self.display = display
        self.audio = audio
        
        # Tracking state
        self._face_centered = False
        self._offset_confirm_count = 0
        self._last_offset_direction = None
        
        # Follow state
        self._smooth_eye_dist = None
        self._smooth_offset = None
        self._familiar_consecutive_actions = 0

    def approach_familiar_person(self):
        if not self.motor:
            print("Motor not enabled; skipping approach")
            return 0.0
        
        # If visual distance checking is disabled, use a fixed duration
        if not FACE_CLOSE_ENABLED:
            print("Visual distance check disabled; using fixed duration")
            fixed_time = MOTOR_MOVE_DURATION
            if fixed_time > 0:
                self.action_recorder.start_action('move', 'forward')
                self.motor.forward()
                time.sleep(fixed_time)
                self.motor.stop()
                self.action_recorder.stop_action()
            return fixed_time
        
        print("Approaching familiar person...")
        
        # Ensure a full stop
        self.motor.stop()
        time.sleep(0.15)
        
        max_approach_time = 10.0
        check_interval = 0.1
        
        start_time = time.time()
        is_blocked = False
        is_moving = False
        
        while time.time() - start_time < max_approach_time:
            # Ultrasonic check
            obstacle_detected = False
            if self.ultrasonic:
                obstacle_detected = self.ultrasonic.is_object_near(use_cached=True)
                
                if DEBUG and obstacle_detected:
                    print(f"[Approach] Obstacle detected: {obstacle_detected}")
            
            if obstacle_detected:
                if is_moving:
                    self.motor.brake()
                    self.action_recorder.stop_action()
                    is_moving = False
                
                if not is_blocked:
                    print("Blocked! Waiting...")
                    self.display.show_emotion("cry")
                    if self.audio:
                        self.audio.play_sound("obstacle")
                    is_blocked = True
                
                time.sleep(check_interval)
                self.display.update(delta_time=check_interval)
                continue
            else:
                if is_blocked:
                    print("Path clear! Resuming...")
                    self.display.show_emotion("happy")
                    is_blocked = False
                    time.sleep(0.2)
            
            # Visual distance check
            stop_signal = False
            
            if self.camera is not None and FACE_CLOSE_ENABLED:
                # Flush camera buffer
                for _ in range(2):
                    self.camera.grab()
                
                ret, frame = self.camera.read()
                if ret:
                    # Detection only (faster)
                    faces = self.face_recognizer.detector.detect(frame)
                    
                    if len(faces) > 0:
                        face_rect = self.face_recognizer.detector.get_largest_face(faces)
                        face_width = face_rect['box'][2]
                        
                        right_eye = face_rect['landmarks'][0]
                        left_eye = face_rect['landmarks'][1]
                        eye_dist = np.linalg.norm(right_eye - left_eye)
                        
                        if DEBUG:
                            print(f"[Distance] Eye distance: {eye_dist:.1f}px (threshold: {FACE_CLOSE_EYE_DISTANCE}), width: {face_width}px (threshold: {FACE_CLOSE_THRESHOLD})")
                        
                        if eye_dist >= FACE_CLOSE_EYE_DISTANCE:
                             print(f"[Vision] Eye distance close enough: {eye_dist:.1f}px")
                             stop_signal = True
                        elif face_width >= FACE_CLOSE_THRESHOLD:
                            print(f"[Vision] Face wide enough: {face_width}px")
                            stop_signal = True
            
            if stop_signal:
                if is_moving:
                    self.motor.stop()
                    self.action_recorder.stop_action()
                    is_moving = False
                break
            
            # Move forward
            if not is_moving:
                self.action_recorder.start_action('move', 'forward')
                self.motor.forward()
                is_moving = True
            
            # Briefly yield CPU
            time.sleep(0.01)
            
            self.display.update(delta_time=0.01)
        
        if is_moving:
            self.motor.stop()
            self.action_recorder.stop_action()
        
        total_forward_time = time.time() - start_time
        print(f"Approach finished. Time: {total_forward_time:.2f}s")
        
        return total_forward_time

    def check_obstacle_while_moving(self):
        if self.ultrasonic:
            if self.ultrasonic.is_object_near():
                if DEBUG:
                    print("Obstacle detected while moving")
                return True
        return False

    def check_face_too_close(self):
        if not FACE_CLOSE_ENABLED:
            return False
        
        if self.camera is None:
            return False
        
        ret, frame = self.camera.read()
        if not ret:
            return False
        
        faces = self.face_recognizer.detector.detect(frame)
        
        if not faces:
            return False
            
        face_rect = self.face_recognizer.detector.get_largest_face(faces)
        face_width = face_rect['box'][2]
        face_height = face_rect['box'][3]
        
        if face_width >= FACE_CLOSE_THRESHOLD or face_height >= FACE_CLOSE_THRESHOLD:
            print(f"Face too close! width={face_width}px (threshold={FACE_CLOSE_THRESHOLD}px); stopping forward movement")
            return True
        
        return False

    def track_face_position(self, face_rect):
        if not self.motor:
            if DEBUG:
                print("[Track] Motor not enabled; skipping tracking")
            return
        
        frame_width = 640
        if self.camera is not None:
            frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        
        face_x = face_rect['box'][0]
        face_w = face_rect['box'][2]
        face_center_x = face_x + face_w / 2
        frame_center_x = frame_width / 2
        
        offset_ratio = (face_center_x - frame_center_x) / frame_width
        
        current_offset_direction = 'right' if offset_ratio > 0 else 'left'
        
        if DEBUG:
            print(f"[Track] Frame width={frame_width}, face_x={face_x:.0f}, face_w={face_w:.0f}, "
                f"face_center={face_center_x:.0f}, frame_center={frame_center_x:.0f}, "
                f"offset={offset_ratio:.2%}, tolerance=±{FACE_CENTER_TOLERANCE:.0%}")
        
        if abs(offset_ratio) <= FACE_CENTER_TOLERANCE:
            self._face_centered = True
            self._offset_confirm_count = 0
            self._last_offset_direction = None
            if DEBUG:
                print("[Track] Face centered; no adjustment needed")
            return
        
        if self._face_centered:
            if current_offset_direction == self._last_offset_direction:
                self._offset_confirm_count += 1
            else:
                self._offset_confirm_count = 1
                self._last_offset_direction = current_offset_direction
            
            if DEBUG:
                print(f"[Track] Confirming offset: {self._offset_confirm_count}/{FACE_CENTER_CONFIRM_COUNT} (dir: {current_offset_direction})")
            
            if self._offset_confirm_count < FACE_CENTER_CONFIRM_COUNT:
                return
            
            if DEBUG:
                print("[Track] Offset confirmed; starting tracking")
            self._face_centered = False
            self._offset_confirm_count = 0
        
        self._track_until_centered(current_offset_direction)

    def _track_until_centered(self, initial_direction):
        max_rotations = 20
        current_direction = initial_direction
        last_offset = None
        stuck_count = 0
        
        for i in range(max_rotations):
            if DEBUG:
                arrow = "->" if current_direction == 'right' else "<-"
                print(f"[Track] {arrow} rotating {current_direction} "
                      f"(speed={FACE_CENTER_SPEED}, duration={FACE_CENTER_STEP_DURATION}s)")
            
            self.action_recorder.start_action('rotate', current_direction)
            if current_direction == 'right':
                self.motor.turn_right(FACE_CENTER_SPEED)
            else:
                self.motor.turn_left(FACE_CENTER_SPEED)
            
            time.sleep(FACE_CENTER_STEP_DURATION)
            self.motor.stop()
            self.action_recorder.stop_action()
            
            if DEBUG:
                print("[Track] Rotation complete; detecting face...")
            time.sleep(FACE_CENTER_STEP_PAUSE)
            
            for _ in range(3):
                self.camera.grab()
            
            ret, frame = self.camera.read()
            if not ret:
                if DEBUG:
                    print("[Track] Failed to read camera")
                return
            
            results = self.face_recognizer.detect_and_recognize(frame)
            
            if len(results) == 0:
                if DEBUG:
                    print("[Track] Face lost; stopping tracking")
                return
            
            face_rect = results[0][0]
            frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            face_x = face_rect['box'][0]
            face_w = face_rect['box'][2]
            face_center_x = face_x + face_w / 2
            frame_center_x = frame_width / 2
            offset_ratio = (face_center_x - frame_center_x) / frame_width
            
            if last_offset is not None:
                delta = abs(offset_ratio - last_offset)
                if delta < 0.02:
                    stuck_count += 1
                    if DEBUG and stuck_count >= 3:
                        print("[Track] Detected stuck state; offset barely changes")
                else:
                    stuck_count = 0
            last_offset = offset_ratio
            
            if DEBUG:
                print(f"[Track] Current offset: {offset_ratio:+.1%}")
            
            if abs(offset_ratio) <= FACE_CENTER_TOLERANCE:
                if DEBUG:
                    print(f"[Track] Centered! Recorded actions: {self.action_recorder.get_action_count()}")
                self._face_centered = True
                self._offset_confirm_count = 0
                self._last_offset_direction = None
                return
            
            current_direction = 'right' if offset_ratio > 0 else 'left'
        
        if DEBUG:
            print(f"[Track] Reached max rotations: {max_rotations}")

    def follow_familiar_person(self):
        if not self.motor:
            return False

        # Flush buffer for real-time behavior
        for _ in range(2):
            self.camera.grab()
        
        ret, frame = self.camera.read()
        if not ret:
            return False

        # Detect faces only (faster)
        faces = self.face_recognizer.detector.detect(frame)
        
        if not faces:
            # Face lost
            return False
        
        # Select the largest face
        face_rect = self.face_recognizer.detector.get_largest_face(faces)
        
        # --- Compute metrics ---
        frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        face_x = face_rect['box'][0]
        face_w = face_rect['box'][2]
        face_center_x = face_x + face_w / 2
        frame_center_x = frame_width / 2
        raw_offset_ratio = (face_center_x - frame_center_x) / frame_width
        
        right_eye = face_rect['landmarks'][0]
        left_eye = face_rect['landmarks'][1]
        raw_eye_dist = np.linalg.norm(right_eye - left_eye)
        
        # --- Data smoothing (EMA) ---
        alpha = 0.7  # Smoothing factor (0.7 means new value weight is 70%)
        if self._smooth_eye_dist is None:
            self._smooth_eye_dist = raw_eye_dist
            self._smooth_offset = raw_offset_ratio
        else:
            self._smooth_eye_dist = self._smooth_eye_dist * (1 - alpha) + raw_eye_dist * alpha
            self._smooth_offset = self._smooth_offset * (1 - alpha) + raw_offset_ratio * alpha
            
        eye_dist = self._smooth_eye_dist
        offset_ratio = self._smooth_offset
        
        # --- Anti-jitter guard ---
        # If actions happen too frequently, force a cooldown
        if self._familiar_consecutive_actions > 6:
            if DEBUG:
                print(f"[Follow] Actions too frequent ({self._familiar_consecutive_actions}); forcing cooldown 0.8s...")
            time.sleep(0.8)
            self._familiar_consecutive_actions = 0
            # Clear smoothing history after cooldown to avoid stale data
            self._smooth_eye_dist = None
            self._smooth_offset = None
            return True # Still return True to indicate the face is present

        # --- Control logic ---
        action_taken = False
        
        # A. Rotation follow (higher priority)
        if abs(offset_ratio) > FACE_CENTER_TOLERANCE:
            direction = 'right' if offset_ratio > 0 else 'left'
            if DEBUG:
                print(f"[Follow] Rotation correction: {direction} (offset: {offset_ratio:+.1%})")
            
            # Short rotation burst
            self.action_recorder.start_action('rotate', direction)
            if direction == 'right':
                self.motor.turn_right(FACE_CENTER_SPEED)
            else:
                self.motor.turn_left(FACE_CENTER_SPEED)
            
            time.sleep(0.1) # Short rotation
            self.motor.stop()
            self.action_recorder.stop_action()
            
            action_taken = True
            
        # B. Distance follow (only when centered)
        else:
            # Target range: target +/- 15% (deadband)
            target_dist = FACE_CLOSE_EYE_DISTANCE
            margin = target_dist * 0.15
            min_dist = target_dist - margin
            max_dist = target_dist + margin
            
            if eye_dist < min_dist:
                # Too far -> forward
                if DEBUG:
                    print(f"[Follow] Too far (eye_dist: {eye_dist:.1f} < {min_dist:.1f}) -> forward")
                
                self.action_recorder.start_action('move', 'forward')
                self.motor.forward(speed=55) # Slightly slower
                time.sleep(0.15) # Short movement
                self.motor.stop()
                self.action_recorder.stop_action()
                action_taken = True
                
            elif eye_dist > max_dist:
                # Too close -> backward
                if DEBUG:
                    print(f"[Follow] Too close (eye_dist: {eye_dist:.1f} > {max_dist:.1f}) -> backward")
                
                # Simple check before backing up (no rear sensor)
                self.action_recorder.start_action('move', 'backward')
                self.motor.backward(speed=55)
                time.sleep(0.15)
                self.motor.stop()
                self.action_recorder.stop_action()
                action_taken = True
            else:
                # Good distance
                if DEBUG:
                    print(f"[Follow] Distance perfect (eye_dist: {eye_dist:.1f})")
        
        # Update consecutive action counter
        if action_taken:
            self._familiar_consecutive_actions += 1
        else:
            self._familiar_consecutive_actions = 0
            
        return True

    def reset_follow_state(self):
        self._smooth_eye_dist = None
        self._smooth_offset = None
        self._familiar_consecutive_actions = 0
