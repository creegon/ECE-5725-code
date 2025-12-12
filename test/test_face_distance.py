#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Face distance threshold test script.

Features:
- Robot keeps moving forward
- Detects faces in real time and prints face box size (pixels)
- Automatically stops when face width reaches the threshold
- Helps calibrate FACE_CLOSE_THRESHOLD

Usage:
1. Stand in front of the robot at some distance
2. Run: python3 test_face_threshold.py
3. The robot moves forward while printing face size
4. Stops at threshold, or press Ctrl+C to stop

Optional arguments:
    --threshold 220    Face width threshold in pixels (defaults to config.py)
    --speed 50         Forward speed (default 50)
    --no-move          Do not start the motor; only detect face size
"""

import cv2
import time
import argparse
import sys

# Import configuration
from config import (
    FACE_CLOSE_THRESHOLD, MOTOR_DEFAULT_SPEED, MOTOR_ENABLED,
    CAMERA_INDEX, DEBUG
)


def main():
    parser = argparse.ArgumentParser(description='Test face distance threshold')
    parser.add_argument('--threshold', type=int, default=FACE_CLOSE_THRESHOLD,
                        help=f'Face width threshold in pixels (default {FACE_CLOSE_THRESHOLD})')
    parser.add_argument('--speed', type=int, default=50,
                        help='Forward speed (0-100), default 50')
    parser.add_argument('--no-move', action='store_true',
                        help='Do not start the motor; only detect face size')
    args = parser.parse_args()
    
    threshold = args.threshold
    speed = args.speed
    no_move = args.no_move
    
    print("\n" + "=" * 60)
    print("Face distance threshold test")
    print("=" * 60)
    print(f"Face width threshold: {threshold}px")
    print(f"Forward speed: {speed}")
    print(f"Motor mode: {'disabled (detect only)' if no_move else 'enabled'}")
    print("=" * 60)
    print()
    
    # Initialize camera
    print("[1/3] Initializing camera...")
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        print("Unable to open camera!")
        sys.exit(1)
    print("Camera ready")
    
    # Initialize face detector
    print("[2/3] Initializing face detector...")
    try:
        from modules.face_recognizer import FaceRecognizer
        face_recognizer = FaceRecognizer()
        print("Face detector ready")
    except Exception as e:
        print(f"Face detector initialization failed: {e}")
        camera.release()
        sys.exit(1)
    
    # Initialize motor
    motor = None
    if not no_move and MOTOR_ENABLED:
        print("[3/3] Initializing motor...")
        try:
            from modules.motor_controller import MotorController
            motor = MotorController(default_speed=speed)
            if motor.enabled:
                print("Motor ready")
            else:
                print("Motor not enabled; will only detect face")
                motor = None
        except Exception as e:
            print(f"Motor initialization failed: {e}")
            motor = None
    else:
        print("[3/3] Skipping motor initialization")
    
    print()
    print("=" * 60)
    print("Starting test!")
    print("   - Prints face size in real time")
    print("   - Stops automatically at the threshold")
    print("   - Press Ctrl+C to stop manually")
    print("=" * 60)
    print()
    
    # State
    is_moving = False
    frame_count = 0
    last_print_time = time.time()
    print_interval = 0.2  # Print every 0.2s
    
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("Camera read failed")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Face detection
            results = face_recognizer.detect_and_recognize(frame)
            
            current_time = time.time()
            should_print = (current_time - last_print_time) >= print_interval
            
            if len(results) > 0:
                # Use the first face
                face_rect, person_name, similarity = results[0]
                face_width = face_rect['box'][2]
                face_height = face_rect['box'][3]
                face_x = face_rect['box'][0]
                face_y = face_rect['box'][1]
                
                # Progress percentage
                progress = min(100, int(face_width / threshold * 100))
                
                # Progress bar
                bar_len = 30
                filled = int(bar_len * progress / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                
                # Check threshold
                reached = face_width >= threshold
                
                if should_print:
                    name_str = f"[{person_name}]" if person_name else "[Unknown]"
                    status = "Reached!" if reached else "Moving"
                    print(f"\r{status} Face: {face_width:3d}x{face_height:3d}px | "
                          f"Threshold: {threshold}px | [{bar}] {progress:3d}% {name_str}   ", 
                          end="", flush=True)
                    last_print_time = current_time
                
                if reached:
                    # Reached threshold; stop
                    if motor and is_moving:
                        motor.stop()
                        is_moving = False
                    
                    print()  # Newline
                    print()
                    print("=" * 60)
                    print("Target distance reached!")
                    print(f"   Final face width: {face_width}px")
                    print(f"   Threshold: {threshold}px")
                    print("=" * 60)
                    break
                else:
                    # Not reached; keep moving
                    if motor and not is_moving:
                        motor.forward(speed)
                        is_moving = True
            else:
                # No face
                if should_print:
                    print(f"\rNo face detected... (frame: {frame_count})                              ", 
                          end="", flush=True)
                    last_print_time = current_time
                
                # Stop moving (safety)
                if motor and is_moving:
                    motor.stop()
                    is_moving = False
            
            time.sleep(0.05)  # 20 FPS
    
    except KeyboardInterrupt:
        print()
        print()
        print("Interrupted by user")
    
    finally:
        # Cleanup
        print()
        print("Cleaning up...")
        
        if motor:
            motor.stop()
            motor.cleanup()
            print("   Motor stopped")
        
        camera.release()
        print("   Camera released")
        
        print()
        print("Test finished")


if __name__ == "__main__":
    main()
