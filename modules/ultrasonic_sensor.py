# modules/ultrasonic_sensor.py

import time
from config import *

GPIO_AVAILABLE = False

if not SIMULATION_MODE and ULTRASONIC_ENABLED:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
        if DEBUG:
            print("Using RPi.GPIO for ultrasonic ranging")
    except (ImportError, RuntimeError) as e:
        print(f"RPi.GPIO not available: {e}")


class SingleUltrasonicSensor:
    def __init__(self, name, trig_pin, echo_pin, timeout=0.04):
        self.name = name
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.timeout = timeout
        self.enabled = False
        self.last_distance = -1
        
        # Skip unconfigured pins
        if trig_pin == 0 or echo_pin == 0:
            return
        
        if not GPIO_AVAILABLE:
            return
        
        try:
            GPIO.setup(trig_pin, GPIO.OUT)
            GPIO.setup(echo_pin, GPIO.IN)
            GPIO.output(trig_pin, False)
            self.enabled = True
            if DEBUG:
                print(f"  {name}: TRIG={trig_pin} ECHO={echo_pin}")
        except Exception as e:
            print(f"  {name}: Initialization failed - {e}")
    
    def get_distance(self):
        if not self.enabled:
            return -1
        
        # Single sample for speed; noise filtering is handled by higher-level logic.
        d = self._get_raw_distance()
        
        # Valid range: 0.5cm - 400cm
        # HC-SR04 spec says minimum 2cm, but it may sometimes read down to 0.5cm.
        # Returning -1 for <2cm could cause collisions (false negatives).
        if 0.5 < d < 400:
            self.last_distance = round(d, 2)
            return self.last_distance
        
        self.last_distance = -1
        return -1
    
    def _get_raw_distance(self):
        try:
            # Trigger pulse (10us)
            GPIO.output(self.trig_pin, False)
            time.sleep(0.000002)
            GPIO.output(self.trig_pin, True)
            time.sleep(0.00001)
            GPIO.output(self.trig_pin, False)
            
            # Wait for echo start
            timeout_time = time.time() + self.timeout
            pulse_start = time.time()
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start > timeout_time:
                    return -1
            
            # Wait for echo end
            pulse_end = time.time()
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end > timeout_time:
                    return -1
            
            # Compute distance
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # Speed of sound / 2
            return distance
            
        except Exception:
            return -1
    
    def is_near(self, threshold):
        distance = self.get_distance()
        if distance == -1:
            return False
        return distance <= threshold


