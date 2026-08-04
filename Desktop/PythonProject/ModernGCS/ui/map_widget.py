import tkinter as tk
import tkintermapview
from tkinter import simpledialog
from PIL import Image, ImageTk
import os
import time
import cv2
import threading
from shapely.geometry import Polygon, Point
import numpy as np

class MapWidget(tk.Frame):
    """
    Modern map widget using tkintermapview.
    
    V4.0 Features:
    - Satellite/Normal/Terrain map type switching
    - Right-click "Go Here" for GUIDED navigation
    - Flight trail (polyline of past drone positions)
    - Waypoint altitude dialog on add
    - Visual path between waypoints
    """
    def __init__(self, master, telemetry_handler, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.telemetry = telemetry_handler
        self.waypoints = []
        self.drone_marker = None
        self.path = None
        self.flight_trail = None
        self._trail_positions = []
        self._current_map_type = "satellite"
        
        # Callback for goto command (set by app_window)
        self.on_goto = None
        
        # Map tile servers
        self._tile_servers = {
            "satellite": "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga",
            "normal": "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga",
            "terrain": "https://mt0.google.com/vt/lyrs=p&hl=en&x={x}&y={y}&z={z}&s=Ga",
        }
        
        # UI Setup
        self.map_view = tkintermapview.TkinterMapView(self, corner_radius=0)
        self.map_view.pack(fill="both", expand=True)
        
        # Set default view (Ankara, Turkey) and zoom
        self.map_view.set_position(39.92077, 32.85411)
        self.map_view.set_zoom(15)
        
        # Default satellite view
        self.map_view.set_tile_server(self._tile_servers["satellite"], max_zoom=22)
        
        # Right click menu
        self.map_view.add_right_click_menu_command(
            label="📍 Add Waypoint",
            command=self.add_waypoint,
            pass_coords=True
        )
        self.map_view.add_right_click_menu_command(
            label="🚀 Go Here (GUIDED)",
            command=self._goto_here,
            pass_coords=True
        )
        self.map_view.add_right_click_menu_command(
            label="🗑️ Clear Waypoints",
            command=self.clear_waypoints,
            pass_coords=False
        )
        self.map_view.add_right_click_menu_command(
            label="📐 Add Polygon Point",
            command=self.add_polygon_point,
            pass_coords=True
        )
        self.map_view.add_right_click_menu_command(
            label="🌐 Generate Grid (Polygon)",
            command=self.generate_grid,
            pass_coords=False
        )
        self.map_view.add_right_click_menu_command(
            label="🧹 Clear Polygon",
            command=self.clear_polygon,
            pass_coords=False
        )
                                                    
        # Load custom drone icon
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'drone_icon.png')
        try:
            pil_image = Image.open(icon_path).resize((48, 48))
            self.drone_icon = ImageTk.PhotoImage(pil_image)
        except Exception:
            self.drone_icon = None
            
        # Polygon state
        self.polygon_points = []
        self.polygon_path = None
            
        # Camera is now handled by the FPV window (fpv_window.py)
        self.cam_running = False

    def set_map_type(self, map_type):
        """Switch between satellite, normal, terrain."""
        if map_type in self._tile_servers:
            self._current_map_type = map_type
            self.map_view.set_tile_server(self._tile_servers[map_type], max_zoom=22)

    def add_waypoint(self, coords):
        """Add waypoint with altitude dialog."""
        # Ask for altitude
        try:
            alt = simpledialog.askinteger(
                "Waypoint Altitude",
                f"WP {len(self.waypoints)+1} için irtifa (metre):",
                initialvalue=20,
                minvalue=1,
                maxvalue=500,
                parent=self.winfo_toplevel()
            )
            if alt is None:
                alt = 20  # Cancelled, use default
        except Exception:
            alt = 20
        
        wp = {
            "lat": coords[0],
            "lon": coords[1],
            "alt": alt,
            "marker": self.map_view.set_marker(
                coords[0], coords[1],
                text=f"WP{len(self.waypoints)+1} ({alt}m)",
                marker_color_circle="#00e5ff",
                marker_color_outside="#0a0a0f"
            )
        }
        self.waypoints.append(wp)
        self.update_path()
        
    def clear_waypoints(self):
        try:
            for wp in self.waypoints:
                if wp.get("marker"):
                    wp["marker"].delete()
            self.waypoints.clear()
            if self.path:
                self.path.delete()
                self.path = None
        except Exception as e:
            print(f"Error clearing waypoints: {e}")
            
    def update_path(self):
        if self.path:
            self.path.delete()
        if len(self.waypoints) >= 2:
            positions = [(wp["lat"], wp["lon"]) for wp in self.waypoints]
            self.path = self.map_view.set_path(positions, color="#00ffcc", width=3)

    def _goto_here(self, coords):
        """Send GOTO command to the coordinates."""
        if self.on_goto:
            self.on_goto(coords[0], coords[1])

    def update_drone_position(self):
        lat = self.telemetry.data["lat"]
        lon = self.telemetry.data["lon"]
        
        # Update drone marker on map
        if lat != 0.0 and lon != 0.0:
            if not self.drone_marker:
                if self.drone_icon:
                    self.drone_marker = self.map_view.set_marker(lat, lon, icon=self.drone_icon, text="")
                else:
                    self.drone_marker = self.map_view.set_marker(
                        lat, lon, text="DRONE",
                        marker_color_circle="#00e5ff",
                        marker_color_outside="#111111"
                    )
                # İlk konum geldiğinde haritayı drone'a odakla
                self.map_view.set_position(lat, lon)
                self.map_view.set_zoom(18)
            else:
                self.drone_marker.set_position(lat, lon)

    def update_flight_trail(self):
        """Draw flight trail from telemetry handler's flight_path."""
        path_data = self.telemetry.flight_path
        
        if len(path_data) < 2:
            return
            
        # Only update if path changed (new points added)
        if len(path_data) == len(self._trail_positions):
            return
            
        self._trail_positions = list(path_data)
        
        # Remove old trail
        if self.flight_trail:
            try:
                self.flight_trail.delete()
            except Exception:
                pass
        
        # Draw new trail
        try:
            self.flight_trail = self.map_view.set_path(
                self._trail_positions,
                color="#f39c12",
                width=2
            )
        except Exception:
            pass

    # --- Polygon & Grid Mapping ---
    def add_polygon_point(self, coords):
        self.polygon_points.append(coords)
        if self.polygon_path:
            self.polygon_path.delete()
        
        # Draw polygon boundary
        if len(self.polygon_points) > 1:
            # close the loop visually if > 2 points
            pts = self.polygon_points.copy()
            if len(pts) > 2:
                pts.append(pts[0])
            self.polygon_path = self.map_view.set_path(pts, color="#ff4081", width=2)
            
    def clear_polygon(self):
        self.polygon_points.clear()
        if self.polygon_path:
            self.polygon_path.delete()
            self.polygon_path = None
            
    def generate_grid(self):
        if len(self.polygon_points) < 3:
            return
            
        try:
            # polygon_points are (lat, lon) tuples — convert to (lon, lat) for Shapely
            # Shapely uses (x, y) = (lon, lat) convention
            shapely_points = [(lon, lat) for lat, lon in self.polygon_points]
            poly = Polygon(shapely_points)
            minx, miny, maxx, maxy = poly.bounds  # minlon, minlat, maxlon, maxlat
            
            # Simple grid spacing (approx 0.0001 deg ~ 11 meters)
            spacing_lon = 0.0001
            spacing_lat = 0.0001
            
            grid_points = []
            x = minx  # longitude
            up = True
            while x <= maxx:
                y_coords = np.arange(miny, maxy, spacing_lat)
                if not up:
                    y_coords = y_coords[::-1]
                
                for y in y_coords:
                    p = Point(x, y)  # (lon, lat)
                    if poly.contains(p):
                        grid_points.append((y, x))  # Store as (lat, lon)
                
                x += spacing_lon
                up = not up
                
            # Add to waypoints
            if grid_points:
                alt = simpledialog.askinteger("Grid Alt", "Grid irtifası (m):", initialvalue=20)
                if not alt: alt = 20
                for pt in grid_points:
                    wp = {
                        "lat": pt[0],  # lat
                        "lon": pt[1],  # lon
                        "alt": alt,
                        "marker": self.map_view.set_marker(pt[0], pt[1], text="", marker_color_circle="#ffab00", marker_color_outside="#1a1a2e")
                    }
                    self.waypoints.append(wp)
                self.update_path()
        except Exception as e:
            print("Grid error:", e)

    def destroy(self):
        self.cam_running = False
        super().destroy()

