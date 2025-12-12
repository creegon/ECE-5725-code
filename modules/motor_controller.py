import time
import threading

try:
    from config import DEBUG, MOTOR_LEFT_SPEED_FACTOR, MOTOR_RIGHT_SPEED_FACTOR
except ImportError:
    DEBUG = True
    MOTOR_LEFT_SPEED_FACTOR = 1.0
    MOTOR_RIGHT_SPEED_FACTOR = 1.0

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("RPi.GPIO not available; running in simulation mode")


class MotorController:
    # BCM pin definitions
    LEFT_PIN1 = 16
    LEFT_PIN2 = 20
    LEFT_SPEED = 21
    
    RIGHT_PIN1 = 13
    RIGHT_PIN2 = 19
    RIGHT_SPEED = 26
    
    def __init__(self, default_speed=40):
        self.default_speed = default_speed
        self.enabled = GPIO_AVAILABLE
        self.left_pwm = None
        self.right_pwm = None
        self.is_moving = False
        self._move_thread = None
        self._stop_requested = False
        
        # Straight-line trim factors
        self.left_speed_factor = MOTOR_LEFT_SPEED_FACTOR
        self.right_speed_factor = MOTOR_RIGHT_SPEED_FACTOR
        
        if self.enabled:
            self._init_gpio()
    
    def _init_gpio(self):
        try:
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            
            GPIO.setwarnings(False)
            
            GPIO.setup(self.LEFT_PIN1, GPIO.OUT)
            GPIO.setup(self.LEFT_PIN2, GPIO.OUT)
            GPIO.setup(self.LEFT_SPEED, GPIO.OUT)
            GPIO.setup(self.RIGHT_PIN1, GPIO.OUT)
            GPIO.setup(self.RIGHT_PIN2, GPIO.OUT)
            GPIO.setup(self.RIGHT_SPEED, GPIO.OUT)
            
            # 1kHz PWM is a common default for DC motors
            self.left_pwm = GPIO.PWM(self.LEFT_SPEED, 1000)
            self.right_pwm = GPIO.PWM(self.RIGHT_SPEED, 1000)
            self.left_pwm.start(0)
            self.right_pwm.start(0)
            
            print(f"Motors ready (speed: {self.default_speed}%)")
            
        except Exception as e:
            print(f"Motor initialization failed: {e}")
            self.enabled = False
    
    def _motor_forward(self, pwm, pin1, pin2, speed=None):
        if not self.enabled: return
        speed = speed or self.default_speed
        GPIO.output(pin1, GPIO.HIGH)
        GPIO.output(pin2, GPIO.LOW)
        pwm.ChangeDutyCycle(speed)
    
    def _motor_backward(self, pwm, pin1, pin2, speed=None):
        if not self.enabled: return
        speed = speed or self.default_speed
        GPIO.output(pin1, GPIO.LOW)
        GPIO.output(pin2, GPIO.HIGH)
        pwm.ChangeDutyCycle(speed)
    
    def _motor_stop(self, pwm, pin1, pin2):
        if not self.enabled: return
        GPIO.output(pin1, GPIO.LOW)
        GPIO.output(pin2, GPIO.LOW)
        pwm.ChangeDutyCycle(0)
    
    def forward(self, speed=None):
        if not self.enabled:
            print("[SIM] Forward")
            return
        speed = speed or self.default_speed
        
        # Apply trim factors
        left_speed = min(100, int(speed * self.left_speed_factor))
        right_speed = min(100, int(speed * self.right_speed_factor))
        
        # Left wheel: counter-clockwise
        GPIO.output(self.LEFT_PIN1, GPIO.LOW)
        GPIO.output(self.LEFT_PIN2, GPIO.HIGH)
        self.left_pwm.ChangeDutyCycle(left_speed)
        
        # Right wheel: clockwise
        GPIO.output(self.RIGHT_PIN1, GPIO.HIGH)
        GPIO.output(self.RIGHT_PIN2, GPIO.LOW)
        self.right_pwm.ChangeDutyCycle(right_speed)
    
    def backward(self, speed=None):
        if not self.enabled:
            print("[SIM] Backward")
            return
        speed = speed or self.default_speed
        
        left_speed = min(100, int(speed * self.left_speed_factor))
        right_speed = min(100, int(speed * self.right_speed_factor))
        
        # Left wheel: clockwise
        GPIO.output(self.LEFT_PIN1, GPIO.HIGH)
        GPIO.output(self.LEFT_PIN2, GPIO.LOW)
        self.left_pwm.ChangeDutyCycle(left_speed)
        
        # Right wheel: counter-clockwise
        GPIO.output(self.RIGHT_PIN1, GPIO.LOW)
        GPIO.output(self.RIGHT_PIN2, GPIO.HIGH)
        self.right_pwm.ChangeDutyCycle(right_speed)
    
    def turn_left(self, speed=None):
        if not self.enabled:
            print("[SIM] Turn left")
            return
        speed = speed or self.default_speed
        
        # Both clockwise -> pivot left
        GPIO.output(self.LEFT_PIN1, GPIO.HIGH)
        GPIO.output(self.LEFT_PIN2, GPIO.LOW)
        self.left_pwm.ChangeDutyCycle(speed)
        GPIO.output(self.RIGHT_PIN1, GPIO.HIGH)
        GPIO.output(self.RIGHT_PIN2, GPIO.LOW)
        self.right_pwm.ChangeDutyCycle(speed)
    
    def turn_right(self, speed=None):
        if not self.enabled:
            print("[SIM] Turn right")
            return
        speed = speed or self.default_speed
        
        # Both counter-clockwise -> pivot right
        GPIO.output(self.LEFT_PIN1, GPIO.LOW)
        GPIO.output(self.LEFT_PIN2, GPIO.HIGH)
        self.left_pwm.ChangeDutyCycle(speed)
        GPIO.output(self.RIGHT_PIN1, GPIO.LOW)
        GPIO.output(self.RIGHT_PIN2, GPIO.HIGH)
        self.right_pwm.ChangeDutyCycle(speed)
    
    def stop(self):
        if not self.enabled:
            print("[SIM] Stop")
            return
        self._motor_stop(self.left_pwm, self.LEFT_PIN1, self.LEFT_PIN2)
        self._motor_stop(self.right_pwm, self.RIGHT_PIN1, self.RIGHT_PIN2)
        self.is_moving = False
    
    def brake(self):
        if not self.enabled: return
        
        # L298N logic: ENA=1, IN1=IN2 (LOW) => dynamic braking
        
        # Left wheel brake
        GPIO.output(self.LEFT_PIN1, GPIO.LOW)
        GPIO.output(self.LEFT_PIN2, GPIO.LOW)
        self.left_pwm.ChangeDutyCycle(100)
        
        # Right wheel brake
        GPIO.output(self.RIGHT_PIN1, GPIO.LOW)
        GPIO.output(self.RIGHT_PIN2, GPIO.LOW)
        self.right_pwm.ChangeDutyCycle(100)
        
        # Brake briefly
        time.sleep(0.1)
        
        # Then stop (coast)
        self.stop()

    def emergency_stop(self):
        self._stop_requested = True
        self.brake() # Use braking instead of a normal stop
        if DEBUG:
            print("Emergency stop!")
    
    def move_for_duration(self, direction, duration=2.0, speed=None, blocking=False, 
                          obstacle_callback=None):
        if self.is_moving:
            print("Motor is already moving; ignoring new command")
            return
        
        self._stop_requested = False
        
        def _move():
            self.is_moving = True
            
            # Execute movement
            if direction == 'forward':
                print(f"Moving forward for {duration} seconds...")
                self.forward(speed)
            elif direction == 'backward':
                print(f"Moving backward for {duration} seconds...")
                self.backward(speed)
            elif direction == 'left':
                print(f"Turning left for {duration} seconds...")
                self.turn_left(speed)
            elif direction == 'right':
                print(f"Turning right for {duration} seconds...")
                self.turn_right(speed)
            
            # Sleep in small steps to allow obstacle checks and interruption
            step_time = 0.1  # Check every 100ms
            elapsed = 0
            while elapsed < duration:
                if self._stop_requested:
                    print("Movement interrupted")
                    break
                
                # Obstacle check while moving forward
                if direction == 'forward' and obstacle_callback:
                    if obstacle_callback():
                        print("Obstacle detected; stopping forward movement!")
                        break
                
                time.sleep(step_time)
                elapsed += step_time
            
            # Stop
            self.stop()
            if not self._stop_requested:
                print("Movement complete")
        
        if blocking:
            _move()
        else:
            # Non-blocking: run in a background thread
            self._move_thread = threading.Thread(target=_move, daemon=True)
            self._move_thread.start()
    
    def rotate_with_detection(self, direction, total_steps, step_duration, speed, 
                               face_detector_callback):
        for step in range(total_steps):
            # Execute a small rotation step
            if self.enabled:
                if direction == 'left':
                    self.turn_left(speed)
                else:
                    self.turn_right(speed)
                time.sleep(step_duration)
                self.stop()
            else:
                # Simulation mode
                print(f"[SIM] {direction} step {step + 1}/{total_steps}")
                time.sleep(step_duration)
            
            # Brief pause and then detect face
            time.sleep(0.05)  # 50ms settle time
            
            if face_detector_callback:
                if face_detector_callback():
                    return True  # Face found
        
        return False  # Completed all steps; no face found
    
    def cleanup(self):
        if self.enabled:
            self.stop()
            if self.left_pwm:
                self.left_pwm.stop()
            if self.right_pwm:
                self.right_pwm.stop()
            print("Motor controller cleaned up")
