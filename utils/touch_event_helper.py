"""
Touch event helper module.

Reads touch events directly from /dev/input/eventX, bypassing SDL limitations.
"""
import glob
import os
import struct
import select
import time

class TouchEventHelper:
    """Helper for reading touch events from evdev directly."""
    DEFAULT_KEYWORDS = (
        "touch",
        "pitft",
        "ep0110",
        "ft5",
        "stmpe",
        "ads7846",
        "ili",
        "tsc",
    )
    
    # evdev event struct (from linux/input.h)
    EVENT_FORMAT = 'llHHi'
    EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
    
    # Event types
    EV_SYN = 0x00
    EV_KEY = 0x01
    EV_ABS = 0x03
    
    # Event codes
    ABS_X = 0x00
    ABS_Y = 0x01
    BTN_TOUCH = 0x14A
    
    def __init__(self, device_path='/dev/input/event6', device_keywords=None):
        """
        Initialize touch event reader.
        
        Args:
            device_path: Touch device path.
        """
        self.device_keywords = tuple((device_keywords or self.DEFAULT_KEYWORDS))
        self.device_path = self._resolve_device_path(device_path)
        self.device = None
        self.touching = False
        self.touch_start_time = None
        self.x = 0
        self.y = 0
        
        if not self.device_path:
            print("Unable to determine touch device; falling back to pygame events")
            return

        try:
            self.device = open(self.device_path, 'rb', buffering=0)
            # Non-blocking to avoid stalling the main loop
            os.set_blocking(self.device.fileno(), False)
            print(f"Touch device opened: {self.device_path}")
        except Exception as e:
            print(f"Failed to open touch device {self.device_path}: {e}")
            self.device = None
    
    def is_available(self):
        """Return whether the touch device is available."""
        return self.device is not None
    
    def read_event(self, timeout=0):
        """
        Read a single touch event.
        
        Args:
            timeout: Timeout in seconds. 0 means non-blocking.
            
        Returns:
            (event_type, duration, x, y) or None
            event_type: 'press', 'release', 'move'
            duration: Touch duration in seconds
        """
        if not self.is_available():
            return None
        
        try:
            # Use select() to check readability; timeout=0 means non-blocking
            wait_time = max(timeout, 0)
            ready, _, _ = select.select([self.device], [], [], wait_time)
            if not ready:
                return None
            
            # Read one event
            data = self.device.read(self.EVENT_SIZE)
            if len(data) < self.EVENT_SIZE:
                return None
            
            # Decode event
            tv_sec, tv_usec, ev_type, code, value = struct.unpack(self.EVENT_FORMAT, data)
            
            # Absolute coordinate events
            if ev_type == self.EV_ABS:
                if code == self.ABS_X:
                    self.x = value
                elif code == self.ABS_Y:
                    self.y = value
                return ('move', 0, self.x, self.y)
            
            # Touch press/release events
            elif ev_type == self.EV_KEY and code == self.BTN_TOUCH:
                if value == 1:  # Press
                    self.touching = True
                    self.touch_start_time = time.time()
                    return ('press', 0, self.x, self.y)
                
                elif value == 0:  # Release
                    self.touching = False
                    duration = 0
                    if self.touch_start_time:
                        duration = time.time() - self.touch_start_time
                        self.touch_start_time = None
                    return ('release', duration, self.x, self.y)
            
            return None
            
        except BlockingIOError:
            return None
        except Exception as e:
            print(f"Failed to read touch event: {e}")
            return None
    
    def read_all_pending(self, max_events=100):
        """
        Read all pending events.
        
        Args:
            max_events: Maximum number of events to read.
            
        Returns:
            List of events.
        """
        events = []
        for _ in range(max_events):
            event = self.read_event(timeout=0)
            if event is None:
                break
            events.append(event)
        return events
    
    def get_touch_state(self):
        """
        Get the current touch state.
        
        Returns:
            (is_touching, duration, x, y)
        """
        # Drain pending events first
        self.read_all_pending()
        
        duration = 0
        if self.touching and self.touch_start_time:
            duration = time.time() - self.touch_start_time
        
        return (self.touching, duration, self.x, self.y)
    
    def close(self):
        """Close the device."""
        if self.device:
            self.device.close()
            self.device = None
    
    def __del__(self):
        """Destructor."""
        self.close()

    # Helper methods
    def _resolve_device_path(self, preferred_path):
        """Auto-select the touch input device from hints and system info."""
        # 1) Use the provided path if it exists
        if preferred_path and os.path.exists(preferred_path):
            return preferred_path

        # 2) Environment variable override
        env_path = os.environ.get('TOUCH_DEVICE_PATH')
        if env_path and os.path.exists(env_path):
            return env_path

        # 3) Auto-detect from /proc/bus/input/devices
        detected = self._detect_device_from_proc()
        if detected:
            return detected

        # 4) Common event nodes
        for candidate in self._default_event_candidates():
            if os.path.exists(candidate):
                return candidate
        return preferred_path

    def _detect_device_from_proc(self):
        """Parse /proc/bus/input/devices and find the touch device by keywords."""
        try:
            with open('/proc/bus/input/devices', 'r') as f:
                content = f.read()
        except OSError:
            return None

        blocks = [blk for blk in content.strip().split('\n\n') if blk.strip()]
        keywords = tuple(kw.lower() for kw in self.device_keywords if kw)

        for block in blocks:
            lines = block.splitlines()
            name_line = next((ln for ln in lines if ln.startswith('N:')), '')
            handler_line = next((ln for ln in lines if ln.startswith('H:')), '')

            if not name_line or not handler_line:
                continue

            name = name_line.split('=', 1)[-1].strip().strip('"')
            lowered = name.lower()
            if not any(keyword in lowered for keyword in keywords):
                continue

            handlers = handler_line.split('=')[-1].split()
            events = [token for token in handlers if token.startswith('event')]
            for evt in events:
                path = f"/dev/input/{evt}"
                if os.path.exists(path):
                    print(f"Auto-detected touch device: {name} -> {path}")
                    return path
        return None

    @staticmethod
    def _default_event_candidates():
        """Return common /dev/input/event candidates in a stable order."""
        explicit = [f"/dev/input/event{i}" for i in range(10)]
        discovered = sorted(glob.glob('/dev/input/event*'))
        combined = []
        for path in explicit + discovered:
            if path not in combined:
                combined.append(path)
        return combined
