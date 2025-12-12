# modules/audio_handler.py

import pygame
import os
import time
from config import *

class AudioHandler:
    def __init__(self):
        try:
            # Most SFX files are 32000Hz; must match to avoid pitch shifts
            # Default 22050Hz -> slower (lower pitch)
            # 44100Hz -> faster (higher pitch)
            self.default_freq = 32000
            self.current_freq = self.default_freq
            pygame.mixer.init(frequency=self.default_freq)
            self.audio_available = True
        except Exception as e:
            if DEBUG:
                print(f"Audio initialization failed: {e}")
            self.audio_available = False
        
        # Playback control
        self.last_play_time = 0
        self.min_interval = 2  # Minimum interval between plays (seconds)
        
        # Load sound effects
        self.sounds = {}
        if self.audio_available:
            self.load_sounds()
        
        if DEBUG:
            if self.audio_available:
                print("Audio handler initialized")
            else:
                print("Audio unavailable; silent mode")
    
    def _set_frequency(self, freq):
        if self.current_freq == freq:
            return
            
        if DEBUG:
            print(f"Switching audio sample rate: {self.current_freq}Hz -> {freq}Hz")
            
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=freq)
            self.current_freq = freq
            self.load_sounds() # Reload SFX
        except Exception as e:
            print(f"Failed to switch sample rate: {e}")

    def load_sounds(self):
        sounds_dir = "resources/sounds"
        
        # Sound effect list
        sound_list = [
            "happy",    # Familiar person detected
            "scared",   # Stranger touch
            "excited",  # Familiar touch/spin
            "awake",    # Wake (was beep)
            "thinking", # Stranger detected
            "obstacle", # Obstacle encountered
            "friends",  # Registration success
            "bye"       # Familiar person left
        ]
        
        self.sounds = {} # Clear old
        for sound_name in sound_list:
            sound_path = os.path.join(sounds_dir, f"{sound_name}.wav")
            
            if os.path.exists(sound_path):
                try:
                    self.sounds[sound_name] = pygame.mixer.Sound(sound_path)
                    if DEBUG:
                        print(f"  Loaded SFX: {sound_name}")
                except Exception as e:
                    if DEBUG:
                        print(f"  Failed to load {sound_name}: {e}")
    
    def play_sound(self, sound_name, force=False):
        if not self.audio_available:
            return
            
        # Restore default sample rate if needed
        if self.current_freq != self.default_freq and not pygame.mixer.music.get_busy():
            self._set_frequency(self.default_freq)
            
        # Skip SFX while long audio is playing
        if not force and pygame.mixer.music.get_busy():
            if DEBUG:
                print(f"Long audio playing; skipping SFX: {sound_name}")
            return

        # Enforce cooldown interval
        current_time = time.time()
        if not force and (current_time - self.last_play_time < self.min_interval):
            if DEBUG:
                print(f"SFX too frequent; skipping: {sound_name} (cooldown)")
            return
        
        if sound_name and sound_name in self.sounds:
            try:
                # Allow mixing; do not check channel busy state
                self.sounds[sound_name].play()
                self.last_play_time = current_time
                if DEBUG:
                    print(f"Playing: {sound_name}")
            except Exception as e:
                if DEBUG:
                    print(f"Play failed: {e}")
    
    def play_file(self, file_path, blocking=False):
        """
        Play an audio file.
        
        Args:
            file_path: Audio file path (supports .wav, .mp3, .ogg)
            blocking: Whether to block until playback finishes
        
        Returns:
            bool: Whether playback started successfully
        """
        if not self.audio_available:
            print("Audio unavailable")
            return False
        
        if not os.path.exists(file_path):
            print(f"Audio file not found: {file_path}")
            return False
        
        try:
            # Check if already playing
            if pygame.mixer.music.get_busy():
                if DEBUG:
                    print(f"Other audio is playing; ignoring new request: {file_path}")
                return False

            # Special-case: for sing.wav, temporarily switch to 44100Hz
            is_singing = "sing.wav" in file_path
            if is_singing:
                self._set_frequency(44100)
            elif self.current_freq != self.default_freq:
                # Restore default frequency before playing other files
                self._set_frequency(self.default_freq)

            # Stop current playback
            pygame.mixer.music.stop()
            
            # Load and play
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Update last play time
            self.last_play_time = time.time()
            
            if DEBUG:
                print(f"Playing audio: {file_path}")
            
            if blocking:
                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                # Restore default frequency after playback
                if self.current_freq != self.default_freq:
                    self._set_frequency(self.default_freq)
            
            return True
            
        except Exception as e:
            print(f"Failed to play audio file: {e}")
            return False
    
    def stop_music(self):
        if self.audio_available:
            try:
                pygame.mixer.music.stop()
                # Restore default frequency after stopping
                if self.current_freq != self.default_freq:
                    self._set_frequency(self.default_freq)
            except:
                pass
    
    def is_music_playing(self):
        if self.audio_available:
            busy = pygame.mixer.music.get_busy()
            # If music stopped but the frequency wasn't restored, restore it
            if not busy and self.current_freq != self.default_freq:
                self._set_frequency(self.default_freq)
            return busy
        return False
    
    def stop_all(self):
        if self.audio_available:
            pygame.mixer.stop()
            pygame.mixer.music.stop()
