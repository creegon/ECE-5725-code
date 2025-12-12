#!/usr/bin/env python3
"""
Face tracking debug script.

Used to test face-centering behavior and display face position/offset in real time.

Two modes are supported:
- GUI mode (default): shows the camera feed
- Headless mode (--headless): text-only output, suitable for SSH sessions
"""

import cv2
import time
import sys
import os

# Detect whether to run in headless mode (SSH session or explicitly specified)
HEADLESS_MODE = (
    os.environ.get('SSH_CLIENT') is not None or 
    os.environ.get('SSH_TTY') is not None or
    '--headless' in sys.argv or
    '-H' in sys.argv
)

if HEADLESS_MODE:
    # Configure OpenCV to not use a GUI backend
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Import configuration
from config import (
    FACE_CENTER_TOLERANCE,
    FACE_CENTER_SPEED,
    FACE_CENTER_STEP_DURATION,
    FACE_CENTER_STEP_PAUSE,
    FACE_CENTER_CONFIRM_COUNT,
    MOTOR_ENABLED,
    MOTOR_DEFAULT_SPEED
)

from modules.face_recognizer import FaceRecognizer
from utils.camera_helper import open_camera

# Optional: motor control
try:
    from modules.motor_controller import MotorController
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    print("Motor module unavailable")


