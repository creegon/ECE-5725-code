"""Simple motor test script.

Verifies that both wheels can run.
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: this script must be run on a Raspberry Pi")
    print("Install: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

# Motor pin configuration (BCM numbering)
LEFT_PIN1 = 16
LEFT_PIN2 = 20
LEFT_SPEED = 21

RIGHT_PIN1 = 13
RIGHT_PIN2 = 19
RIGHT_SPEED = 26

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(LEFT_PIN1, GPIO.OUT)
GPIO.setup(LEFT_PIN2, GPIO.OUT)
GPIO.setup(LEFT_SPEED, GPIO.OUT)
GPIO.setup(RIGHT_PIN1, GPIO.OUT)
GPIO.setup(RIGHT_PIN2, GPIO.OUT)
GPIO.setup(RIGHT_SPEED, GPIO.OUT)

# Initialize PWM
left_pwm = GPIO.PWM(LEFT_SPEED, 1000)
right_pwm = GPIO.PWM(RIGHT_SPEED, 1000)
left_pwm.start(0)
right_pwm.start(0)


def motor_stop(pwm, pin1, pin2):
    """Stop a motor."""
    GPIO.output(pin1, GPIO.LOW)
    GPIO.output(pin2, GPIO.LOW)
    pwm.ChangeDutyCycle(0)


def motor_cw(pwm, pin1, pin2, speed=80):
    """Rotate clockwise."""
    GPIO.output(pin1, GPIO.HIGH)
    GPIO.output(pin2, GPIO.LOW)
    pwm.ChangeDutyCycle(speed)


def motor_ccw(pwm, pin1, pin2, speed=80):
    """Rotate counter-clockwise."""
    GPIO.output(pin1, GPIO.LOW)
    GPIO.output(pin2, GPIO.HIGH)
    pwm.ChangeDutyCycle(speed)


def move_forward():
    """Move forward."""
    print("  -> Forward")
    motor_cw(left_pwm, LEFT_PIN1, LEFT_PIN2)
    motor_cw(right_pwm, RIGHT_PIN1, RIGHT_PIN2)


def move_backward():
    """Move backward."""
    print("  -> Backward")
    motor_ccw(left_pwm, LEFT_PIN1, LEFT_PIN2)
    motor_ccw(right_pwm, RIGHT_PIN1, RIGHT_PIN2)


def turn_left():
    """Turn left."""
    print("  -> Left")
    motor_ccw(left_pwm, LEFT_PIN1, LEFT_PIN2)
    motor_cw(right_pwm, RIGHT_PIN1, RIGHT_PIN2)


def turn_right():
    """Turn right."""
    print("  -> Right")
    motor_cw(left_pwm, LEFT_PIN1, LEFT_PIN2)
    motor_ccw(right_pwm, RIGHT_PIN1, RIGHT_PIN2)


def stop_all():
    """Stop all motors."""
    print("  -> Stop")
    motor_stop(left_pwm, LEFT_PIN1, LEFT_PIN2)
    motor_stop(right_pwm, RIGHT_PIN1, RIGHT_PIN2)


def cleanup():
    """Clean up resources."""
    stop_all()
    left_pwm.stop()
    right_pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")


def run_test():
    """Run the motor test."""
    print("="*50)
    print("Motor test")
    print("="*50)
    print(f"Left motor: GPIO {LEFT_PIN1}, {LEFT_PIN2}, PWM={LEFT_SPEED}")
    print(f"Right motor: GPIO {RIGHT_PIN1}, {RIGHT_PIN2}, PWM={RIGHT_SPEED}")
    print("="*50)
    print()
    
    test_duration = 2  # Duration for each action (seconds)
    pause_duration = 1  # Pause between actions (seconds)
    
    try:
        # Test 1: Forward
        print("[1/4] Testing forward...")
        move_forward()
        time.sleep(test_duration)
        stop_all()
        time.sleep(pause_duration)
        
        # Test 2: Backward
        print("[2/4] Testing backward...")
        move_backward()
        time.sleep(test_duration)
        stop_all()
        time.sleep(pause_duration)
        
        # Test 3: Left
        print("[3/4] Testing left...")
        turn_left()
        time.sleep(test_duration)
        stop_all()
        time.sleep(pause_duration)
        
        # Test 4: Right
        print("[4/4] Testing right...")
        turn_right()
        time.sleep(test_duration)
        stop_all()
        
        print()
        print("="*50)
        print("Motor test complete!")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    finally:
        cleanup()


if __name__ == "__main__":
    run_test()