class UltrasonicSensor:
    def __init__(self):
        self.sensors = []
        self.enabled = False
        self.measure_interval = ULTRASONIC_MEASURE_INTERVAL
        self.distance_threshold = ULTRASONIC_DISTANCE_THRESHOLD
        self.last_measure_time = 0
        self.debug_frame_count = 0
        
        # Cache
        self.cached_is_near = False
        self.cached_distances = {}
        
        if not ULTRASONIC_ENABLED:
            if DEBUG:
                print("Ultrasonic is disabled in config")
            return
        
        if SIMULATION_MODE:
            if DEBUG:
                print("Ultrasonic is in simulation mode")
            return
        
        if not GPIO_AVAILABLE:
            print("RPi.GPIO not available")
            return
        
        # Set GPIO mode
        try:
            GPIO.setmode(GPIO.BCM)
        except:
            pass  # Might already be set
        
        # Initialize all sensors
        print("  Initializing ultrasonic sensor array...")
        for name, trig, echo in ULTRASONIC_SENSORS:
            sensor = SingleUltrasonicSensor(name, trig, echo, ULTRASONIC_TIMEOUT)
            self.sensors.append(sensor)
            if sensor.enabled:
                self.enabled = True
        
        if self.enabled:
            enabled_count = sum(1 for s in self.sensors if s.enabled)
            print(f"Ultrasonic sensors initialized: {enabled_count}/{len(ULTRASONIC_SENSORS)} enabled")
            print(f"  Distance threshold: {self.distance_threshold} cm")
        else:
            print("No ultrasonic sensors available")
    
    def get_all_distances(self):
        distances = {}
        for sensor in self.sensors:
            if sensor.enabled:
                distances[sensor.name] = sensor.get_distance()
            else:
                distances[sensor.name] = -1
        self.cached_distances = distances
        return distances
    
    def is_object_near(self, use_cached=True):
        if not self.enabled:
            return False
        
        current_time = time.time()
        
        # Cache validity (50ms)
        if use_cached and (current_time - self.last_measure_time) < 0.05:
            return self.cached_is_near
            
        # Hardware protection: minimum interval 20ms to avoid echo interference
        if (current_time - self.last_measure_time) < 0.02:
            return self.cached_is_near
        
        # Update measurement
        self.last_measure_time = current_time
        self.debug_frame_count += 1
        
        # Check all sensors
        is_near = False
        triggered_sensors = []
        
        # Optimization: as soon as one sensor detects an obstacle, stop checking others.
        for sensor in self.sensors:
                # Call get_distance directly to avoid extra loops
                dist = sensor.get_distance()
                if dist != -1 and dist <= self.distance_threshold:
                    is_near = True
                    triggered_sensors.append(sensor.name)
                    # Stop on first trigger
                    break
        self.cached_is_near = is_near
        
        # Periodic debug output
        if DEBUG and self.debug_frame_count % ULTRASONIC_DEBUG_INTERVAL == 0:
            print(f"Sensor check: {' | '.join(triggered_sensors) if triggered_sensors else 'clear'}")
        
        return is_near
    
    def _print_all_distances(self, distances):
        parts = []
        for name, dist in distances.items():
            if dist != -1:
                parts.append(f"{name}: {dist:.1f}cm")
            else:
                parts.append(f"{name}: --")
        print(f"Ultrasonic: {' | '.join(parts)}")
    
    def get_status(self):
        distances = self.cached_distances if self.cached_distances else self.get_all_distances()
        triggered = [name for name, dist in distances.items() 
                     if dist != -1 and dist <= self.distance_threshold]
        
        return {
            'enabled': self.enabled,
            'distances': distances,
            'is_close': len(triggered) > 0,
            'triggered_sensors': triggered,
            'threshold': self.distance_threshold
        }
    
    def get_distance(self):
        distances = self.cached_distances if self.cached_distances else self.get_all_distances()
        valid_distances = [d for d in distances.values() if d != -1]
        if valid_distances:
            return min(valid_distances)
        return -1
    
    def cleanup(self):
        """Clean up GPIO resources."""
        if self.enabled and GPIO_AVAILABLE:
            try:
                pins = []
                for sensor in self.sensors:
                    if sensor.enabled:
                        pins.extend([sensor.trig_pin, sensor.echo_pin])
                if pins:
                    GPIO.cleanup(pins)
                if DEBUG:
                    print("Ultrasonic sensor GPIO cleaned up")
            except Exception as e:
                if DEBUG:
                    print(f"Error while cleaning ultrasonic GPIO: {e}")


# Test code
if __name__ == "__main__":
    print("="*60)
    print("Ultrasonic sensor array test (press Ctrl+C to quit)")
    print("="*60)
    
    manager = UltrasonicSensor()
    
    if not manager.enabled:
        print("No sensors available; exiting test")
        exit(1)
    
    print()
    print("Starting measurements...")
    print("-"*60)
    
    try:
        while True:
            is_near = manager.is_object_near(use_cached=False)
            status = manager.get_status()
            
            # Print all sensor distances
            parts = []
            for name, dist in status['distances'].items():
                if dist == -1:
                    parts.append(f"{name}:N/A")
                elif dist <= manager.distance_threshold:
                    parts.append(f"{name}:{dist:.1f}!")
                else:
                    parts.append(f"{name}:{dist:.1f}")
            
            alert = " PROXIMITY ALERT!" if is_near else "OK"
            print(f"{alert} | {' | '.join(parts)}")
            
            time.sleep(0.3)
    
    except KeyboardInterrupt:
        print("\n\nTest stopped")
    finally:
        manager.cleanup()
        print("Sensors cleaned up")
