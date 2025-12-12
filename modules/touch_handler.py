# modules/touch_handler.py

import time
from config import *

class TouchHandler:
    
    def __init__(self, display, audio):
        self.display = display
        self.audio = audio
        
        # Registration state
        self.is_registering = False
        self.register_name = ""
        
        if DEBUG:
            print("Touch handler initialized")
    
    def handle_touch_end(self, duration):
        if DEBUG:
            print(f"Touch duration: {duration:.2f}s")
        
        # Any valid touch switches to 'excited'
        if duration >= 0.1:
            if DEBUG:
                print("  -> Touch -> Excited (5s)")
            self.display.show_emotion("excited")
            self.audio.play_sound("excited")
            return "excited"
        
        else:
            # Too short; ignore
            return None
