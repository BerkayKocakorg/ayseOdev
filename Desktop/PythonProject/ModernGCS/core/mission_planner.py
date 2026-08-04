import json
import os
import math
from datetime import datetime


class MissionPlanner:
    """
    Mission planner for autonomous flight operations.
    
    Features:
    - Waypoint management (add, remove, reorder, edit altitude)
    - Mission command types: TAKEOFF, WAYPOINT, LAND, RTL, LOITER_TIME, DO_DIGICAM_CONTROL
    - Survey grid generation from polygon
    - Save/Load missions as JSON
    - Total distance and estimated time calculation
    """
    
    # Command types
    CMD_TAKEOFF = "NAV_TAKEOFF"
    CMD_WAYPOINT = "NAV_WAYPOINT"
    CMD_LAND = "NAV_LAND"
    CMD_RTL = "NAV_RETURN_TO_LAUNCH"
    CMD_LOITER_TIME = "NAV_LOITER_TIME"
    CMD_DO_PHOTO = "DO_DIGICAM_CONTROL"
    CMD_DO_CAM_TRIGG_DIST = "DO_SET_CAM_TRIGG_DIST"
    
    def __init__(self):
        self.mission_items = []  # List of mission item dicts
        self.on_mission_changed = None  # Callback when mission is modified
    
    def add_takeoff(self, altitude=10):
        """Add a takeoff command to the mission."""
        item = {
            "command": self.CMD_TAKEOFF,
            "lat": 0.0,
            "lon": 0.0,
            "alt": altitude,
            "param1": 0,  # pitch
            "param2": 0,
            "param3": 0,
            "param4": 0,  # yaw
            "label": f"TAKEOFF {altitude}m"
        }
        self.mission_items.append(item)
        self._notify_change()
        return len(self.mission_items) - 1
    
    def add_waypoint(self, lat, lon, alt=20):
        """Add a navigation waypoint."""
        item = {
            "command": self.CMD_WAYPOINT,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "param1": 0,  # hold time
            "param2": 0,  # acceptance radius
            "param3": 0,  # pass through
            "param4": 0,  # yaw
            "label": f"WP ({alt}m)"
        }
        self.mission_items.append(item)
        self._notify_change()
        return len(self.mission_items) - 1
    
    def add_land(self):
        """Add a land command."""
        item = {
            "command": self.CMD_LAND,
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0,
            "param1": 0,
            "param2": 0,
            "param3": 0,
            "param4": 0,
            "label": "LAND"
        }
        self.mission_items.append(item)
        self._notify_change()
        return len(self.mission_items) - 1
    
    def add_rtl(self):
        """Add a Return-to-Launch command."""
        item = {
            "command": self.CMD_RTL,
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0,
            "param1": 0,
            "param2": 0,
            "param3": 0,
            "param4": 0,
            "label": "RTL"
        }
        self.mission_items.append(item)
        self._notify_change()
        return len(self.mission_items) - 1
    
    def add_loiter_time(self, seconds=10, lat=0.0, lon=0.0, alt=0):
        """Add a loiter (hover/wait) command for given duration."""
        item = {
            "command": self.CMD_LOITER_TIME,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "param1": seconds,  # time in seconds
            "param2": 0,
            "param3": 0,
            "param4": 0,
            "label": f"LOITER {seconds}s"
        }
        self.mission_items.append(item)
        self._notify_change()
        return len(self.mission_items) - 1
    
    def add_photo(self):
        """Add a camera trigger command (take photo)."""
        item = {
            "command": self.CMD_DO_PHOTO,
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0,
            "param1": 0,
            "param2": 0,
            "param3": 0,
            "param4": 0,
            "label": "📷 PHOTO"
        }
        self.mission_items.append(item)
        self._notify_change()
        return len(self.mission_items) - 1
    
    def remove_item(self, index):
        """Remove a mission item by index."""
        if 0 <= index < len(self.mission_items):
            self.mission_items.pop(index)
            self._notify_change()
    
    def move_item(self, from_index, to_index):
        """Move a mission item from one position to another."""
        if 0 <= from_index < len(self.mission_items) and 0 <= to_index < len(self.mission_items):
            item = self.mission_items.pop(from_index)
            self.mission_items.insert(to_index, item)
            self._notify_change()
    
    def update_altitude(self, index, alt):
        """Update the altitude of a waypoint."""
        if 0 <= index < len(self.mission_items):
            self.mission_items[index]["alt"] = alt
            cmd = self.mission_items[index]["command"]
            if cmd == self.CMD_WAYPOINT:
                self.mission_items[index]["label"] = f"WP ({alt}m)"
            elif cmd == self.CMD_TAKEOFF:
                self.mission_items[index]["label"] = f"TAKEOFF {alt}m"
            self._notify_change()
    
    def clear(self):
        """Clear entire mission."""
        self.mission_items.clear()
        self._notify_change()
    
    def get_waypoints_for_upload(self):
        """
        Get waypoints formatted for MAVLink upload.
        Returns list of dicts with lat, lon, alt, and MAVLink command ID.
        """
        from pymavlink import mavutil
        
        cmd_map = {
            self.CMD_TAKEOFF: mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            self.CMD_WAYPOINT: mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            self.CMD_LAND: mavutil.mavlink.MAV_CMD_NAV_LAND,
            self.CMD_RTL: mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            self.CMD_LOITER_TIME: mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
            self.CMD_DO_PHOTO: mavutil.mavlink.MAV_CMD_DO_DIGICAM_CONTROL,
            self.CMD_DO_CAM_TRIGG_DIST: mavutil.mavlink.MAV_CMD_DO_SET_CAM_TRIGG_DIST,
        }
        
        result = []
        for item in self.mission_items:
            mav_cmd = cmd_map.get(item["command"], mavutil.mavlink.MAV_CMD_NAV_WAYPOINT)
            result.append({
                "lat": item["lat"],
                "lon": item["lon"],
                "alt": item["alt"],
                "command": mav_cmd,
                "param1": item.get("param1", 0),
                "param2": item.get("param2", 0),
                "param3": item.get("param3", 0),
                "param4": item.get("param4", 0),
            })
        return result
    
    def get_nav_waypoints(self):
        """Get only navigation waypoints (those with lat/lon) for map display."""
        return [
            item for item in self.mission_items
            if item["command"] in (self.CMD_WAYPOINT, self.CMD_TAKEOFF, self.CMD_LAND, self.CMD_LOITER_TIME)
            and (item["lat"] != 0.0 or item["lon"] != 0.0)
        ]
    
    # ─── Distance & Time Calculations ────────────────────────────────────
    
    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate distance between two GPS coordinates in meters."""
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def total_distance(self):
        """Calculate total mission distance in meters."""
        nav_wps = self.get_nav_waypoints()
        total = 0.0
        for i in range(1, len(nav_wps)):
            total += self.haversine(
                nav_wps[i - 1]["lat"], nav_wps[i - 1]["lon"],
                nav_wps[i]["lat"], nav_wps[i]["lon"]
            )
        return total
    
    def estimated_time(self, speed_ms=5.0):
        """Estimate total mission time in seconds at given speed (m/s)."""
        distance = self.total_distance()
        flight_time = distance / speed_ms if speed_ms > 0 else 0
        
        # Add loiter times
        for item in self.mission_items:
            if item["command"] == self.CMD_LOITER_TIME:
                flight_time += item.get("param1", 0)
        
        return flight_time
    
    # ─── Save / Load ─────────────────────────────────────────────────────
    
    def save_to_json(self, filepath):
        """Save mission to JSON file."""
        data = {
            "version": "5.0",
            "created": datetime.now().isoformat(),
            "mission_items": self.mission_items
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_json(self, filepath):
        """Load mission from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.mission_items = data.get("mission_items", [])
        self._notify_change()
    
    def _notify_change(self):
        """Notify listeners that mission has changed."""
        if self.on_mission_changed:
            try:
                self.on_mission_changed()
            except Exception:
                pass
