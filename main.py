# main.py

import cv2
import time
import os
import sys
import platform
import numpy as np

if platform.system() == "Windows":
    os.environ['SDL_AUDIODRIVER'] = 'directsound'

from config import SIMULATION_MODE

os.environ['SDL_VIDEODRIVER'] = 'dummy'

from config import *
from modules.display_handler import DisplayHandler
from modules.audio_handler import AudioHandler
from modules.touch_handler import TouchHandler
from modules.face_recognizer import FaceRecognizer
from modules.voice_listener import VoiceListener
from modules.ultrasonic_sensor import UltrasonicSensor
from modules.motor_controller import MotorController
from utils.camera_helper import open_camera

# New modules
from modules.state_machine import State
from modules.action_recorder import ActionRecorder
from modules.recognition_handler import RecognitionHandler
from modules.search_controller import SearchController
from modules.interaction_handler import InteractionHandler
from modules.debug_controller import DebugController
from modules.behavior_controller import BehaviorController



class WallE:
    def __init__(self):
        print("WALL-E system starting...")
        
        # Core subsystems
        self.display = DisplayHandler()
        self.audio = AudioHandler()
        self.touch = TouchHandler(self.display, self.audio)
        
        # Hardware sensors & actuators
        self.ultrasonic = None
        self.ultrasonic_enabled = False
        if ULTRASONIC_ENABLED:
            try:
                self.ultrasonic = UltrasonicSensor()
                self.ultrasonic_enabled = self.ultrasonic.enabled
            except Exception as e:
                print(f"Ultrasonic initialization failed: {e}")
        
        self.motor = None
        self.motor_enabled = False
        if MOTOR_ENABLED:
            try:
                self.motor = MotorController(default_speed=MOTOR_DEFAULT_SPEED)
                self.motor_enabled = self.motor.enabled
            except Exception as e:
                print(f"Motor initialization failed: {e}")
        
        # Vision system
        self.face_recognizer = None
        self.face_enabled = False
        self.camera = None
        
        try:
            # Check whether the OpenCV version supports YuNet
            opencv_version = tuple(map(int, cv2.__version__.split('.')[:2]))
            if opencv_version >= (4, 5):
                self.face_recognizer = FaceRecognizer()
                self.face_enabled = True
            else:
                print(f"OpenCV version too old ({cv2.__version__}); need 4.5.4+ to support YuNet")
        except Exception as e:
            print(f"Face recognition initialization failed: {e}")
        
        if self.face_enabled:
            self.camera = open_camera()
            if self.camera is None:
                print("Camera initialization failed; disabling face recognition")
                self.face_enabled = False
        
        self.running = True
        self.frame_count = 0
        self.voice_listener = None
        
        # Logic controllers
        self.action_recorder = ActionRecorder()
        self.recognition = RecognitionHandler()
        self.search = SearchController()
        self.interaction = InteractionHandler()
        
        self.behavior_controller = BehaviorController(
            self.motor, self.camera, self.ultrasonic, 
            self.face_recognizer, self.action_recorder, 
            self.display, self.audio
        )

        # State machine
        self.state = State.IDLE
        self.state_start_time = time.time()
        
        # Performance monitoring
        self.fps_time = time.time()
        self.fps_counter = 0
        self.fps = 0
        
        print("System ready.")
        if SIMULATION_MODE:
            print("Mode: simulation")
            if os.environ.get('SSH_CLIENT') or os.environ.get('SSH_TTY'):
                print("SSH environment detected - headless mode")
            else:
                print("   - Click to simulate touch")
                print("   - Press Q to quit")
        else:
            print("Hardware mode")
        
        if self.face_enabled:
            known_count = self.face_recognizer.database.get_person_count()
            print(f"Known faces: {known_count}")
        
        if self.ultrasonic_enabled:
            enabled_count = sum(1 for s in self.ultrasonic.sensors if s.enabled)
            print(f"Ultrasonic sensors: {enabled_count} active (threshold: {ULTRASONIC_DISTANCE_THRESHOLD}cm)")
        
        print("="*60 + "\n")
        
        self.init_voice_control()
        
        # Initial state: IDLE
        print("State: IDLE (Sleepy)")
        self.state = State.IDLE
        self.display.show_emotion("sleepy")
        
        self.last_status_time = time.time()
        
        # Debug controller
        self.debug_controller = DebugController(self)
        self.debug_controller.start()
    
    
    def init_voice_control(self):
        if not VOICE_ENABLED:
            return
        try:
            self.voice_listener = VoiceListener(
                wake_phrases=VOICE_WAKE_PHRASES,
                on_trigger=self.on_voice_wake,
                mic_name=VOICE_MIC_NAME,
                mic_index=VOICE_MIC_INDEX,
                listen_timeout=VOICE_LISTEN_TIMEOUT,
                phrase_time_limit=VOICE_PHRASE_TIME_LIMIT,
                language=VOICE_LANGUAGE,
                engine=VOICE_ENGINE,
                vosk_model_path=VOSK_MODEL_PATH,
                commands=VOICE_COMMANDS,
                on_command=self.on_voice_command,
            )
            if not self.voice_listener.available:
                print("SpeechRecognition not installed; voice wake is disabled")
                self.voice_listener = None
                return
            if self.voice_listener.start():
                print("Voice wake started. Say 'hey' to wake, 'sing' to sing, 'spin' to spin")
            else:
                print("Failed to start voice listener")
        except Exception as e:
            print(f"Voice control initialization failed: {e}")
            self.voice_listener = None

    def stop_voice_control(self):
        if self.voice_listener:
            self.voice_listener.stop()
            self.voice_listener = None

    def _pause_voice_recognition(self):
        if self.voice_listener:
            self.voice_listener.pause()
    
    def _resume_voice_recognition(self):
        if self.voice_listener:
            self.voice_listener.resume()
        self.interaction.is_playing_audio = False

    def on_voice_command(self, command, transcript):
        # If currently returning, ignore voice commands
        if self.action_recorder.is_returning:
            if DEBUG:
                print(f"Returning; ignoring command: {command}")
            return
        
        # If not awakened, ignore commands (need to say 'hey' first)
        if not self.interaction.is_awake:
            if DEBUG:
                print(f"Not awakened; ignoring command: {command}")
            return
        
        print(f"Voice command: {command} (transcript: {transcript})")
        
        # Extend wake time
        self.interaction.awake_time = time.time()
        
        # Refresh interaction timers
        if self.interaction.familiar_interaction_active:
            self.interaction.refresh_familiar_interaction()
        
        if self.interaction.stranger_observation_active:
            self.interaction.refresh_stranger_observation()
        
        # Permission check: some commands are familiar-only
        if command in ["sing", "spin", "back"]:
            if self.state != State.FAMILIAR_STAY:
                if DEBUG:
                    print(f"Command '{command}' ignored: familiar-only (current state: {self.state.value})")
                return
        
        if command == "sing":
            self.interaction.do_sing(self.display, self.audio, self.voice_listener)
        elif command == "spin":
            self.interaction.do_spin(self.display, self.audio, self.motor, self.voice_listener)
        elif command == "back":
            print("'Back' command received; starting return...")
            self.interaction.end_familiar_interaction()
            self._start_returning()
        elif command == "friends":
            print("'Friends' command received; starting registration...")
            self._start_registration()

    def on_voice_wake(self, transcript):
        # Ignore wake words during registration
        if self.recognition.is_registering:
            return
        
        if self.action_recorder.is_returning:
            return
        
        # Only wake in IDLE state
        if self.state != State.IDLE:
            return
        
        print(f"Wake phrase detected: {transcript}")
        print("Woken up! Entering SEARCHING state.")
        
        self.action_recorder.clear()
        self.interaction.wake_up()
        
        self._change_state(State.SEARCHING)
        self.display.show_emotion("curious")
        self.audio.play_sound("awake")
        
        self.search.reset()
    
    def _change_state(self, new_state):
        if new_state != self.state:
            if DEBUG:
                print(f"\n{'='*50}")
                print(f"State transition: {self.state.value} -> {new_state.value}")
                print(f"{'='*50}")
            
            self.state = new_state
            self.state_start_time = time.time()
    

    def handle_face_recognition(self, frame):
        # Skip face recognition during registration
        if self.recognition.is_registering:
            return
        
        # Run recognition every N frames (performance)
        if self.recognition.should_skip_frame(self.frame_count):
            return
        
        # Detect and recognize faces
        results = self.face_recognizer.detect_and_recognize(frame)
        
        if len(results) == 0:
            # No face detected
            if DEBUG and self.frame_count % (RECOGNITION_INTERVAL * 30) == 0:
                print("Camera running... no face detected")
            
            if self.recognition.on_face_lost():
                if self.display.current_emotion in ["happy", "scared"]:
                    self.display.show_emotion("neutral")
            return
        
        self.recognition.on_face_detected()
        
        # Process detected face (first one only)
        face_rect, person_name, similarity = results[0]
        label = "familiar" if person_name else "stranger"
        self.recognition.update_counter(label)
        current_count = self.recognition.get_count(label)
        
        if person_name:
            if DEBUG:
                print(f"Familiar: {person_name} (similarity: {similarity:.2f}) | count: {current_count}/{EMOTION_CONFIRM_COUNT}")
        else:
            if DEBUG:
                print(f"Stranger (similarity: {similarity:.2f}) | count: {current_count}/{EMOTION_CONFIRM_COUNT}")
        
        if self.recognition.is_confirmed(label) and self.recognition.get_active_label() != label:
            desired_emotion = "happy" if label == "familiar" else "scared"
            self.display.show_emotion(desired_emotion, force=False)
            self.audio.play_sound(desired_emotion)
            self.recognition.set_active_label(label)
            
            # Motor action: happy -> forward; scared -> backward
            if self.motor_enabled and self.motor:
                if desired_emotion == "happy":
                    self.motor.move_for_duration('forward', MOTOR_MOVE_DURATION)
                elif desired_emotion == "scared":
                    self.motor.move_for_duration('backward', MOTOR_MOVE_DURATION)
        
        # Draw face box in debug window (simulation mode only)
        if SIMULATION_MODE and self.camera is not None:
            color = COLORS["green"] if person_name else COLORS["red"]
            display_label = f"{person_name}" if person_name else "Stranger"
            self.face_recognizer.detector.draw_face_box(
                frame, face_rect, display_label, color
            )
    
    def _start_registration(self):
        if self.recognition.start_registration():
            self.display.show_emotion("curious")
    
    def _handle_registration(self, frame):
        if self.recognition.should_skip_registration_frame(self.frame_count):
            return
        
        def on_complete():
            self.display.show_emotion("happy")
            self.audio.play_sound("friends")
            
            # After registration, switch to TRACKING to re-identify and enter familiar logic
            print("Registration complete; switching to TRACKING to re-identify...")
            self.recognition.reset_counters()
            self._change_state(State.TRACKING)
            
            if REGISTRATION_COMPLETE_AUTO_RECOVERY:
                self.interaction.start_voice_wake_emotion()
        
        self.recognition.handle_registration(frame, self.face_recognizer, on_complete)
    
    # State machine update methods
    
    def _update_idle(self):
        # Ensure the sleepy emotion is displayed
        # Do not force sleepy during registration
        if not self.recognition.is_registering:
            if self.display.current_emotion != "sleepy":
                self.display.show_emotion("sleepy")
    
    def _update_searching(self):
        # Searching counts as activity; refresh activity timer
        self.interaction.update_activity()
        
        # Check whether we are in the rotation pause window
        if self.search.is_in_rotation_pause():
            # Detect faces during the pause
            if self.search.detect_face_in_search(self.camera, self.face_recognizer, self.motor):
                self.recognition.reset_counters()
                self._change_state(State.TRACKING)
            return
        
        # Get next search action
        action_info = self.search.get_next_search_action()
        
        if action_info['action'] == 'complete':
            # Search complete; no face found; start returning
            print("Search complete; no face found; returning to start position")
            self._start_returning()
            return
        
        print(f"{action_info['message']}")
        
        # Execute rotation
        direction = 'left' if action_info['action'] == 'rotate_left' else 'right'
        found = self.search.rotate_and_detect(
            direction, action_info['duration'],
            self.motor, self.action_recorder,
            self.camera, self.face_recognizer
        )
        
        if found:
            # Face found; switch to tracking
            self.recognition.reset_counters()
            self._change_state(State.TRACKING)
            return
        
        self.search.update_rotation_time()
        self.search.advance_step()
    
    def _update_tracking(self):
        # Tracking counts as activity; refresh activity timer
        self.interaction.update_activity()
        
        if not self.face_enabled or self.camera is None:
            # Cannot recognize; start returning
            self._start_returning()
            return
        
        ret, frame = self.camera.read()
        if not ret:
            return
        
        # Recognize faces
        results = self.face_recognizer.detect_and_recognize(frame)
        
        if len(results) == 0:
            # Face lost
            if self.recognition.on_face_lost():
                # Face lost for too long; go back to searching
                print("Face lost; continuing search...")
                self.recognition.reset_counters()
                # Do not reset search state; continue from current position
                self._change_state(State.SEARCHING)
            return
        
        self.recognition.on_face_detected()
        
        # Process detected face (first one only)
        face_rect, person_name, similarity = results[0]
        label = "familiar" if person_name else "stranger"
        
        # Update counters
        self.recognition.update_counter(label)
        current_count = self.recognition.get_count(label)
        
        if person_name:
            if DEBUG:
                print(f"Familiar: {person_name} (similarity: {similarity:.2f}) | count: {current_count}/{EMOTION_CONFIRM_COUNT}")
        else:
            if DEBUG:
                print(f"Stranger (similarity: {similarity:.2f}) | count: {current_count}/{EMOTION_CONFIRM_COUNT}")
        
        # Once confirmed, execute action
        if self.recognition.is_confirmed(label):
            # First, center the face
            print("Centering face...")
            self.search.center_face(
                face_rect, self.motor, self.camera,
                self.face_recognizer, self.action_recorder, self.display
            )
            
            if person_name:
                # Familiar -> happy -> approach until near -> enter FAMILIAR_STAY
                print(f"Confirmed familiar: {person_name}! Approaching...")
                self.display.show_emotion("happy")
                self.audio.play_sound("happy")
                
                # Use continuous approach logic (pause on obstacle, resume after cleared)
                self.behavior_controller.approach_familiar_person()
                
                # Reset counters
                self.recognition.reset_counters()
                
                # Enter familiar interaction state
                self.interaction.start_familiar_interaction()
                self._change_state(State.FAMILIAR_STAY)
            else:
                # Stranger -> shocked -> enter shocked mode
                print("Confirmed stranger! Showing shocked emotion; entering shocked mode")
                self.display.show_emotion("shocked")
                self.audio.play_sound("thinking")  # Play thinking sound when seeing a stranger
                
                # Reset counters
                self.recognition.reset_counters()
                
                # Enter shocked state
                self.interaction.start_stranger_observation()
                self._change_state(State.SHOCKED)
    
    def _update_stranger_observe(self):
        # Ensure the scared emotion is displayed
        if self.display.current_emotion != "scared":
            self.display.show_emotion("scared")
        
        # Refresh activity time (stay active)
        self.interaction.update_activity()
        
        # Check observation timeout
        if self.interaction.check_stranger_timeout():
            print("Stranger observation timed out; returning to start position")
            self._start_returning()
            return
        
        # If stranger tracking is enabled, keep face centered
        if STRANGER_TRACK_ENABLED and self.face_enabled and self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                results = self.face_recognizer.detect_and_recognize(frame)
                
                if len(results) == 0:
                    # Face lost; check whether to end observation
                    if self.recognition.on_face_lost():
                        print("Stranger left; returning to start position")
                        self._start_returning()
                    return
                
                self.recognition.on_face_detected()
                
                # Get face position and adjust tracking
                face_rect = results[0][0]
                self.behavior_controller.track_face_position(face_rect)
    
    
    def _update_familiar_stay(self):
        # If audio is playing (e.g., singing), keep 'sing' emotion and avoid overrides
        if self.interaction.is_playing_audio:
            if self.display.current_emotion != "sing":
                self.display.show_emotion("sing")
        else:
            # Check excited state (triggered by touch)
            if time.time() < self.interaction.excited_until:
                if self.display.current_emotion != "excited":
                    self.display.show_emotion("excited")
            else:
                # Default emotion is happy
                if self.display.current_emotion != "happy":
                    self.display.show_emotion("happy")
        
        # 1) Check interaction timeout (if face lost too long)
        if self.interaction.check_familiar_timeout():
            self._start_returning()
            self.behavior_controller.reset_follow_state()
            return

        # 2) Get face info
        if not self.face_enabled or self.camera is None:
            return

        # 3) Execute follow logic
        face_detected = self.behavior_controller.follow_familiar_person()
        
        if face_detected:
            # Refresh activity time (do not timeout while face present)
            self.interaction.refresh_familiar_interaction()
    
    def _update_shocked(self):
        # Ensure shocked emotion is displayed
        # Do not force shocked during registration
        if not self.recognition.is_registering:
            if self.display.current_emotion != "shocked":
                self.display.show_emotion("shocked")
                # Play thinking/alert sound
                self.audio.play_sound("thinking")
        
        # Refresh activity time (stay active)
        self.interaction.update_activity()
        
        # Check observation timeout
        if self.interaction.check_stranger_timeout():
            print("Stranger observation timed out; returning to start position")
            self._start_returning()
            return
        
        # If stranger tracking is enabled, keep face centered
        if STRANGER_TRACK_ENABLED and self.face_enabled and self.camera is not None:
            ret, frame = self.camera.read()
            if ret:
                results = self.face_recognizer.detect_and_recognize(frame)
                
                if len(results) == 0:
                    # Face lost; check whether to end observation
                    if self.recognition.on_face_lost():
                        print("Stranger left; returning to start position")
                        self._start_returning()
                    return
                
                self.recognition.on_face_detected()
                
                # Get face position and adjust tracking
                face_rect = results[0][0]
                self.behavior_controller.track_face_position(face_rect)

    def _update_stranger_observe(self):
        # Ensure scared emotion is displayed
        # Do not force scared during registration
        if not self.recognition.is_registering:
            if self.display.current_emotion != "scared":
                self.display.show_emotion("scared")
                self.audio.play_sound("scared")
        
        # Refresh activity time
        self.interaction.update_activity()
        
        # Execute the backward action (only once)
        if not hasattr(self, '_fear_action_done') or not self._fear_action_done:
            print("Scared! Moving backward...")
            
            # Record the action for returning
            self.action_recorder.start_action('move', 'backward')
            
            if self.motor_enabled and self.motor:
                self.motor.move_for_duration('backward', 1.5)
            else:
                time.sleep(1.5)
            
            self.action_recorder.stop_action()
            
            self._fear_action_done = True
            self._fear_start_time = time.time()
            
            # Refresh stranger observation time (an interaction occurred)
            self.interaction.refresh_stranger_observation()
        
        # After a short delay, go back to SHOCKED
        if time.time() - self._fear_start_time > 0.5:  # Brief pause after moving backward
            print("Scared sequence finished; returning to shocked state")
            self._change_state(State.SHOCKED)
            self.display.show_emotion("shocked")
            del self._fear_action_done

    def _update_returning(self):
        # Refresh activity time while returning (avoid wake timeout)
        self.interaction.update_activity()
        
        # Execute one return action
        done = self.action_recorder.execute_return_action(
            self.motor,
            obstacle_callback=self.behavior_controller.check_obstacle_while_moving
        )
        
        if done:
            # Return finished
            self._change_state(State.IDLE)
            self.display.show_emotion("sleepy")
    
    def _start_returning(self):
        # If returning from familiar interaction, play bye
        if self.state == State.FAMILIAR_STAY:
             self.audio.play_sound("bye")

        if not self.action_recorder.has_actions():
            if DEBUG:
                print("No action history; returning directly to IDLE")
            self._change_state(State.IDLE)
            self.display.show_emotion("sleepy")
            return
        
        self.action_recorder.start_returning()
        self._change_state(State.RETURNING)
        self.display.show_emotion("neutral")  # Show neutral emotion while returning
    
    def run(self):
        while self.running:
            # Process keyboard debug commands
            self.debug_controller.process_commands()
            
            # If a blocking action is active (e.g., spin), skip state updates so the main loop
            # does not interfere with action execution.
            if self.interaction.blocking_action_active:
                time.sleep(0.1)
                # Still update the display to keep UI responsive
                self.display.update(delta_time=0.1)
                continue

            # State machine update
            if self.state == State.IDLE:
                self._update_idle()
            elif self.state == State.SEARCHING:
                self._update_searching()
            elif self.state == State.TRACKING:
                self._update_tracking()
            elif self.state == State.FAMILIAR_STAY:
                self._update_familiar_stay()
            elif self.state == State.STRANGER_OBSERVE:
                self._update_stranger_observe()
            elif self.state == State.SHOCKED:
                self._update_shocked()
            elif self.state == State.RETURNING:
                self._update_returning()
            
            # Skip most checks while returning
            if self.action_recorder.is_returning:
                # Only check ultrasonic obstacle avoidance
                if self.ultrasonic_enabled and self.ultrasonic:
                    if self.ultrasonic.is_object_near():
                        if self.motor_enabled and self.motor:
                            self.motor.stop()
                        if DEBUG:
                            print("Obstacle detected while returning; pausing")
                        self.audio.play_sound("obstacle")
                        time.sleep(0.5)  # Wait for the obstacle to clear
                
                # Update display
                self.display.update(delta_time=0.01)
                time.sleep(0.01)
                continue  # Skip all other checks
            
            # Check emotion recovery after voice wake
            if self.interaction.voice_wake_active and not self.recognition.is_registering:
                if self.interaction.check_voice_wake_emotion_timeout():
                    # Restore sleepy (default emotion in IDLE)
                    if self.state == State.IDLE:
                        self.display.show_emotion("sleepy", force=False)
                        if DEBUG:
                            print("Emotion restored to sleepy")
            
            # If audio finished playing, resume voice recognition
            if self.interaction.check_audio_finished(self.audio):
                print("Audio playback finished; resuming voice recognition")
                self._resume_voice_recognition()
            
            # Check ultrasonic sensors (proximity detection)
            # Only respond in IDLE
            if self.ultrasonic_enabled and not self.recognition.is_registering and self.state == State.IDLE:
                is_near = self.ultrasonic.is_object_near()
                
                if is_near:
                    # Object near: stop movement and show scared emotion
                    if self.display.current_emotion != "scared":
                        # Stop all motor movement immediately
                        if self.motor_enabled and self.motor:
                            self.motor.stop()
                        
                        self.display.show_emotion("scared", force=False)
                        self.audio.play_sound("scared")
                        if DEBUG:
                            status = self.ultrasonic.get_status()
                            triggered = ", ".join(status['triggered_sensors'])
                            print(f"Proximity alert! Stop now! Triggered sensors: {triggered}")
                    # Mark scared state as triggered by ultrasonic
                    self.interaction.trigger_ultrasonic_scared()
                else:
                    # Object left; check whether to recover
                    if self.interaction.check_ultrasonic_recovery(ULTRASONIC_RECOVERY_DELAY):
                        # Restore sleepy
                        if self.display.current_emotion == "scared" and self.state == State.IDLE:
                            self.display.show_emotion("sleepy", force=False)
                            if DEBUG:
                                print("Object cleared; restoring sleepy")
            

            # Handle touch events
            event = self.display.get_touch_event()
            
            if event:
                if event[0] == "quit":
                    self.running = False
                    continue
                
                elif event[0] == "touch_end":
                    _, x, y, duration = event
                    
                    # If audio is playing (e.g., singing), touching the screen stops playback
                    if self.interaction.is_playing_audio:
                        print("Touch detected; stopping audio playback")
                        self.audio.stop_all()
                        self.interaction.is_playing_audio = False
                        self._resume_voice_recognition()
                        # Restore emotion
                        if self.state == State.FAMILIAR_STAY:
                            self.display.show_emotion("happy")
                        elif self.state == State.IDLE:
                            self.display.show_emotion("sleepy")
                        continue

                    action = self.touch.handle_touch_end(duration)
                    
                    # If touched while SHOCKED, enter STRANGER_OBSERVE (scared/backward)
                    if self.state == State.SHOCKED:
                        print("Stranger touch detected! Entering scared state")
                        self._change_state(State.STRANGER_OBSERVE)
                        # Do not execute other touch actions
                        action = None
                    
                    # If in familiar interaction, refresh interaction time
                    if self.interaction.familiar_interaction_active:
                        self.interaction.refresh_familiar_interaction()
                        if action == "excited":
                            print("Familiar touch detected! Excited for 5 seconds")
                            self.interaction.excited_until = time.time() + 5.0
                        if DEBUG:
                            print("Familiar interaction: touch detected; refreshed timer")
                    
                    # Touch wake (in IDLE)
                    if action == "excited" and self.state == State.IDLE:
                        print("Touch wake! Entering SEARCHING state; enabling voice commands")
                        # Clear previous action history
                        self.action_recorder.clear()
                        # Mark as awake
                        self.interaction.wake_up()
                        # Switch state
                        self._change_state(State.SEARCHING)
                        self.display.show_emotion("curious")
                        self.audio.play_sound("awake")
                        self.search.reset()
            
            # Handle face registration
            if self.recognition.is_registering and self.face_enabled and self.camera is not None:
                ret, frame = self.camera.read()
                if ret:
                    self._handle_registration(frame)
            
            self.frame_count += 1
            
            # Update display (blink and delayed transitions)
            self.display.update(delta_time=0.01)
            
            # Periodic status output in SSH headless simulation mode (every 30s)
            if SIMULATION_MODE and (os.environ.get('SSH_CLIENT') or os.environ.get('SSH_TTY')):
                current_time = time.time()
                if current_time - self.last_status_time >= 30:
                    self.last_status_time = current_time
                    print(f"Running... state: {self.state.value} | frames: {self.frame_count}")
                    if self.face_enabled:
                        print(f"   Face recognition: enabled | known people: {self.face_recognizer.database.get_person_count()}")
            
            time.sleep(0.01)
        
        self.cleanup()
    
    def cleanup(self):
        print("\nCleaning up resources...")

        self.stop_voice_control()
        
        # Clean up ultrasonic sensors
        if self.ultrasonic_enabled and self.ultrasonic:
            self.ultrasonic.cleanup()
        
        # Clean up motor controller
        if self.motor_enabled and self.motor:
            self.motor.cleanup()
        
        if self.camera is not None:
            self.camera.release()
        
        cv2.destroyAllWindows()
        
        print("WALL-E shutdown")


if __name__ == "__main__":
    wall_e = WallE()
    try:
        wall_e.run()
    except KeyboardInterrupt:
        print("\n\nInterrupt signal received")
        wall_e.cleanup()
