import time
import threading
from config import SEARCH_ROTATE_SPEED, ROTATE_STEP_DURATION, ROTATE_STEP_PAUSE


class ActionRecorder:
    def __init__(self):
        self.action_history = []      # Action history
        self.is_returning = False     # Whether currently returning to the original position
        self.return_action_index = 0  # Current return action index
        
        # Async tracking
        self._current_action = None   # Current action: {'type': 'move'/'rotate', 'direction': ...}
        self._action_start_time = 0   # Action start time
        self._lock = threading.Lock() # Thread lock
    
    # Async action recording API
    
    def start_action(self, action_type, direction):
        if self.is_returning:
            return  # Do not record during return
        
        with self._lock:
            # If there's an unfinished action, finish it first
            if self._current_action is not None:
                self._finish_current_action()
            
            self._current_action = {
                'type': action_type,
                'direction': direction
            }
            self._action_start_time = time.time()
    
    def stop_action(self):
        with self._lock:
            if self._current_action is not None:
                self._finish_current_action()
    
    def _finish_current_action(self):
        if self._current_action is None:
            return
        
        duration = time.time() - self._action_start_time
        
        # Record only meaningful actions (>= 0.05s)
        if duration >= 0.05:
            action = {
                'type': self._current_action['type'],
                'direction': self._current_action['direction'],
                'duration': duration,
                'timestamp': time.time()
            }
            self.action_history.append(action)
        
        self._current_action = None
        self._action_start_time = 0
    
    def get_current_action(self):
        with self._lock:
            return self._current_action.copy() if self._current_action else None
    
    def record(self, action_type, direction, duration):
        if self.is_returning:
            return
        
        # Record only meaningful actions
        if duration < 0.05:
            return
            
        with self._lock:
            action = {
                'type': action_type,
                'direction': direction,
                'duration': duration,
                'timestamp': time.time()
            }
            self.action_history.append(action)
    
    # History management
    
    def clear(self):
        with self._lock:
            self.action_history = []
            self._current_action = None
            self._action_start_time = 0
    
    def has_actions(self):
        return len(self.action_history) > 0
    
    def get_action_count(self):
        return len(self.action_history)

    def get_reverse_direction(self, direction):
        reverse_map = {
            'left': 'right',
            'right': 'left',
            'forward': 'backward',
            'backward': 'forward'
        }
        return reverse_map.get(direction, direction)
    
    # Return-to-origin feature
    
    def start_returning(self):
        # Finish any ongoing action first
        self.stop_action()
        
        if not self.has_actions():
            return False
        
        print(f"Starting return-to-origin: {len(self.action_history)} actions to reverse")
        self.is_returning = True
        self.return_action_index = len(self.action_history) - 1  # Start from the last
        return True
    
    def get_next_return_action(self):
        if self.return_action_index < 0:
            return None
        
        action = self.action_history[self.return_action_index]
        reverse_direction = self.get_reverse_direction(action['direction'])
        
        return_action = {
            'type': action['type'],
            'direction': reverse_direction,
            'original_direction': action['direction'],
            'duration': action['duration'],
            'index': self.return_action_index,
            'total': len(self.action_history)
        }
        
        return return_action
    
    def advance_return_index(self):
        self.return_action_index -= 1
    
    def is_return_complete(self):
        return self.return_action_index < 0
    
    def finish_returning(self):
        print("Returned to origin")
        self.is_returning = False
        self.clear()
    
    def execute_return_action(self, motor, obstacle_callback=None):
        action_info = self.get_next_return_action()
        
        if action_info is None:
            self.finish_returning()
            return True
        
        if motor is None or not motor.enabled:
            # No motor; simulate delay
            time.sleep(action_info['duration'])
        else:
            if action_info['type'] == 'rotate':
                # Reverse rotation - stepwise pulses
                step_duration = ROTATE_STEP_DURATION
                pause_duration = ROTATE_STEP_PAUSE
                total_steps = int(action_info['duration'] / step_duration)
                
                for step in range(total_steps):
                    if action_info['direction'] == 'left':
                        motor.turn_left(SEARCH_ROTATE_SPEED)
                    else:
                        motor.turn_right(SEARCH_ROTATE_SPEED)
                    time.sleep(step_duration)
                    motor.stop()
                    time.sleep(pause_duration)
                    
            elif action_info['type'] == 'move':
                # Reverse movement
                if action_info['direction'] == 'forward':
                    motor.forward()
                else:
                    motor.backward()
                time.sleep(action_info['duration'])
                motor.stop()
        
        time.sleep(0.1)  # Stabilization time
        self.advance_return_index()
        return False