class FaceTrackingTester:
    def __init__(self, enable_motor=False):
        print("=" * 60)
        print("Face tracking debug tool")
        print("=" * 60)
        
        # Show current configuration
        print("\nCurrent configuration:")
        print(f"   FACE_CENTER_TOLERANCE = {FACE_CENTER_TOLERANCE:.0%} (tolerance)")
        print(f"   FACE_CENTER_SPEED = {FACE_CENTER_SPEED} (turn speed)")
        print(f"   FACE_CENTER_STEP_DURATION = {FACE_CENTER_STEP_DURATION}s (step duration)")
        print(f"   FACE_CENTER_STEP_PAUSE = {FACE_CENTER_STEP_PAUSE}s (pause between steps)")
        print(f"   FACE_CENTER_CONFIRM_COUNT = {FACE_CENTER_CONFIRM_COUNT} (debounce confirm count)")
        print()
        
        # Initialize camera and face recognition
        print("Initializing camera and face recognition...")
        self.face_recognizer = FaceRecognizer()
        self.camera = open_camera()
        
        if self.camera is None:
            print("Unable to open camera!")
            sys.exit(1)
        
        # Camera parameters
        self.frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        self.frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        print(f"   Camera resolution: {self.frame_width}x{self.frame_height}")
        
        # Motor control
        self.motor = None
        self.motor_enabled = False
        if enable_motor and MOTOR_AVAILABLE and MOTOR_ENABLED:
            try:
                self.motor = MotorController(default_speed=MOTOR_DEFAULT_SPEED)
                self.motor_enabled = self.motor.enabled
                print(f"   Motor control: {'enabled' if self.motor_enabled else 'disabled'}")
            except Exception as e:
                print(f"   Motor initialization failed: {e}")
        
        # Debounce state
        self._face_centered = False
        self._offset_confirm_count = 0
        self._last_offset_direction = None
        
        # Stats
        self.frame_count = 0
        self.detection_count = 0
        self.rotation_count = 0
        
        print("\nInitialization complete!")
        print()
        print("=" * 60)
        if HEADLESS_MODE:
            print("Headless mode (no GUI)")
            print("   - Prints face position and offset in real time")
            print("   - Progress bar: [---|---] center is frame center, '*' is face position")
            print("   - Status: Centered | Confirming | Tracking")
            if self.motor_enabled:
                print("   - Motor is enabled; will physically rotate")
            else:
                print("   - Motor is disabled (use -m to enable)")
            print("   - Press Ctrl+C to exit")
        else:
            print("GUI mode")
            print("   - Green box = face centered")
            print("   - Yellow box = confirming offset")
            print("   - Red box = adjustment needed")
            print()
            print("Keys:")
            print("   q - quit")
            print("   r - reset debounce state")
            print("   m - toggle motor control (if available)")
            print("   + - increase tolerance")
            print("   - - decrease tolerance")
        print("=" * 60)
        print()
    
    def calculate_offset(self, face_rect):
        """Compute face offset."""
        face_x = face_rect['box'][0]
        face_w = face_rect['box'][2]
        face_center_x = face_x + face_w / 2
        frame_center_x = self.frame_width / 2
        
        offset_ratio = (face_center_x - frame_center_x) / self.frame_width
        offset_direction = 'right' if offset_ratio > 0 else 'left'
        
        return {
            'face_x': face_x,
            'face_w': face_w,
            'face_center_x': face_center_x,
            'frame_center_x': frame_center_x,
            'offset_ratio': offset_ratio,
            'offset_direction': offset_direction,
            'is_centered': abs(offset_ratio) <= FACE_CENTER_TOLERANCE
        }
    
    def check_should_rotate(self, offset_info):
        """
        Check whether a rotation should happen (includes debounce logic).
        
        Returns:
            (should_rotate, status_message)
        """
        if offset_info['is_centered']:
            # Centered
            self._face_centered = True
            self._offset_confirm_count = 0
            self._last_offset_direction = None
            return False, "Centered"
        
        # Face is offset
        current_direction = offset_info['offset_direction']
        
        if self._face_centered:
            # Previously centered; offset detected, require confirmation
            if current_direction == self._last_offset_direction:
                self._offset_confirm_count += 1
            else:
                self._offset_confirm_count = 1
                self._last_offset_direction = current_direction
            
            if self._offset_confirm_count < FACE_CENTER_CONFIRM_COUNT:
                return False, f"Confirming {self._offset_confirm_count}/{FACE_CENTER_CONFIRM_COUNT}"
            
            # Reached confirm threshold
            self._face_centered = False
            self._offset_confirm_count = 0
            return True, f"Start tracking ({current_direction})"
        else:
            # Not centered previously; track immediately
            return True, f"Tracking ({current_direction})"
    
    def do_rotation(self, direction, check_after=True):
        """
        Perform a rotation step.
        
        Args:
            direction: 'left' or 'right'
            check_after: whether to check after rotation (for continuous tracking)
        
        Returns:
            bool: True if centered (no more rotation needed), False otherwise
        """
        if not self.motor_enabled or not self.motor:
            return True  # Without a motor, treat as complete
        
        if direction == 'right':
            self.motor.turn_right(FACE_CENTER_SPEED)
        else:
            self.motor.turn_left(FACE_CENTER_SPEED)
        
        time.sleep(FACE_CENTER_STEP_DURATION)
        self.motor.stop()
        time.sleep(FACE_CENTER_STEP_PAUSE)
        
        self.rotation_count += 1
        
        return False  # Assume more rotation may be needed
    
    def track_until_centered(self, initial_direction):
        """
        Continuously track until the face is centered.
        
        Args:
            initial_direction: initial rotation direction
        
        Returns:
            bool: True if centered successfully, False if face is lost
        """
        if not self.motor_enabled or not self.motor:
            return True
        
        max_rotations = 20  # Max rotation steps to avoid infinite loops
        current_direction = initial_direction
        last_offset = None  # Last offset to detect changes
        stuck_count = 0     # Stuck counter
        
        for i in range(max_rotations):
            # Perform one turn step
            print(f"       Motor turn: {current_direction} "
                f"(speed={FACE_CENTER_SPEED}, duration={FACE_CENTER_STEP_DURATION}s)")
            
            if current_direction == 'right':
                self.motor.turn_right(FACE_CENTER_SPEED)
            else:
                self.motor.turn_left(FACE_CENTER_SPEED)
            
            time.sleep(FACE_CENTER_STEP_DURATION)
            self.motor.stop()
            self.rotation_count += 1
            
            print("       Turn complete; checking face...")
            time.sleep(FACE_CENTER_STEP_PAUSE)
            
            # Important: clear camera buffer and fetch the latest frame
            # Grab a few frames to discard stale ones
            for _ in range(3):
                self.camera.grab()
            
            ret, frame = self.camera.read()
            if not ret:
                print("       Failed to read from camera")
                return False
            
            self.frame_count += 1
            results = self.face_recognizer.detect_and_recognize(frame)
            
            if len(results) == 0:
                print("       Face lost; stopping tracking")
                return False
            
            self.detection_count += 1
            face_rect = results[0][0]
            offset_info = self.calculate_offset(face_rect)
            
            # Generate a compact progress bar showing current position
            offset_ratio = offset_info['offset_ratio']
            bar = self._make_progress_bar(offset_ratio)
            
            # Detect if tracking is stuck (offset barely changes)
            if last_offset is not None:
                delta = abs(offset_ratio - last_offset)
                if delta < 0.02:  # Change less than 2%
                    stuck_count += 1
                    if stuck_count >= 3:
                        print(f"       Stuck detected: offset barely changed (delta={delta:.1%})")
                        print("       Possible causes: 1) motor not moving 2) camera frame buffering 3) face turns with robot")
                        # Try reversing direction
                        if stuck_count >= 5:
                            print("       Trying opposite direction...")
                            current_direction = 'left' if current_direction == 'right' else 'right'
                            stuck_count = 0
                else:
                    stuck_count = 0
            
            last_offset = offset_ratio
            
            if offset_info['is_centered']:
                print(f"       [{bar}] {offset_ratio:+5.1%} Centered!")
                self._face_centered = True
                self._offset_confirm_count = 0
                self._last_offset_direction = None
                return True
            else:
                # Update direction (may need to reverse)
                new_direction = offset_info['offset_direction']
                if new_direction != current_direction:
                    print(f"       [{bar}] {offset_ratio:+5.1%} Direction changed: {current_direction} -> {new_direction}")
                else:
                    print(f"       [{bar}] {offset_ratio:+5.1%} Continue {current_direction}...")
                current_direction = new_direction
        
        print(f"       WARNING: reached max rotation steps {max_rotations}")
        return False
    
    def _make_progress_bar(self, offset_ratio, width=30):
        """Generate a compact progress bar."""
        center_pos = width // 2
        face_pos = int(center_pos + offset_ratio * width)
        face_pos = max(0, min(width - 1, face_pos))
        
        tol_left = int(center_pos - FACE_CENTER_TOLERANCE * width)
        tol_right = int(center_pos + FACE_CENTER_TOLERANCE * width)
        
        bar = [' '] * width
        bar[center_pos] = '|'
        for i in range(tol_left, tol_right + 1):
            if bar[i] == ' ':
                bar[i] = '.'
        bar[face_pos] = '*'
        
        return ''.join(bar)
    
    def draw_debug_info(self, frame, face_rect, offset_info, status, should_rotate):
        """Draw debug information on the frame."""
        # Choose box color
        if offset_info['is_centered']:
            color = (0, 255, 0)  # Green - centered
        elif not should_rotate:
            color = (0, 255, 255)  # Yellow - confirming
        else:
            color = (0, 0, 255)  # Red - adjustment needed
        
        # Draw face box
        box = face_rect['box']
        x, y, w, h = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        # Draw center line
        frame_center = int(self.frame_width / 2)
        cv2.line(frame, (frame_center, 0), (frame_center, self.frame_height), (128, 128, 128), 1)
        
        # Draw tolerance region
        tolerance_left = int(frame_center - self.frame_width * FACE_CENTER_TOLERANCE)
        tolerance_right = int(frame_center + self.frame_width * FACE_CENTER_TOLERANCE)
        cv2.line(frame, (tolerance_left, 0), (tolerance_left, self.frame_height), (0, 255, 0), 1)
        cv2.line(frame, (tolerance_right, 0), (tolerance_right, self.frame_height), (0, 255, 0), 1)
        
        # Draw face center point
        face_center = int(offset_info['face_center_x'])
        cv2.circle(frame, (face_center, y + h // 2), 5, color, -1)
        cv2.line(frame, (face_center, y), (face_center, y + h), color, 2)
        
        # Draw offset arrow
        if not offset_info['is_centered']:
            arrow_start = (frame_center, 30)
            arrow_end = (face_center, 30)
            cv2.arrowedLine(frame, arrow_start, arrow_end, (0, 0, 255), 2)
        
        # Text info
        info_lines = [
            f"Frame: {self.frame_count} | Detections: {self.detection_count} | Rotations: {self.rotation_count}",
            f"Face Center: {offset_info['face_center_x']:.0f} | Frame Center: {offset_info['frame_center_x']:.0f}",
            f"Offset: {offset_info['offset_ratio']:.1%} ({offset_info['offset_direction']})",
            f"Tolerance: +/-{FACE_CENTER_TOLERANCE:.0%} | Status: {status}",
            f"Motor: {'ON' if self.motor_enabled else 'OFF'} | Centered: {self._face_centered}",
        ]
        
        y_offset = 20
        for line in info_lines:
            cv2.putText(frame, line, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
        
        # Draw status indicator
        status_color = (0, 255, 0) if offset_info['is_centered'] else ((0, 255, 255) if not should_rotate else (0, 0, 255))
        cv2.circle(frame, (self.frame_width - 30, 30), 20, status_color, -1)
        
        return frame
    
    def run(self):
        """Main loop."""
        if HEADLESS_MODE:
            self.run_headless()
        else:
            self.run_gui()
    
    def run_headless(self):
        """Run in headless mode (no GUI)."""
        global FACE_CENTER_TOLERANCE
        
        print("Starting (headless mode)...")
        print("   Press Ctrl+C to exit\n")
        
        # Characters used for the progress bar
        BAR_WIDTH = 40
        
        last_status = ""
        no_face_count = 0
        
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    print("ERROR: failed to read from camera")
                    break
                
                self.frame_count += 1
                
                # Face detection
                results = self.face_recognizer.detect_and_recognize(frame)
                
                if len(results) == 0:
                    no_face_count += 1
                    # Print "no face" status every 30 frames
                    if no_face_count % 30 == 1:
                        print(f"[{self.frame_count:4d}] No face detected...")
                else:
                    no_face_count = 0
                    self.detection_count += 1
                    face_rect = results[0][0]
                    
                    # Compute offset
                    offset_info = self.calculate_offset(face_rect)
                    
                    # Check whether to rotate
                    should_rotate, status = self.check_should_rotate(offset_info)
                    
                    # Build a visual progress bar
                    offset_ratio = offset_info['offset_ratio']
                    center_pos = BAR_WIDTH // 2
                    face_pos = int(center_pos + offset_ratio * BAR_WIDTH)
                    face_pos = max(0, min(BAR_WIDTH - 1, face_pos))
                    
                    # Tolerance range
                    tol_left = int(center_pos - FACE_CENTER_TOLERANCE * BAR_WIDTH)
                    tol_right = int(center_pos + FACE_CENTER_TOLERANCE * BAR_WIDTH)
                    
                    # Construct the bar
                    bar = [' '] * BAR_WIDTH
                    bar[center_pos] = '|'  # Center line
                    for i in range(tol_left, tol_right + 1):
                        if bar[i] == ' ':
                            bar[i] = '.'
                        bar[face_pos] = '*'  # Face position
                    
                    bar_str = ''.join(bar)
                    
                    # Status tag
                    if offset_info['is_centered']:
                        icon = '[OK]'
                    elif not should_rotate:
                        icon = '[WAIT]'
                    else:
                        icon = '[ROT]'
                    
                    # Output
                    motor_indicator = " [M]" if self.motor_enabled else ""
                    output = (f"[{self.frame_count:4d}] [{bar_str}] "
                              f"{offset_ratio:+6.1%} {icon} {status}{motor_indicator}")
                    
                    # Print only on status change or every 5 frames
                    if status != last_status or self.frame_count % 5 == 0:
                        print(output)
                        last_status = status
                    
                    # Track (if needed) - continue until centered
                    if should_rotate and self.motor_enabled:
                        self.track_until_centered(offset_info['offset_direction'])
                
                time.sleep(0.03)  # ~30 fps
        
        except KeyboardInterrupt:
            print("\nInterrupted")
        
        finally:
            self.cleanup()
    
    def run_gui(self):
        """Run in GUI mode."""
        global FACE_CENTER_TOLERANCE
        
        print("Starting (GUI mode)...")
        print("   Press 'q' to exit\n")
        
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    print("ERROR: failed to read from camera")
                    break
                
                self.frame_count += 1
                
                # Face detection
                results = self.face_recognizer.detect_and_recognize(frame)
                
                if len(results) == 0:
                    # No face
                    cv2.putText(frame, "No face detected", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame, f"Frame: {self.frame_count}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    self.detection_count += 1
                    face_rect = results[0][0]
                    
                    # Compute offset
                    offset_info = self.calculate_offset(face_rect)
                    
                    # Check whether to rotate
                    should_rotate, status = self.check_should_rotate(offset_info)
                    
                    # Draw debug info
                    frame = self.draw_debug_info(frame, face_rect, offset_info, status, should_rotate)
                    
                    # Rotate (if needed)
                    if should_rotate and self.motor_enabled:
                        self.do_rotation(offset_info['offset_direction'])
                    
                    # Console output
                    if self.frame_count % 10 == 0:  # Every 10 frames
                        print(f"[{self.frame_count:4d}] Offset: {offset_info['offset_ratio']:+6.1%} "
                            f"Dir: {offset_info['offset_direction']:5s} "
                            f"Status: {status}")
                
                # Show frame
                cv2.imshow("Face Tracking Debug", frame)
                
                # Handle keys
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\nExiting...")
                    break
                elif key == ord('r'):
                    self._face_centered = False
                    self._offset_confirm_count = 0
                    self._last_offset_direction = None
                    print("Debounce state reset")
                elif key == ord('m'):
                    if MOTOR_AVAILABLE and self.motor:
                        self.motor_enabled = not self.motor_enabled
                        print(f"Motor control: {'ON' if self.motor_enabled else 'OFF'}")
                elif key == ord('+') or key == ord('='):
                    FACE_CENTER_TOLERANCE = min(0.5, FACE_CENTER_TOLERANCE + 0.02)
                    print(f"Tolerance increased to: {FACE_CENTER_TOLERANCE:.0%}")
                elif key == ord('-'):
                    FACE_CENTER_TOLERANCE = max(0.02, FACE_CENTER_TOLERANCE - 0.02)
                    print(f"Tolerance decreased to: {FACE_CENTER_TOLERANCE:.0%}")
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\nInterrupted")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        print("\n" + "=" * 60)
        print("Stats:")
        print(f"   Total frames: {self.frame_count}")
        print(f"   Detections: {self.detection_count} ({self.detection_count/max(1,self.frame_count)*100:.1f}%)")
        print(f"   Rotations: {self.rotation_count}")
        if self.motor_enabled:
            total_rotation_time = self.rotation_count * (FACE_CENTER_STEP_DURATION + FACE_CENTER_STEP_PAUSE)
            print(f"   Total rotation time: {total_rotation_time:.2f}s")
        print("=" * 60)
        
        if self.camera:
            self.camera.release()
        
        if not HEADLESS_MODE:
            cv2.destroyAllWindows()
        
        if self.motor:
            self.motor.stop()
            self.motor.cleanup()
        
        print("\nCleanup complete")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Face tracking debug tool")
    parser.add_argument('--motor', '-m', action='store_true', 
                        help='Enable motor control')
    parser.add_argument('--headless', '-H', action='store_true',
                        help='Headless mode (no GUI; auto-detect SSH)')
    args = parser.parse_args()
    
    tester = FaceTrackingTester(enable_motor=args.motor)
    tester.run()


if __name__ == "__main__":
    main()
