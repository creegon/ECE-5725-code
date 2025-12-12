# WALL-E Project Instructions

## Project Overview
This is a Raspberry Pi-based emotional companion robot project ("WALL-E").
- **Core Logic:** Python 3 application using OpenCV (vision) and Pygame (UI/Audio).
- **Hardware Target:** Raspberry Pi with a touchscreen (3.5" TFT likely) and USB Camera.
- **Key Features:** Face recognition (MobileFaceNet), emotion display, and touch interaction.

## Architecture & Key Components
- **Entry Point:** `main.py` orchestrates the main event loop, integrating vision, touch, and display.
- **Configuration (`config.py`):** 
  - **Smart Mode Detection:** Automatically switches between "Simulation Mode" (SSH/Headless) and "Hardware Mode" (Local/DirectFB).
  - **Drivers:** Sets `SDL_VIDEODRIVER` to `dummy` (SSH) or `fbcon`/`directfb` (Local).
- **Modules (`modules/`):**
  - `face_*.py`: Complete face recognition pipeline (Detection -> Alignment -> Embedding -> Recognition).
  - `display_handler.py`: Manages the UI on the framebuffer (`/dev/fb0`).
  - `touch_handler.py`: Handles raw input events from `/dev/input/event6`.
  - `audio_handler.py`: Manages sound effects.
- **Data:** Face features stored in `data/face_features.pkl`.

## Hardware Specifics & Patterns
- **Camera Initialization:** 
  - **CRITICAL:** Must use `cv2.CAP_V4L2` and set format to `MJPEG` to avoid freezing on Raspberry Pi.
  - Reference: `utils/camera_helper.py`.
- **Display Access:** 
  - Writes directly to framebuffer `/dev/fb0`.
  - Uses `os.environ` to configure SDL before initializing Pygame.
- **Input Handling:**
  - Reads raw events from `/dev/input/event6` (ensure this device path is correct for the target hardware).

## Development Workflows
- **Running the App:**
  - `python3 main.py`: Auto-detects environment.
- **Testing Components:**
  - `python3 test_camera_helper.py`: Verify camera V4L2/MJPEG setup.
  - `python3 test_touch_only.py`: Test UI/Touch logic without loading heavy AI models.
  - `python3 face_test.py`: Validate face recognition performance.
  - `python3 face_register.py`: Tool to register new faces into the database.
- **Service Management:**
  - Systemd service file: `wall-e.service`.

## Common Pitfalls
- **OpenCV Version:** Code contains checks for OpenCV < 4.5.4. Keep this in mind when updating dependencies.
- **Permissions:** The user needs access to `/dev/video0`, `/dev/fb0`, and `/dev/input/event*`.
- **SSH vs Local:** If the display isn't working, check if `config.py` incorrectly detected an SSH session.
