import pygame
import time
import os
import sys

def test_audio():
    print("Starting audio test...")
    
    # Check whether the audio file exists
    sound_file = "resources/sounds/awake.wav"
    if not os.path.exists(sound_file):
        print(f"ERROR: file not found: {sound_file}")
        # Try a fallback file
        if os.path.exists("resources/sounds/bye.wav"):
            sound_file = "resources/sounds/bye.wav"
        else:
            print("No hello.wav or bye.wav found in the directory")
            return

    print(f"Testing playback: {sound_file}")

    try:
        # Initialize pygame mixer
        # Note: do not set SDL_AUDIODRIVER=dummy so SDL can pick the best driver (e.g., ALSA)
        pygame.mixer.init()
        print("Pygame mixer initialized")
        
        # Load audio
        sound = pygame.mixer.Sound(sound_file)
        print(f"Audio loaded (duration: {sound.get_length():.2f}s)")
        
        # Play
        print("Playing...")
        sound.play()
        
        # Wait until playback finishes
        time.sleep(sound.get_length() + 0.5)
        print("Playback finished")
        
    except Exception as e:
        print(f"Playback failed: {e}")
        print("\nTip: if you see an ALSA error, try: sudo apt-get install libsdl2-mixer-2.0-0")

if __name__ == "__main__":
    test_audio()
