# config.py
"""
WALL-E full system configuration.

Integrates touch interaction and face recognition.
"""

import os

# Runtime mode
# Auto-detect: if running via SSH, force simulation mode
_is_ssh = os.environ.get('SSH_CLIENT') or os.environ.get('SSH_TTY')

# Emotion animation settings
EMOTION_CHANGE_DELAY = 0.3      # Minimum interval between emotion changes (seconds), to prevent rapid flicker
EMOTION_CONFIRM_COUNT = 3       # How many consistent recognition results are required before switching emotion
NO_FACE_RESET_COUNT = 30        # How many consecutive "no face" frames before considering the face lost (increase to reduce false resets)


SIMULATION_MODE = False  # Force hardware mode even when running via SSH

# If you want to auto-switch to simulation mode when using SSH, uncomment below
# SIMULATION_MODE = bool(_is_ssh)

# Debug
DEBUG = True                    # Whether to print debug information
# Show a camera preview window (requires a GUI environment)
# Set True on a desktop; set False when running on Raspberry Pi via SSH
SHOW_CAMERA_WINDOW = False  # True: show debug window; False: headless/no window

# Display
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Camera
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# Touch
SHORT_TOUCH = 0.5               # Short press: happy
MEDIUM_TOUCH = 2.0              # Medium press: excited
LONG_TOUCH_REGISTER = 3.0       # Long press: trigger face registration

# Motor control
MOTOR_ENABLED = True            # Enable motor control
MOTOR_DEFAULT_SPEED = 60        # Default speed (0-100), recommended range 50-80
MOTOR_MIN_SPEED = 50            # Minimum usable speed (below this the motor may not start)
MOTOR_MOVE_DURATION = 2.0       # Move duration (seconds)
MOTOR_ROTATE_DURATION = 0.5     # Time to rotate 45 degrees (seconds); tune on hardware
# Left/right motor speed compensation (to correct drift when driving straight)
# If the robot drifts right: increase LEFT or decrease RIGHT
# If the robot drifts left: increase RIGHT or decrease LEFT
MOTOR_LEFT_SPEED_FACTOR = 0.90  # Left motor speed factor (0.8-1.2)
MOTOR_RIGHT_SPEED_FACTOR = 1.0  # Right motor speed factor (0.8-1.2)

# State machine
SEARCH_CYCLES = 4               # Search-mode cycles (scan left/right)
SEARCH_ROTATE_PAUSE = 0.5       # Pause after each rotation (seconds) - for face detection
SEARCH_ROTATE_SPEED = 36        # Search rotation speed (0-100); slower reduces motion blur and improves detection
SEARCH_45DEG_DURATION = 1.5     # Time to rotate 45 degrees (seconds); increase if speed is lowered
TRACKING_TIMEOUT = 5.0          # Tracking timeout (seconds); returns to IDLE after timeout

# Stepped rotation (jerky) settings
ROTATE_STEP_DURATION = 0.15     # Rotation time per step (seconds)
ROTATE_STEP_PAUSE = 0.08        # Pause after each step (seconds), for detection

# Familiar-person interaction
FAMILIAR_IDLE_TIMEOUT = 20.0    # How long to wait without interaction before returning (seconds)

# Stranger observation
STRANGER_OBSERVE_DURATION = 1.5  # How long to observe a stranger (seconds)
STRANGER_TRACK_ENABLED = True    # Enable stranger tracking (keep face centered)
STRANGER_TRACK_TIMEOUT = 55.0     # Maximum stranger tracking time (seconds)

# Face centering
FACE_CENTER_ENABLED = True      # Enable face-centering behavior
FACE_CENTER_TOLERANCE = 0.16    # Centering tolerance (fraction of frame width); within this range counts as centered
FACE_CENTER_SPEED = 50          # Centering rotation speed (0-100); must be > MOTOR_MIN_SPEED
FACE_CENTER_TIMEOUT = 3.0       # Max centering time (seconds); stops after timeout
FACE_CENTER_STEP_DURATION = 0.15  # Rotation time per step while centering (seconds); shorter than search for fine adjustment
FACE_CENTER_STEP_PAUSE = 0.50     # Pause after each centering step (seconds)
FACE_CENTER_CONFIRM_COUNT = 3     # Debounce: how many consecutive offset frames before re-tracking after being centered

# Ultrasonic sensors
ULTRASONIC_ENABLED = True       # Enable ultrasonic sensors
ULTRASONIC_DISTANCE_THRESHOLD = 8.0  # Distance threshold (cm); increase to leave braking margin
ULTRASONIC_TIMEOUT = 0.04       # Measurement timeout (seconds)
ULTRASONIC_MEASURE_INTERVAL = 0.1    # Measurement interval (seconds), to avoid measuring too frequently
ULTRASONIC_RECOVERY_DELAY = 2.0      # Delay before returning to neutral after an object leaves (seconds)
ULTRASONIC_DEBUG_INTERVAL = 30       # Debug print interval (frames): how often to print all sensor distances

# Ultrasonic sensor GPIO pinout (BCM numbering)
# Format: (name, TRIG pin, ECHO pin)
# PiTFT uses: GPIO 18 (backlight), 24 (touch), 25 (DC), 7/8/9/10/11 (SPI)
# Motors use: GPIO 13, 16, 19, 20, 21, 26
ULTRASONIC_SENSORS = [
    ("front",  6, 5),     # Front sensor
    ("left",   22, 27),   # Left sensor
    ("right",  4, 17),   # Right sensor
]

# YuNet face detection
# YuNet model path (OpenCV DNN)
YUNET_MODEL_PATH = "models/face_detection_yunet_2023mar.onnx"

