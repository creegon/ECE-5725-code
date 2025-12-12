import os
import time
from config import (
    DEBUG,
    VOICE_WAKE_DURATION, AWAKE_TIMEOUT, AWAKE_ACTIVITY_EXTEND,
    FAMILIAR_IDLE_TIMEOUT, SING_AUDIO_FILE,
    SEARCH_45DEG_DURATION, SEARCH_ROTATE_SPEED,
    MOTOR_MOVE_DURATION, SPIN_DURATION, SPIN_SPEED,
    STRANGER_TRACK_TIMEOUT
)


class InteractionHandler:
    def __init__(self):
        self.voice_wake_time = 0
        self.voice_wake_active = False
        self.voice_wake_duration = VOICE_WAKE_DURATION
        
        self.is_awake = False
        self.awake_time = 0
        self.awake_duration = AWAKE_TIMEOUT
        self.last_activity_time = 0
        
        self.is_playing_audio = False
        self.blocking_action_active = False
        
        self.familiar_interaction_active = False
        self.familiar_interaction_time = 0
        self.familiar_idle_timeout = FAMILIAR_IDLE_TIMEOUT
        
        self.stranger_observation_active = False
        self.stranger_observation_time = 0
        self.stranger_track_timeout = STRANGER_TRACK_TIMEOUT
        
        self.ultrasonic_scared_active = False
        self.ultrasonic_scared_time = 0
        
        self.excited_until = 0
    
    def wake_up(self):
        self.is_awake = True
        self.awake_time = time.time()
        self.last_activity_time = time.time()
    
    def update_activity(self):
        self.last_activity_time = time.time()

    def check_awake_timeout(self):
        if not self.is_awake:
            return False
        time_since_activity = time.time() - self.last_activity_time
        
        if AWAKE_ACTIVITY_EXTEND and time_since_activity < self.awake_duration:
            return False
        
        if time.time() - self.awake_time >= self.awake_duration:
            self.is_awake = False
            if DEBUG:
                print(f"Sleep timeout ({time_since_activity:.1f}s inactive)")
            return True
        
        return False
    
    def sleep(self):
        self.is_awake = False
    
    def start_voice_wake_emotion(self):
        self.voice_wake_time = time.time()
        self.voice_wake_active = True
    
    def check_voice_wake_emotion_timeout(self):
        if not self.voice_wake_active:
            return False
        
        if time.time() - self.voice_wake_time >= self.voice_wake_duration:
            self.voice_wake_active = False
            return True
        
        return False
    
    def start_playing_audio(self):
        self.is_playing_audio = True
    
    def check_audio_finished(self, audio):
        if self.is_playing_audio:
            if not audio.is_music_playing():
                self.is_playing_audio = False
                return True
        return False
    
    def start_familiar_interaction(self):
        self.familiar_interaction_active = True
        self.familiar_interaction_time = time.time()
        print(f"Enter familiar interaction state (timeout: {self.familiar_idle_timeout}s)")
    
    def refresh_familiar_interaction(self):
        if self.familiar_interaction_active:
            self.familiar_interaction_time = time.time()
    
    def check_familiar_timeout(self):
        if not self.familiar_interaction_active:
            return False
        
        time_since_interaction = time.time() - self.familiar_interaction_time
        if time_since_interaction >= self.familiar_idle_timeout:
            print(f"Familiar interaction timed out ({time_since_interaction:.1f}s)")
            self.familiar_interaction_active = False
            return True
        return False
    
    def end_familiar_interaction(self):
        self.familiar_interaction_active = False
    
    def start_stranger_observation(self):
        self.stranger_observation_active = True
        self.stranger_observation_time = time.time()
        print(f"Enter stranger observation state (timeout: {self.stranger_track_timeout}s)")
    
    def refresh_stranger_observation(self):
        if self.stranger_observation_active:
            self.stranger_observation_time = time.time()

    def check_stranger_timeout(self):
        if not self.stranger_observation_active:
            return False
        
        time_since_start = time.time() - self.stranger_observation_time
        if time_since_start >= self.stranger_track_timeout:
            self.stranger_observation_active = False
            return True
        return False
    
    def end_stranger_observation(self):
        self.stranger_observation_active = False
    
    def trigger_ultrasonic_scared(self):
        self.ultrasonic_scared_active = True
        self.ultrasonic_scared_time = time.time()
    
    def check_ultrasonic_recovery(self, recovery_delay):
        if not self.ultrasonic_scared_active:
            return False
        
        if time.time() - self.ultrasonic_scared_time >= recovery_delay:
            self.ultrasonic_scared_active = False
            return True
        return False
    
    def do_sing(self, display, audio, voice_listener):
        print("Action: sing")
        
        if voice_listener:
            voice_listener.pause()
        
        display.show_emotion("sing")
        
        if os.path.exists(SING_AUDIO_FILE):
            audio.play_file(SING_AUDIO_FILE, blocking=False)
            self.start_playing_audio()
        else:
            print(f"Sing audio file missing: {SING_AUDIO_FILE}")
            audio.play_sound("happy")
            if voice_listener:
                voice_listener.resume()
    
    def do_spin(self, display, audio, motor, voice_listener):
        print("Action: spin")
        
        self.blocking_action_active = True
        
        if voice_listener:
            voice_listener.pause()
        
        display.show_emotion("excited")
        audio.play_sound("excited")
        
        if motor is not None and motor.enabled:
            motor.turn_right(SPIN_SPEED)
            
            start_time = time.time()
            while time.time() - start_time < SPIN_DURATION:
                time.sleep(0.05)
                display.update(delta_time=0.05)
            
            motor.stop()
        else:
            print("Motor not enabled; cannot spin")
        
        if voice_listener:
            voice_listener.resume()
            
        self.blocking_action_active = False
        self.start_voice_wake_emotion()

    def do_emotion_action(self, emotion, motor, action_recorder, obstacle_callback=None):
        if motor is None or not motor.enabled:
            return
        
        motor.stop()
        time.sleep(0.15)
        
        if emotion == "happy":
            print("Action: happy (move forward)")
            action_recorder.start_action('move', 'forward')
            motor.move_for_duration(
                'forward', 
                MOTOR_MOVE_DURATION,
                obstacle_callback=obstacle_callback
            )
            action_recorder.stop_action()
        elif emotion == "scared":
            print("Action: scared (move backward)")
            action_recorder.start_action('move', 'backward')
            motor.move_for_duration('backward', MOTOR_MOVE_DURATION)
            action_recorder.stop_action()
