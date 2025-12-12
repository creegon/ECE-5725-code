import RPi.GPIO as GPIO
import time

# --- Hardware configuration (adjust pins for your wiring) ---
# Pins used in the original script:
TRIG_PIN = 22
ECHO_PIN = 27

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

def get_distance():
    """
    Send an ultrasonic pulse and compute distance (cm).

    Preserves the original script logic, including timeout protection.
    """
    # 1. Ensure TRIG starts low to clear the signal
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.00001) 

    # 2. Send a 10us trigger pulse
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    pulse_start = time.time()
    pulse_end = time.time()
    
        # 3. Set a timeout (avoid infinite loops)
        # 0.04s ~= 40ms; sound round-trip ~13m, enough for the sensor max range (~4m)
    timeout = time.time() + 0.04 

        # 4. Wait for ECHO to go high
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
        if pulse_start > timeout:
            return -1 # Timeout error code

        # 5. Wait for ECHO to go low
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()
        if pulse_end > timeout:
            return -1 # Timeout error code

        # 6. Compute distance
    pulse_duration = pulse_end - pulse_start
    
        # distance = time * speed_of_sound (34300 cm/s) / 2
    distance = pulse_duration * 17150
    return round(distance, 2)

def main():
    print("Ultrasonic sensor test (press Ctrl+C to exit)")
    print(f"TRIG: {TRIG_PIN}, ECHO: {ECHO_PIN}")
    
    try:
        while True:
            dist = get_distance()
            
            if dist == -1:
                print("ERROR: measurement timeout (check wiring or distance)")
            else:
                print(f"Distance: {dist} cm")
            
            # Avoid measuring too frequently; allow echoes to dissipate
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up")

if __name__ == "__main__":
    main()