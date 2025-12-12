#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emotion cycling test script.

Displays each emotion on the PiTFT in sequence; each emotion is shown for 3 seconds.
"""

import os
import sys
import time

# Set environment variables (required for hardware mode)
if not os.environ.get('SSH_CLIENT'):
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    os.environ['SDL_FBDEV'] = '/dev/fb0'

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, SIMULATION_MODE, EMOTIONS_DIR

# Try to import the framebuffer helper
try:
    from utils.framebuffer_helper import FramebufferHelper
except ImportError:
    FramebufferHelper = None


def main():
    """Main entry: cycle through and display all emotions."""
    
    print("=" * 50)
    print("Emotion cycle test")
    print("=" * 50)
    print(f"Screen size: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    print(f"Emotions dir: {EMOTIONS_DIR}")
    print(f"Simulation mode: {SIMULATION_MODE}")
    print("=" * 50)
    
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.mouse.set_visible(False)
    
    if SIMULATION_MODE:
        pygame.display.set_caption("Emotion cycle test")
    
    # Initialize framebuffer (hardware mode)
    fb_helper = None
    if not SIMULATION_MODE and FramebufferHelper:
        fb_helper = FramebufferHelper('/dev/fb0', SCREEN_WIDTH, SCREEN_HEIGHT)
        if fb_helper.is_available():
            print("Framebuffer mode enabled")
        else:
            print("Framebuffer unavailable")
            fb_helper = None
    
    # Get all emotion files
    emotions_dir = EMOTIONS_DIR
    if not os.path.exists(emotions_dir):
        print(f"ERROR: emotions directory does not exist: {emotions_dir}")
        return
    
    # Get all PNG files
    emotion_files = sorted([f for f in os.listdir(emotions_dir) if f.endswith('.png')])
    
    if not emotion_files:
        print("ERROR: no PNG files found in the emotions directory")
        return
    
    print(f"\nFound {len(emotion_files)} emotions:")
    for f in emotion_files:
        print(f"  - {f}")
    print()
    
    # Load all emotions
    emotions = {}
    for filename in emotion_files:
        emotion_name = filename.replace('.png', '')
        img_path = os.path.join(emotions_dir, filename)
        try:
            img = pygame.image.load(img_path)
            emotions[emotion_name] = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print(f"Loaded: {emotion_name}")
        except Exception as e:
            print(f"Failed to load: {emotion_name} - {e}")
    
    if not emotions:
        print("ERROR: no emotions were loaded successfully")
        return
    
    print(f"\nStarting to cycle through {len(emotions)} emotions (3 seconds each)...")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            for emotion_name, emotion_surface in emotions.items():
                print(f"Showing: {emotion_name}")
                
                # Draw to the pygame surface
                screen.blit(emotion_surface, (0, 0))
                pygame.display.flip()
                
                # Write to framebuffer (hardware mode)
                if fb_helper:
                    fb_helper.update_from_pygame_surface(screen)
                
                # Handle exit events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        raise KeyboardInterrupt
                
                # Wait 3 seconds
                time.sleep(3)
            
            print("\n--- Cycle complete; restarting ---\n")
    
    except KeyboardInterrupt:
        print("\n\nTest finished")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
