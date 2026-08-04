import threading
from .telemetry_handler import TelemetryHandler


class DroneInstance:
    """Represents a single drone with its own telemetry handler and metadata."""
    
    # Color palette for multi-drone visualization
    COLORS = [
        "#00e5ff",  # Cyan
        "#ff4081",  # Pink
        "#76ff03",  # Lime
        "#ff9100",  # Orange
        "#e040fb",  # Purple
        "#00e676",  # Green
        "#ffd740",  # Amber
        "#448aff",  # Blue
    ]
    
    def __init__(self, name, color_index=0):
        self.name = name
        self.color = self.COLORS[color_index % len(self.COLORS)]
        self.telemetry = TelemetryHandler()
        self.connection_string = ""
        self.connected = False
        self.marker = None  # Map marker reference


class SwarmManager:
    """
    Multi-drone (swarm) manager.
    
    Features:
    - Manage multiple drone connections simultaneously
    - Each drone has its own TelemetryHandler
    - Active drone selection for UI control
    - Batch commands (ARM ALL, DISARM ALL, RTL ALL)
    - Different colored markers for each drone
    """
    
    def __init__(self):
        self.drones = []  # List of DroneInstance
        self.active_index = -1  # Currently selected drone index
        self.max_drones = 8
        
        # Callbacks
        self.on_drone_list_changed = None
        self.on_active_changed = None
    
    @property
    def active_drone(self):
        """Get the currently active drone instance."""
        if 0 <= self.active_index < len(self.drones):
            return self.drones[self.active_index]
        return None
    
    @property
    def active_telemetry(self):
        """Get the telemetry handler for the active drone."""
        drone = self.active_drone
        return drone.telemetry if drone else None
    
    def add_drone(self, name=None):
        """
        Add a new drone to the swarm.
        Returns the index of the new drone, or -1 if max reached.
        """
        if len(self.drones) >= self.max_drones:
            return -1
        
        if name is None:
            name = f"Drone {len(self.drones) + 1}"
        
        drone = DroneInstance(name, len(self.drones))
        drone.telemetry.start()
        self.drones.append(drone)
        
        # Auto-select first drone
        if self.active_index < 0:
            self.active_index = 0
        
        self._notify_list_changed()
        return len(self.drones) - 1
    
    def remove_drone(self, index):
        """Remove a drone from the swarm."""
        if 0 <= index < len(self.drones):
            drone = self.drones[index]
            drone.telemetry.stop()
            self.drones.pop(index)
            
            # Adjust active index
            if self.active_index >= len(self.drones):
                self.active_index = len(self.drones) - 1
            
            self._notify_list_changed()
    
    def set_active(self, index):
        """Set the active drone by index."""
        if 0 <= index < len(self.drones):
            self.active_index = index
            if self.on_active_changed:
                try:
                    self.on_active_changed(index, self.drones[index])
                except Exception:
                    pass
    
    def connect_drone(self, index, connection_string):
        """Connect a specific drone."""
        if 0 <= index < len(self.drones):
            drone = self.drones[index]
            drone.connection_string = connection_string
            success, msg = drone.telemetry.connect(connection_string)
            drone.connected = success
            self._notify_list_changed()
            return success, msg
        return False, "Invalid drone index"
    
    def disconnect_drone(self, index):
        """Disconnect a specific drone."""
        if 0 <= index < len(self.drones):
            drone = self.drones[index]
            drone.telemetry.disconnect()
            drone.connected = False
            self._notify_list_changed()
    
    # ─── Batch Commands ──────────────────────────────────────────────────
    
    def arm_all(self):
        """ARM all connected drones."""
        for drone in self.drones:
            if drone.telemetry.connected:
                drone.telemetry.arm()
    
    def disarm_all(self):
        """DISARM all connected drones."""
        for drone in self.drones:
            if drone.telemetry.connected:
                drone.telemetry.disarm()
    
    def rtl_all(self):
        """Send RTL to all connected drones."""
        for drone in self.drones:
            if drone.telemetry.connected:
                drone.telemetry.rtl()
    
    def land_all(self):
        """Send LAND to all connected drones."""
        for drone in self.drones:
            if drone.telemetry.connected:
                drone.telemetry.land()
    
    def set_mode_all(self, mode):
        """Set flight mode on all connected drones."""
        for drone in self.drones:
            if drone.telemetry.connected:
                drone.telemetry.set_mode(mode)
    
    # ─── Utility ─────────────────────────────────────────────────────────
    
    def get_all_positions(self):
        """Get positions of all connected drones for map display."""
        positions = []
        for i, drone in enumerate(self.drones):
            if drone.telemetry.connected:
                lat = drone.telemetry.data.get("lat", 0.0)
                lon = drone.telemetry.data.get("lon", 0.0)
                if lat != 0.0 and lon != 0.0:
                    positions.append({
                        "index": i,
                        "name": drone.name,
                        "lat": lat,
                        "lon": lon,
                        "color": drone.color,
                        "altitude": drone.telemetry.data.get("altitude", 0.0),
                        "battery": drone.telemetry.data.get("battery", 0),
                    })
        return positions
    
    def stop_all(self):
        """Stop all telemetry handlers."""
        for drone in self.drones:
            drone.telemetry.stop()
    
    def _notify_list_changed(self):
        if self.on_drone_list_changed:
            try:
                self.on_drone_list_changed()
            except Exception:
                pass
