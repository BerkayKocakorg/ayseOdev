import threading
import time

# Graceful fallback: if pygame is not installed, gamepad will be disabled
try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False
    print("[WARN] pygame not installed. Gamepad support disabled. Install with: pip install pygame")

from pymavlink import mavutil

class GamepadHandler:
    def __init__(self, telemetry_handler):
        self.telemetry = telemetry_handler
        self.running = False
        self.joystick = None
        self.thread = None
        
        # Mappings for channel values (1000 to 2000)
        # Default mid point is 1500
        self.channels = {
            1: 1500, # Roll
            2: 1500, # Pitch
            3: 1500, # Throttle
            4: 1500, # Yaw
            5: 0, 6: 0, 7: 0, 8: 0
        }

    def start(self):
        if not _PYGAME_AVAILABLE:
            return False
        try:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.running = True
                self.thread = threading.Thread(target=self._joystick_loop, daemon=True)
                self.thread.start()
                print(f"Gamepad connected: {self.joystick.get_name()}")
                return True
            else:
                print("No gamepad detected.")
                return False
        except Exception as e:
            print(f"Gamepad init error: {e}")
            return False

    def _map_axis(self, value, reverse=False):
        # Pygame joystick axis gives -1.0 to 1.0
        # MAVLink RC channels expect 1000 to 2000
        val = int(1500 + (value * 500))
        if reverse:
            val = 3000 - val # Reverse direction
        return max(1000, min(2000, val))

    def _joystick_loop(self):
        while self.running:
            pygame.event.pump() # Process events internally
            
            if self.joystick and self.telemetry.connected:
                # Axis 0: Left Stick X (Yaw) -> Ch4
                # Axis 1: Left Stick Y (Throttle) -> Ch3
                # Axis 3 or 4: Right Stick X (Roll) -> Ch1
                # Axis 4 or 3: Right Stick Y (Pitch) -> Ch2
                # Note: Axis mapping varies heavily by controller (Xbox vs PS)
                
                # Using standard Xbox controller mapping as default
                yaw = self.joystick.get_axis(0)
                throttle = self.joystick.get_axis(1) 
                roll = self.joystick.get_axis(2) # Sometimes 3
                pitch = self.joystick.get_axis(3) # Sometimes 4
                
                self.channels[4] = self._map_axis(yaw)
                self.channels[3] = self._map_axis(throttle, reverse=True) # Up is negative in pygame
                self.channels[1] = self._map_axis(roll)
                self.channels[2] = self._map_axis(pitch, reverse=True)
                
                # Send RC Override command
                if self.telemetry.mav:
                    self.telemetry.mav.mav.rc_channels_override_send(
                        self.telemetry.mav.target_system,
                        self.telemetry.mav.target_component,
                        self.channels[1],
                        self.channels[2],
                        self.channels[3],
                        self.channels[4],
                        0, 0, 0, 0
                    )
            
            time.sleep(0.05) # 20Hz update rate

    def stop(self):
        self.running = False
        try:
            if self.joystick:
                self.joystick.quit()
            if _PYGAME_AVAILABLE:
                pygame.quit()
        except Exception:
            pass
