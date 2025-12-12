import threading

class DebugController:
    def __init__(self, wall_e):
        self.wall_e = wall_e
        self.command_queue = []
        self.running = True

    def start(self):
        kb_thread = threading.Thread(target=self._keyboard_thread, daemon=True)
        kb_thread.start()

    def _keyboard_thread(self):
        print()
        print("=" * 60)
        print("Debug keys:")
        print("   1 - Wake 'hey'")
        print("   2 - Command 'sing'")
        print("   3 - Command 'spin'")
        print("   4 - Command 'friends'")
        print("   [ / ] - Left wheel trim")
        print("   - / = - Right wheel trim")
        print("   s - Save trim")
        print("   q - Quit")
        print("=" * 60)
        print()
        
        while self.running and self.wall_e.running:
            try:
                cmd = input()
                if cmd.strip():
                    self.command_queue.append(cmd.strip().lower())
            except EOFError:
                break
            except Exception:
                break

    def process_commands(self):
        while self.command_queue:
            cmd = self.command_queue.pop(0)
            
            if cmd == '1':
                print("SIM: wake 'hey'")
                self.wall_e.on_voice_wake("hey")
            elif cmd == '2':
                print("SIM: 'sing'")
                self.wall_e.on_voice_command("sing", "sing")
            elif cmd == '3':
                print("SIM: 'spin'")
                self.wall_e.on_voice_command("spin", "spin")
            elif cmd == '4':
                print("SIM: 'friends'")
                self.wall_e.on_voice_command("friends", "friends")
            elif cmd == '[':
                if self.wall_e.motor: self.wall_e.motor.adjust_calibration('left', -0.05)
            elif cmd == ']':
                if self.wall_e.motor: self.wall_e.motor.adjust_calibration('left', 0.05)
            elif cmd == '-':
                if self.wall_e.motor: self.wall_e.motor.adjust_calibration('right', -0.05)
            elif cmd == '=':
                if self.wall_e.motor: self.wall_e.motor.adjust_calibration('right', 0.05)
            elif cmd == 's':
                if self.wall_e.motor: self.wall_e.motor.save_calibration()
            elif cmd == 'q':
                print("Exiting...")
                self.wall_e.running = False