# YuNet parameters
YUNET_INPUT_SIZE = (320, 320)   # Input size
YUNET_CONF_THRESHOLD = 0.75     # Confidence threshold (higher is stricter; 0.6 -> 0.75 reduces false positives)
YUNET_NMS_THRESHOLD = 0.3       # NMS threshold (suppress overlapping boxes)
YUNET_TOP_K = 5000              # Maximum number of candidate boxes
MIN_FACE_SIZE = 60              # Minimum face size (pixels), filter tiny false detections

# Distance estimation based on face size
# If the face width reaches this pixel value, consider it close enough and stop moving forward.
# Calibrate for your camera and environment:
# - Measure face-box width at your target distance (e.g., 10 cm)
# - Put that value into FACE_CLOSE_THRESHOLD
# Reference: 230px≈10cm, 200px≈15cm, 180px≈20cm, 150px≈30cm
FACE_CLOSE_THRESHOLD = 190      # Face width threshold (pixels); above this means too close
FACE_CLOSE_ENABLED = True       # Enable face-size-based distance detection

# Distance control (new)
FACE_APPROACH_TARGET_DISTANCE = 30.0  # Target stopping distance (cm), based on ultrasonic (most reliable)
FACE_CLOSE_EYE_DISTANCE = 85          # Eye-to-eye distance threshold (pixels); more stable than face width as a fallback

# SFace face recognition
# SFace model path (OpenCV DNN)
SFACE_MODEL_PATH = "models/face_recognition_sface_2021dec.onnx"

# SFace input
SFACE_INPUT_SIZE = (112, 112)   # Standard input size
EMBEDDING_SIZE = 128             # Embedding vector size

# Face recognition
# Similarity threshold (cosine similarity, 0-1)
# RECOGNITION_THRESHOLD = 0.363   # SFace recommended threshold (official guidance)
# Values above 0.6 can easily classify familiar people as strangers; 0.6 is a more balanced trade-off.
RECOGNITION_THRESHOLD = 0.6       # Familiar-person recognition threshold
RECOGNITION_MARGIN = 0.0         # Minimum gap between the best and second-best match
CONFIDENCE_HIGH = 0.5           # High-confidence threshold (> 0.5)

# Face registration
SAMPLES_PER_PERSON = 5          # Number of samples per person
SAMPLE_INTERVAL = 3             # Collect one sample every N frames (faster collection)
REGISTRATION_COMPLETE_AUTO_RECOVERY = True  # Auto-recover to neutral after registration (True: recover after 5s; False: stay happy until next recognition)

# ============ Data paths ============
DATA_DIR = "data"
FACE_DATABASE_PATH = os.path.join(DATA_DIR, "face_features.pkl")

# Emotion image directory (choose different emotion styles)
# EMOTIONS_DIR = "resources/emotions"        # Default WALL-E style
EMOTIONS_DIR = "resources/emotions_saki"  # Saki style (uncomment to use)

# ============ Performance tuning ============
RECOGNITION_INTERVAL = 2        # Run recognition every N frames (performance)
USE_THREADING = False           # Threading disabled for now (simpler debugging)

# ============ Voice wakeup ============
VOICE_ENABLED = True
VOICE_ENGINE = "vosk"          # Options: "vosk" (offline) / "google" (online)
VOICE_WAKE_PHRASES = [
    "hey",
    "hello"
]
# Voice commands (different from wake words; these trigger actions)
VOICE_COMMANDS = {
    "sing": ["sing", "sing a song", "play music", "music"],
    "spin": ["spin", "turn around", "rotate", "dance"],
    "friends": ["of course"],
    "back": ["back", "go back", "return", "go home"],
}
VOICE_MIC_NAME = "ME6S"        # Fuzzy match in the microphone name list
VOICE_MIC_INDEX = None          # Set an exact index if known; otherwise keep None for auto-detect
VOICE_LISTEN_TIMEOUT = 2.0      # Max listen wait time (seconds) - shorter reduces latency
VOICE_PHRASE_TIME_LIMIT = 3.0   # Max single-phrase duration (seconds) - shorter avoids buildup
VOICE_LANGUAGE = "en-US"       # Speech recognition language
# VOSK_MODEL_PATH = os.path.join("models", "vosk-model-en-us-daanzu-20200905")
VOSK_MODEL_PATH = os.path.join("models", "vosk-model-small-en-us-0.15")
VOICE_WAKE_DURATION = 5.0      # How long to show happy after wake (seconds)

# ============ Awake-state timeouts ============
AWAKE_TIMEOUT = 30.0           # Awake-state timeout (seconds) - returns to sleep after inactivity
AWAKE_ACTIVITY_EXTEND = True   # Extend awake timer automatically when activity occurs

# ============ Singing ============
SING_AUDIO_FILE = "resources/sounds/sing.wav"  # Singing audio file path
SPIN_DURATION = 4.5            # Time to spin 360 degrees (seconds); tune on hardware
SPIN_SPEED = 60                # Spin speed (0-100)

# ============ Emotion mapping ============
EMOTION_SOUNDS = {
    "neutral": None,
    "happy": "happy",           # Familiar person seen, or short press
    "scared": "scared",         # Stranger seen, or long press
    "excited": "excited",       # Medium press
    "curious": "beep"           # Face detected but still recognizing
}

# ============ Colors ============
COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "green": (0, 255, 0),       # Familiar
    "yellow": (255, 255, 0),    # Recognizing
    "red": (255, 0, 0),         # Stranger
    "blue": (0, 0, 255),        # Neutral
}