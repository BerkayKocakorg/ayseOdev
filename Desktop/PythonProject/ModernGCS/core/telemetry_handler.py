import threading
import time
import math
import csv
import os
from datetime import datetime
from pymavlink import mavutil
from .voice_assistant import VoiceAssistant
from .gamepad_handler import GamepadHandler

class TelemetryHandler:
    """
    Handles MAVLink connection, telemetry data fetching, and sending commands.
    Runs in its own background thread to prevent UI freezing.
    
    V4.0 Features:
    - Fixed takeoff command
    - Emergency stop (kill switch)
    - Flight path tracking for trail display
    - CSV telemetry logging
    - GOTO command for guided navigation
    """
    def __init__(self):
        self.mav = None
        self.connected = False
        self.running = True
        self.thread = None
        self.uploading_mission = False
        self.mav_lock = threading.Lock()
        
        # Central data store for the entire app to read from
        self.data = {
            "altitude": 0.0,
            "groundspeed": 0.0,
            "climb_rate": 0.0,
            "battery": 0,
            "voltage": 0.0,
            "current": 0.0,
            "gps_fix": 0,
            "satellites": 0,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "heading": 0,
            "mode": "UNKNOWN",
            "armed": False,
            "lat": 0.0,
            "lon": 0.0
        }
        
        # Flight path tracking — list of (lat, lon) tuples
        self.flight_path = []
        self._last_path_time = 0
        self._path_interval = 1.0  # Record position every 1 second
        
        # Telemetry CSV logging
        self._logging_active = False
        self._log_file = None
        self._csv_writer = None
        self._log_lock = threading.Lock()
        
        # MAVLink Forwarding (e.g. to Mission Planner)
        self.forward_ip = "127.0.0.1"
        self.forward_port = 14550
        self.forward_conn = None
        
        # Voice Assistant and Gamepad
        self.voice = VoiceAssistant()
        self.gamepad = GamepadHandler(self)
        
        # State trackers for voice alerts
        self._last_spoken_mode = "UNKNOWN"
        self._last_spoken_armed = False
        self._battery_warned = False
        
        # Callback to update UI if needed
        self.on_data_updated = None

    def start(self):
        self.running = True
        
        # Setup forwarding to Mission Planner
        try:
            self.forward_conn = mavutil.mavlink_connection(f"udpout:{self.forward_ip}:{self.forward_port}")
            print(f"[INFO] MAVLink forwarding to {self.forward_ip}:{self.forward_port}")
        except Exception as e:
            print(f"[WARN] Failed to setup MAVLink forwarding: {e}")

        self.thread = threading.Thread(target=self._mavlink_loop, daemon=True)
        self.thread.start()
        
        # Try to start gamepad
        self.gamepad.start()

    def connect(self, connection_string="tcp:127.0.0.1:5760"):
        try:
            print(f"Connecting to {connection_string}...")
            self.mav = mavutil.mavlink_connection(connection_string)
            self.mav.wait_heartbeat(timeout=5)
            self.connected = True
            
            # Tüm veri akışlarını saniyede 4 kez (4 Hz) göndermesi için drone'a talep yolla
            self.mav.mav.request_data_stream_send(
                self.mav.target_system, self.mav.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL, 4, 1)
                
            # Clear flight path on new connection
            self.flight_path.clear()
            
            print("Heartbeat received. Connected.")
            return True, "Connected successfully."
        except Exception as e:
            self.connected = False
            return False, str(e)

    def disconnect(self):
        if self.mav:
            self.mav.close()
        self.mav = None
        self.connected = False
        self.stop_logging()

    def arm(self):
        if self.mav and self.connected:
            self.mav.arducopter_arm()
            
    def disarm(self):
        if self.mav and self.connected:
            self.mav.arducopter_disarm()
            
    def set_mode(self, mode_name):
        if self.mav and self.connected:
            mode_map = self.mav.mode_mapping()
            if mode_name in mode_map:
                self.mav.set_mode(mode_map[mode_name])

    def takeoff(self, altitude):
        """
        Send NAV_TAKEOFF command with correct parameters.
        Only param7 (altitude) is relevant for copters.
        """
        if self.mav and self.connected:
            self.mav.mav.command_long_send(
                self.mav.target_system,
                self.mav.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,      # confirmation
                0,      # param1: pitch (ignored for copters)
                0,      # param2: empty
                0,      # param3: empty
                0,      # param4: yaw angle (NaN for default)
                0,      # param5: latitude (ignored, use current)
                0,      # param6: longitude (ignored, use current)
                altitude # param7: altitude in meters
            )

    def land(self):
        """Switch to LAND mode."""
        self.set_mode("LAND")

    def rtl(self):
        """Switch to RTL (Return to Launch) mode."""
        self.set_mode("RTL")

    def emergency_stop(self):
        """
        Emergency kill switch — force disarm regardless of state.
        Uses MAV_CMD_COMPONENT_ARM_DISARM with param2=21196 (force).
        WARNING: This will cause the drone to fall from the sky!
        """
        if self.mav and self.connected:
            self.mav.mav.command_long_send(
                self.mav.target_system,
                self.mav.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,      # confirmation
                0,      # param1: 0=disarm
                21196,  # param2: 21196=force (magic number)
                0, 0, 0, 0, 0
            )

    def goto(self, lat, lon, alt=20):
        """
        Command drone to fly to a specific coordinate in GUIDED mode.
        Uses SET_POSITION_TARGET_GLOBAL_INT for precision.
        """
        if self.mav and self.connected:
            self.mav.mav.mission_item_int_send(
                self.mav.target_system,
                self.mav.target_component,
                0,  # seq
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                2,  # current (2 = guided mode goto)
                0,  # autocontinue
                0, 0, 0, 0,  # param 1-4
                int(lat * 1e7), int(lon * 1e7), alt
            )

    def set_waypoint(self, lat, lon, alt=10):
        if self.mav and self.connected:
            # Command drone to go to a specific coordinate
            self.mav.mav.mission_item_int_send(
                self.mav.target_system,
                self.mav.target_component,
                0, # seq
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                2, # current (2 = guided mode goto)
                0, # autocontinue
                0, 0, 0, 0, # param 1-4
                int(lat * 1e7), int(lon * 1e7), alt
            )

    def upload_mission(self, waypoints):
        if not self.mav or not self.connected:
            return False, "Bağlı değil."
            
        self.uploading_mission = True
        try:
            with self.mav_lock:
                # 1. Clear existing mission
                self.mav.mav.mission_clear_all_send(self.mav.target_system, self.mav.target_component)
                self.mav.recv_match(type='MISSION_ACK', blocking=True, timeout=3)
                
                # 2. Total waypoints (1 dummy home + real waypoints)
                wp_count = len(waypoints) + 1
                self.mav.mav.mission_count_send(self.mav.target_system, self.mav.target_component, wp_count)
                
                # 3. Handle requests — support both MISSION_REQUEST and MISSION_REQUEST_INT
                for i in range(wp_count):
                    msg = self.mav.recv_match(
                        type=['MISSION_REQUEST', 'MISSION_REQUEST_INT'],
                        blocking=True, timeout=5
                    )
                    if not msg:
                        return False, f"Zaman aşımı (WP {i} isteği gelmedi)."
                    
                    seq = msg.seq
                    msg_type = msg.get_type()
                    
                    if seq == 0:
                        # Dummy home waypoint (current position)
                        lat_val = int(self.data.get("lat", 0) * 1e7)
                        lon_val = int(self.data.get("lon", 0) * 1e7)
                        alt_val = 0
                        cmd = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
                        current = 0
                        autocontinue = 0
                    else:
                        wp = waypoints[seq - 1]
                        lat_val = int(wp["lat"] * 1e7)
                        lon_val = int(wp["lon"] * 1e7)
                        alt_val = int(wp.get("alt", 20))
                        cmd = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
                        current = 0
                        autocontinue = 1
                    
                    if msg_type == 'MISSION_REQUEST_INT':
                        # Respond with mission_item_int (preferred by modern firmware)
                        self.mav.mav.mission_item_int_send(
                            self.mav.target_system, self.mav.target_component, seq,
                            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                            cmd, current, autocontinue,
                            0, 0, 0, 0,
                            lat_val, lon_val, alt_val
                        )
                    else:
                        # Respond with mission_item (legacy firmware)
                        self.mav.mav.mission_item_send(
                            self.mav.target_system, self.mav.target_component, seq,
                            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                            cmd, current, autocontinue,
                            0, 0, 0, 0,
                            lat_val / 1e7, lon_val / 1e7, alt_val
                        )
                
                # 4. Wait for final ACK
                ack = self.mav.recv_match(type='MISSION_ACK', blocking=True, timeout=5)
                if ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                    # 5. Reset mission index to first real waypoint
                    self.mav.mav.mission_set_current_send(
                        self.mav.target_system, self.mav.target_component, 1
                    )
                    return True, "Görev başarıyla yüklendi."
                else:
                    return False, f"Görev reddedildi (Kod: {ack.type if ack else 'Yok'})."
        except Exception as e:
            return False, str(e)
        finally:
            self.uploading_mission = False

    def reset_mission_current(self):
        """Reset mission index to first waypoint so AUTO starts from beginning."""
        if self.mav and self.connected:
            self.mav.mav.mission_set_current_send(
                self.mav.target_system, self.mav.target_component, 1
            )

    # ─── Telemetry CSV Logging ───────────────────────────────────────────

    def start_logging(self, directory=None):
        """Start recording telemetry data to a CSV file."""
        if self._logging_active:
            return False, "Zaten kayıt yapılıyor."
        
        if directory is None:
            directory = os.path.join(os.path.dirname(__file__), '..', 'logs')
        
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(directory, f"flight_log_{timestamp}.csv")
        
        try:
            self._log_file = open(filepath, 'w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._log_file)
            self._csv_writer.writerow([
                "timestamp", "lat", "lon", "altitude", "groundspeed",
                "climb_rate", "heading", "roll", "pitch", "yaw",
                "battery", "voltage", "current", "satellites", "gps_fix",
                "mode", "armed"
            ])
            self._logging_active = True
            return True, filepath
        except Exception as e:
            return False, str(e)

    def stop_logging(self):
        """Stop recording telemetry data."""
        with self._log_lock:
            self._logging_active = False
            if self._log_file:
                try:
                    self._log_file.close()
                except Exception:
                    pass
                self._log_file = None
                self._csv_writer = None

    def _write_log_row(self):
        """Write current telemetry data to CSV."""
        if not self._logging_active or not self._csv_writer:
            return
        with self._log_lock:
            try:
                self._csv_writer.writerow([
                    datetime.now().isoformat(),
                    self.data["lat"], self.data["lon"],
                    self.data["altitude"], self.data["groundspeed"],
                    self.data["climb_rate"], self.data["heading"],
                    self.data["roll"], self.data["pitch"], self.data["yaw"],
                    self.data["battery"], self.data["voltage"], self.data["current"],
                    self.data["satellites"], self.data["gps_fix"],
                    self.data["mode"], self.data["armed"]
                ])
                self._log_file.flush()
            except Exception:
                pass

    @property
    def is_logging(self):
        return self._logging_active

    # ─── Flight Path Tracking ────────────────────────────────────────────

    def _record_flight_path(self):
        """Record drone position for trail display."""
        now = time.time()
        if now - self._last_path_time >= self._path_interval:
            lat = self.data["lat"]
            lon = self.data["lon"]
            if lat != 0.0 and lon != 0.0:
                # Only add if position changed meaningfully
                if (not self.flight_path or
                    abs(self.flight_path[-1][0] - lat) > 1e-7 or
                    abs(self.flight_path[-1][1] - lon) > 1e-7):
                    self.flight_path.append((lat, lon))
                    # Limit path length to prevent memory issues
                    if len(self.flight_path) > 5000:
                        self.flight_path = self.flight_path[-3000:]
            self._last_path_time = now

    # ─── MAVLink Loop ────────────────────────────────────────────────────

    def _mavlink_loop(self):
        """
        Optimized MAVLink loop:
        - Reads ALL available messages in a burst (drains queue)
        - No per-message UI callback (UI uses its own periodic timer)
        - CSV logging throttled to 4Hz
        """
        last_log_time = 0
        log_interval = 0.25  # 4Hz CSV logging
        
        while self.running:
            if self.mav and self.connected and not self.uploading_mission:
                with self.mav_lock:
                    try:
                        # Drain all available messages in one burst
                        msg_count = 0
                        while msg_count < 200:  # Safety limit per cycle
                            msg = self.mav.recv_match(blocking=False)
                            if not msg:
                                break
                            
                            # Forward raw bytes to Mission Planner
                            if self.forward_conn:
                                try:
                                    self.forward_conn.write(msg.get_msgbuf())
                                except Exception:
                                    pass
                                    
                            self._process_message(msg)
                            msg_count += 1
                        
                        # Throttled CSV logging (4Hz instead of every message)
                        now = time.time()
                        if now - last_log_time >= log_interval:
                            self._record_flight_path()
                            self._write_log_row()
                            last_log_time = now
                            
                    except Exception as e:
                        import traceback
                        print(f"[ERROR] Exception in MAVLink loop: {e}")
                        traceback.print_exc()
            time.sleep(0.005)  # 5ms sleep — fast enough for responsive commands

    def _process_message(self, msg):
        """Process a single MAVLink message. Only updates data dict — no UI calls."""
        # Ignore messages from other Ground Stations (e.g., Mission Planner with sysid 255)
        # or from systems other than the target drone we connected to.
        if hasattr(msg, 'get_srcSystem'):
            src_sys = msg.get_srcSystem()
            if self.mav and src_sys != self.mav.target_system:
                return
                
        msg_type = msg.get_type()
        
        if msg_type == "HEARTBEAT":
            modes = {0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO", 4: "GUIDED", 5: "LOITER", 6: "RTL", 9: "LAND"}
            new_mode = modes.get(msg.custom_mode, f"MODE({msg.custom_mode})")
            new_armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            
            self.data["mode"] = new_mode
            self.data["armed"] = new_armed
            
            # Voice Alerts for Mode and Arming
            if new_mode != self._last_spoken_mode and self._last_spoken_mode != "UNKNOWN":
                self.voice.say(f"Flight mode changed to {new_mode}")
            self._last_spoken_mode = new_mode
            
            if new_armed != self._last_spoken_armed:
                state_str = "Armed" if new_armed else "Disarmed"
                self.voice.say(f"Vehicle {state_str}")
            self._last_spoken_armed = new_armed
            
        elif msg_type == "SYS_STATUS":
            self.data["voltage"] = msg.voltage_battery / 1000.0
            self.data["current"] = msg.current_battery / 100.0
            self.data["battery"] = msg.battery_remaining
            
            # Voice Alert for Battery
            if self.data["battery"] > 0 and self.data["battery"] < 20 and not self._battery_warned:
                self.voice.say_warning("Warning. Battery level low.")
                self._battery_warned = True
            elif self.data["battery"] >= 20:
                self._battery_warned = False
            
        elif msg_type == "GPS_RAW_INT":
            self.data["gps_fix"] = msg.fix_type
            self.data["satellites"] = msg.satellites_visible
            
        elif msg_type == "GLOBAL_POSITION_INT":
            self.data["lat"] = msg.lat / 1e7
            self.data["lon"] = msg.lon / 1e7
            self.data["altitude"] = msg.relative_alt / 1000.0
                
        elif msg_type == "ATTITUDE":
            self.data["roll"] = math.degrees(msg.roll)
            self.data["pitch"] = math.degrees(msg.pitch)
            self.data["yaw"] = math.degrees(msg.yaw)
            
        elif msg_type == "VFR_HUD":
            self.data["groundspeed"] = msg.groundspeed
            self.data["climb_rate"] = msg.climb
            self.data["heading"] = msg.heading

    def stop(self):
        self.running = False
        self.stop_logging()
        self.disconnect()
        self.voice.stop()
        self.gamepad.stop()
