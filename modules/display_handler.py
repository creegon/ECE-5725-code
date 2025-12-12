# modules/display_handler.py

import pygame
import os
from config import *

# Language setting
LANG = getattr(__import__('config'), 'LANG', 'zh')

# Import framebuffer helper
try:
    from utils.framebuffer_helper import FramebufferHelper
except ImportError:
    FramebufferHelper = None

# Import touch event helper
try:
    from utils.touch_event_helper import TouchEventHelper
except ImportError:
    TouchEventHelper = None

class DisplayHandler:
    def __init__(self):
        # Ensure the dummy driver is used (avoid errors when no display is present)
        if not SIMULATION_MODE:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            
        try:
            pygame.display.init()
            # Initialize pygame screen (dummy mode)
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"Pygame display initialization failed: {e}")
            # Try forcing dummy again
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            try:
                pygame.display.init()
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception as e2:
                print(f"Unable to initialize display: {e2}")
                self.screen = None

        pygame.mouse.set_visible(False if not SIMULATION_MODE else True)
        
        # Initialize framebuffer (hardware mode)
        self.fb_helper = None
        if not SIMULATION_MODE and FramebufferHelper:
            self.fb_helper = FramebufferHelper('/dev/fb0', SCREEN_WIDTH, SCREEN_HEIGHT)
            if self.fb_helper.is_available():
                msg = "Using direct framebuffer mode"
                print(msg)
            else:
                msg = "Framebuffer unavailable; using pygame only"
                print(msg)
                self.fb_helper = None
        
        # Initialize touch event reader (hardware mode)
        self.touch_helper = None
        if not SIMULATION_MODE and TouchEventHelper:
            self.touch_helper = TouchEventHelper('/dev/input/event6')
            if self.touch_helper.is_available():
                msg = "Using direct touch event input"
                print(msg)
            else:
                msg = "Touch device unavailable; using pygame events"
                print(msg)
                self.touch_helper = None
        
        if SIMULATION_MODE:
            pygame.display.set_caption("WALL-E Simulator")
        
        # Load emotion assets
        self.emotions = {}
        self.load_emotions()
        
        # Touch state
        self.touch_start_time = None
        self.is_touching = False
        
        # Current emotion and switching control
        self.current_emotion = "neutral"
        self.target_emotion = "neutral"  # Target emotion
        self.last_emotion_change = 0  # Last emotion switch time
        self.emotion_switch_time = 0  # Scheduled switch time
        self.emotion_change_delay = EMOTION_CHANGE_DELAY  # From config
        self.transition_alpha = 1.0  # Transition alpha
        self.is_transitioning = False  # Whether transitioning
        
        if DEBUG:
            print("Display handler initialized")
    
    def load_emotions(self):
        emotions_dir = "resources/emotions_saki"
        
        # Emotion list (includes all supported emotions)
        emotion_list = ["neutral", "happy", "scared", "excited", "curious", "sleepy", "love", "cry", "shocked", "sing"]
        
        for emotion in emotion_list:
            img_path = os.path.join(emotions_dir, f"{emotion}.png")
            
            if os.path.exists(img_path):
                img = pygame.image.load(img_path)
                self.emotions[emotion] = pygame.transform.scale(
                    img, (SCREEN_WIDTH, SCREEN_HEIGHT)
                )
                if DEBUG:
                    print(f"  Loaded emotion: {emotion}")
            else:
                # Placeholder
                self.emotions[emotion] = self.create_placeholder(emotion)
                if DEBUG:
                    print(f"  Placeholder: {emotion}")
    
    def create_placeholder(self, emotion):
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        
        color_map = {
            "neutral": COLORS["blue"],
            "happy": COLORS["green"],
            "scared": COLORS["red"],
            "excited": COLORS["yellow"],
            "curious": COLORS["white"]
        }
        
        surface.fill(color_map.get(emotion, COLORS["white"]))
        
        # Add label text
        font = pygame.font.Font(None, 48)
        text = font.render(emotion.upper(), True, COLORS["black"])
        text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        surface.blit(text, text_rect)
        
        return surface
    
    def show_emotion(self, emotion, force=False):
        import time
        
        if emotion not in self.emotions:
            return
        
        # Skip if the same as current emotion
        if emotion == self.current_emotion and not force:
            return
        
        # Skip if already queued as target emotion
        if emotion == self.target_emotion and not force:
            return
        
        # Check switch cooldown window
        current_time = time.time()
        if not force and (current_time - self.last_emotion_change) < self.emotion_change_delay:
            # Record target emotion to switch later
            self.target_emotion = emotion
            if DEBUG:
                print(f"  [Emotion queue] {emotion} (cooldown; switching in {self.emotion_change_delay:.1f}s)")
            return
        
        # Update emotion
        self.current_emotion = emotion
        self.target_emotion = emotion
        self.last_emotion_change = current_time
        
        # Render immediately (fade transitions could be added later)
        self._render_emotion(emotion)
    
    def _render_emotion(self, emotion):
        if emotion in self.emotions:
            self.screen.blit(self.emotions[emotion], (0, 0))
            pygame.display.flip()
            
            # If framebuffer is available, push directly to screen
            if self.fb_helper and self.fb_helper.is_available():
                self.fb_helper.update_from_pygame_surface(self.screen)
                if DEBUG:
                    msg = f"  [Framebuffer] Rendered emotion: {emotion}"
                    print(msg)
    
    def get_touch_event(self):
        import time
        # Prefer direct touch helper if available
        if self.touch_helper and self.touch_helper.is_available():
            events = self.touch_helper.read_all_pending()
            for event_type, duration, x, y in events:
                if event_type == 'press':
                    return ("touch_start", x, y, 0)
                elif event_type == 'release':
                    return ("touch_end", x, y, duration)
            return None
        
        # Otherwise use pygame events
        for event in pygame.event.get():
            # Quit
            if event.type == pygame.QUIT:
                return ("quit", 0, 0, 0)
            
            # Keyboard
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return ("quit", 0, 0, 0)
            
            # Touch/mouse down
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.touch_start_time = time.time()
                self.is_touching = True
                pos = pygame.mouse.get_pos()
                return ("touch_start", pos[0], pos[1], 0)
            
            # Touch/mouse up
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.touch_start_time is not None:
                    duration = time.time() - self.touch_start_time
                    pos = pygame.mouse.get_pos()
                    self.is_touching = False
                    self.touch_start_time = None
                    return ("touch_end", pos[0], pos[1], duration)
        
        return None
    
    def peek_touch_event(self):
        # Check whether currently touching
        # Prefer direct touch helper if available
        if self.touch_helper and self.touch_helper.is_available():
            return self.touch_helper.is_touched()
        return pygame.mouse.get_pressed()[0]

    def draw_text(self, text, x, y, color=None, size=20):
        if color is None:
            color = (255, 255, 255)
        
        try:
            font = pygame.font.Font(None, size)
            text_surface = font.render(text, True, color)
            self.screen.blit(text_surface, (x, y))
        except:
            pass

    def update(self, delta_time=0.016):
        import time
        
        # Check if a delayed emotion switch is due
        if self.target_emotion and self.target_emotion != self.current_emotion:
            if time.time() >= self.emotion_switch_time:
                self.current_emotion = self.target_emotion
                self.target_emotion = None
                self.show_emotion(self.current_emotion, force=True)
    
    def clear(self):
        self.screen.fill(COLORS["black"])