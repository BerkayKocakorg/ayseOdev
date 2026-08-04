import math
import time
import threading


class SafetyMonitor:
    """
    Real-time safety monitoring system for drone flight.
    
    Features:
    - Smart RTL calculator: Can the drone make it home with remaining battery?
    - Geofence monitoring: Alert if drone exceeds radius from home
    - Altitude limit monitoring
    - Signal loss detection (heartbeat timeout)
    - Climb rate warnings
    - All alerts delivered via VoiceAssistant priority system
    """
    
    # Safety states
    STATE_SAFE = "SAFE"
    STATE_WARNING = "WARNING"
    STATE_CRITICAL = "CRITICAL"
    
    def __init__(self, telemetry_handler, voice_assistant):
        self.telemetry = telemetry_handler
        self.voice = voice_assistant
        
        # Configuration
        self.geofence_radius = 500  # meters
        self.max_altitude = 120  # meters (legal limit in many countries)
        self.battery_rtl_threshold = 30  # Start warning at 30%
        self.battery_critical_threshold = 15  # Critical at 15%
        self.heartbeat_timeout = 5.0  # seconds
        self.min_satellites = 6  # Minimum GPS satellites for safe flight
        
        # Home position (set when armed)
        self.home_lat = 0.0
        self.home_lon = 0.0
        self.home_set = False
        
        # State tracking
        self.overall_state = self.STATE_SAFE
        self.safety_checks = {}  # Dict of check_name -> {state, message}
        
        # Alert cooldowns (prevent spam)
        self._alert_cooldowns = {}
        self._cooldown_duration = 15.0  # seconds between repeated alerts
        
        # Last heartbeat time
        self._last_heartbeat_time = time.time()
        
        # Monitoring thread
        self.running = False
        self.thread = None
        
        # Callback for UI updates
        self.on_safety_update = None
    
    def start(self):
        """Start safety monitoring loop."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
    
    def set_home(self, lat, lon):
        """Set home/launch position for distance calculations."""
        if lat != 0.0 and lon != 0.0:
            self.home_lat = lat
            self.home_lon = lon
            self.home_set = True
    
    def heartbeat_received(self):
        """Call this when a heartbeat is received from the drone."""
        self._last_heartbeat_time = time.time()
    
    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS coordinates in meters."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def distance_to_home(self):
        """Get current distance to home in meters."""
        if not self.home_set:
            return 0.0
        lat = self.telemetry.data.get("lat", 0.0)
        lon = self.telemetry.data.get("lon", 0.0)
        if lat == 0.0 and lon == 0.0:
            return 0.0
        return self.haversine(self.home_lat, self.home_lon, lat, lon)
    
    def can_return_home(self):
        """
        Smart RTL calculator.
        Estimates if drone has enough battery to return home based on:
        - Distance to home
        - Current speed
        - Battery remaining
        - Battery consumption rate
        
        Returns: (can_return: bool, estimated_time_seconds: float, reason: str)
        """
        distance = self.distance_to_home()
        speed = self.telemetry.data.get("groundspeed", 0.0)
        battery = self.telemetry.data.get("battery", 0)
        
        if speed < 0.5:
            speed = 5.0  # Assume 5 m/s if stationary
        
        # Time to return home (seconds)
        time_to_home = distance / speed
        
        # Rough estimation: assume 1% battery per 30 seconds of flight
        # This is a simplification; real drones vary widely
        battery_needed = (time_to_home / 30.0) * 1.0
        battery_needed += 10  # Safety margin of 10%
        
        can_return = battery > battery_needed
        
        if can_return:
            reason = f"OK ({distance:.0f}m, ~{time_to_home:.0f}s)"
        else:
            reason = f"LOW BATTERY! Need ~{battery_needed:.0f}%, have {battery}%"
        
        return can_return, time_to_home, reason
    
    def _monitor_loop(self):
        """Main monitoring loop — runs every 2 seconds."""
        while self.running:
            if self.telemetry.connected:
                self._run_all_checks()
                self._update_overall_state()
                
                if self.on_safety_update:
                    try:
                        self.on_safety_update(self.overall_state, self.safety_checks)
                    except Exception:
                        pass
            
            time.sleep(2.0)
    
    def _run_all_checks(self):
        """Run all safety checks."""
        data = self.telemetry.data
        
        # Set home on first armed
        if data.get("armed", False) and not self.home_set:
            self.set_home(data.get("lat", 0.0), data.get("lon", 0.0))
        
        # 1. Battery / RTL Check
        self._check_battery(data)
        
        # 2. Geofence Check
        self._check_geofence(data)
        
        # 3. Altitude Limit Check
        self._check_altitude(data)
        
        # 4. Signal Loss Check
        self._check_heartbeat()
        
        # 5. GPS Quality Check
        self._check_gps(data)
        
        # 6. Climb Rate Check
        self._check_climb_rate(data)
    
    def _check_battery(self, data):
        battery = data.get("battery", 0)
        if battery <= 0:
            self.safety_checks["battery"] = {"state": self.STATE_SAFE, "message": "N/A"}
            return
        
        can_return, time_home, reason = self.can_return_home()
        
        if battery <= self.battery_critical_threshold:
            self.safety_checks["battery"] = {"state": self.STATE_CRITICAL, "message": f"CRITICAL {battery}%"}
            self._alert("battery_critical", "Batarya kritik! Hemen geri dön!", critical=True)
        elif battery <= self.battery_rtl_threshold or not can_return:
            self.safety_checks["battery"] = {"state": self.STATE_WARNING, "message": f"LOW {battery}% — {reason}"}
            self._alert("battery_low", f"Battery low. {reason}")
        else:
            self.safety_checks["battery"] = {"state": self.STATE_SAFE, "message": f"{battery}% — {reason}"}
    
    def _check_geofence(self, data):
        if not self.home_set:
            self.safety_checks["geofence"] = {"state": self.STATE_SAFE, "message": "Home not set"}
            return
        
        distance = self.distance_to_home()
        
        if distance > self.geofence_radius:
            self.safety_checks["geofence"] = {
                "state": self.STATE_WARNING,
                "message": f"OUTSIDE {distance:.0f}m (limit: {self.geofence_radius}m)"
            }
            self._alert("geofence", f"Geofence ihlali! Drone {distance:.0f} metre uzakta!")
        else:
            self.safety_checks["geofence"] = {
                "state": self.STATE_SAFE,
                "message": f"{distance:.0f}m / {self.geofence_radius}m"
            }
    
    def _check_altitude(self, data):
        alt = data.get("altitude", 0.0)
        
        if alt > self.max_altitude:
            self.safety_checks["altitude"] = {
                "state": self.STATE_WARNING,
                "message": f"OVER LIMIT {alt:.0f}m (max: {self.max_altitude}m)"
            }
            self._alert("altitude", f"İrtifa limiti aşıldı! {alt:.0f} metre!")
        else:
            self.safety_checks["altitude"] = {
                "state": self.STATE_SAFE,
                "message": f"{alt:.0f}m / {self.max_altitude}m"
            }
    
    def _check_heartbeat(self):
        elapsed = time.time() - self._last_heartbeat_time
        
        if elapsed > self.heartbeat_timeout:
            self.safety_checks["signal"] = {
                "state": self.STATE_CRITICAL,
                "message": f"LOST ({elapsed:.0f}s)"
            }
            self._alert("signal_lost", "Sinyal kaybı! Drone bağlantısı kesildi!", critical=True)
        else:
            self.safety_checks["signal"] = {
                "state": self.STATE_SAFE,
                "message": f"OK ({elapsed:.1f}s)"
            }
    
    def _check_gps(self, data):
        sats = data.get("satellites", 0)
        fix = data.get("gps_fix", 0)
        
        if fix < 3:
            self.safety_checks["gps"] = {
                "state": self.STATE_WARNING,
                "message": f"NO 3D FIX ({sats} SAT)"
            }
            self._alert("gps_fix", "GPS 3D fix kaybedildi!")
        elif sats < self.min_satellites:
            self.safety_checks["gps"] = {
                "state": self.STATE_WARNING,
                "message": f"LOW SATS ({sats})"
            }
        else:
            self.safety_checks["gps"] = {
                "state": self.STATE_SAFE,
                "message": f"{sats} SAT (Fix: {fix})"
            }
    
    def _check_climb_rate(self, data):
        climb = data.get("climb_rate", 0.0)
        
        if climb < -5.0:  # Falling faster than 5 m/s
            self.safety_checks["climb"] = {
                "state": self.STATE_CRITICAL,
                "message": f"RAPID DESCENT {climb:.1f} m/s"
            }
            self._alert("rapid_descent", "İrtifa hızla düşüyor!", critical=True)
        elif climb < -3.0:
            self.safety_checks["climb"] = {
                "state": self.STATE_WARNING,
                "message": f"DESCENDING {climb:.1f} m/s"
            }
        else:
            self.safety_checks["climb"] = {
                "state": self.STATE_SAFE,
                "message": f"{climb:+.1f} m/s"
            }
    
    def _update_overall_state(self):
        """Determine overall safety state from individual checks."""
        states = [check["state"] for check in self.safety_checks.values()]
        
        if self.STATE_CRITICAL in states:
            self.overall_state = self.STATE_CRITICAL
        elif self.STATE_WARNING in states:
            self.overall_state = self.STATE_WARNING
        else:
            self.overall_state = self.STATE_SAFE
    
    def _alert(self, alert_id, message, critical=False):
        """Send a voice alert with cooldown to prevent spam."""
        now = time.time()
        last_time = self._alert_cooldowns.get(alert_id, 0)
        
        if now - last_time >= self._cooldown_duration:
            if critical:
                self.voice.say_critical(message)
            else:
                self.voice.say_warning(message)
            self._alert_cooldowns[alert_id] = now
