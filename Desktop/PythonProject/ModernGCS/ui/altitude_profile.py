import tkinter as tk
import math


class AltitudeProfileWidget(tk.Canvas):
    """
    Real-time altitude profile widget.
    
    Features:
    - Scrolling altitude graph over time/distance
    - Terrain reference line (configurable)
    - Current altitude indicator
    - Altitude history visualization
    - Min/Max/Avg altitude display
    - Terrain clearance warning zone
    """
    
    def __init__(self, parent, telemetry_handler, width=290, height=120, **kwargs):
        bg = kwargs.pop("bg", "#0a0a0f")
        super().__init__(parent, bg=bg, width=width, height=height, highlightthickness=0, **kwargs)
        
        self.telemetry = telemetry_handler
        self.w = width
        self.h = height
        
        # Altitude history (rolling buffer)
        self.altitude_history = []
        self.max_points = 150  # Number of data points to show
        
        # Terrain reference (can be set dynamically)
        self.terrain_altitude = 0.0  # Ground level reference
        self.terrain_clearance_min = 5.0  # Minimum safe altitude above terrain
        
        # Colors
        self.colors = {
            "bg": bg,
            "grid": "#1a1a2e",
            "altitude_line": "#00e5ff",
            "altitude_fill": "#00e5ff",
            "terrain_line": "#3d2b1f",
            "terrain_fill": "#2a1f15",
            "warning_zone": "#ff174420",
            "text": "#eeeeee",
            "text_muted": "#666680",
            "danger": "#ff1744",
            "safe": "#00c853",
        }
    
    def update_altitude(self):
        """Call this periodically to add current altitude to history."""
        alt = self.telemetry.data.get("altitude", 0.0)
        self.altitude_history.append(alt)
        
        # Trim to max points
        if len(self.altitude_history) > self.max_points:
            self.altitude_history = self.altitude_history[-self.max_points:]
    
    def draw(self):
        """Draw the altitude profile."""
        self.delete("all")
        
        if len(self.altitude_history) < 2:
            self.create_text(
                self.w // 2, self.h // 2,
                text="Altitude data collecting...",
                fill=self.colors["text_muted"],
                font=("Consolas", 9)
            )
            return
        
        # Margins
        margin_left = 35
        margin_right = 10
        margin_top = 15
        margin_bottom = 20
        
        graph_w = self.w - margin_left - margin_right
        graph_h = self.h - margin_top - margin_bottom
        
        # Calculate data range
        data = self.altitude_history
        max_alt = max(max(data), self.terrain_altitude + 10, 10)
        min_alt = min(min(data), self.terrain_altitude, 0)
        alt_range = max_alt - min_alt
        if alt_range < 5:
            alt_range = 5
        
        # ── Background Grid ──
        num_grid_lines = 4
        for i in range(num_grid_lines + 1):
            y = margin_top + (i / num_grid_lines) * graph_h
            self.create_line(margin_left, y, self.w - margin_right, y,
                           fill=self.colors["grid"], width=1, dash=(2, 4))
            
            # Y-axis labels
            alt_val = max_alt - (i / num_grid_lines) * alt_range
            self.create_text(margin_left - 5, y, text=f"{alt_val:.0f}",
                           fill=self.colors["text_muted"], font=("Consolas", 7),
                           anchor="e")
        
        # ── Terrain Fill (ground level) ──
        terrain_y = margin_top + ((max_alt - self.terrain_altitude) / alt_range) * graph_h
        terrain_y = max(margin_top, min(self.h - margin_bottom, terrain_y))
        
        # Fill ground area
        self.create_rectangle(
            margin_left, terrain_y,
            self.w - margin_right, self.h - margin_bottom,
            fill=self.colors["terrain_fill"], outline=""
        )
        
        # Terrain line
        self.create_line(
            margin_left, terrain_y,
            self.w - margin_right, terrain_y,
            fill=self.colors["terrain_line"], width=2, dash=(4, 2)
        )
        
        # Warning zone (terrain clearance minimum)
        warning_alt = self.terrain_altitude + self.terrain_clearance_min
        warning_y = margin_top + ((max_alt - warning_alt) / alt_range) * graph_h
        warning_y = max(margin_top, min(self.h - margin_bottom, warning_y))
        
        if warning_y < terrain_y:
            self.create_rectangle(
                margin_left, warning_y,
                self.w - margin_right, terrain_y,
                fill="#331a1a", outline=""
            )
            self.create_line(
                margin_left, warning_y,
                self.w - margin_right, warning_y,
                fill=self.colors["danger"], width=1, dash=(3, 3)
            )
        
        # ── Altitude Line ──
        points = []
        fill_points = []
        
        for i, alt in enumerate(data):
            x = margin_left + (i / (len(data) - 1)) * graph_w
            y = margin_top + ((max_alt - alt) / alt_range) * graph_h
            y = max(margin_top, min(self.h - margin_bottom, y))
            points.append((x, y))
            fill_points.append((x, y))
        
        # Fill under altitude line (gradient effect)
        if fill_points:
            fill_polygon = list(fill_points)
            fill_polygon.append((fill_points[-1][0], self.h - margin_bottom))
            fill_polygon.append((fill_points[0][0], self.h - margin_bottom))
            flat = [coord for pt in fill_polygon for coord in pt]
            self.create_polygon(flat, fill="#0a2a3a", outline="")
        
        # Draw altitude line
        if len(points) >= 2:
            flat_line = [coord for pt in points for coord in pt]
            self.create_line(flat_line, fill=self.colors["altitude_line"], width=2, smooth=True)
        
        # ── Current Altitude Indicator ──
        if points:
            cx, cy = points[-1]
            current_alt = data[-1]
            
            # Dot at current position
            self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                           fill=self.colors["altitude_line"], outline="white", width=1)
            
            # Current altitude text
            color = self.colors["safe"] if current_alt > (self.terrain_altitude + self.terrain_clearance_min) else self.colors["danger"]
            self.create_text(
                self.w - margin_right - 5, margin_top + 5,
                text=f"{current_alt:.1f}m",
                fill=color,
                font=("Consolas", 11, "bold"),
                anchor="ne"
            )
        
        # ── Stats ──
        if data:
            avg_alt = sum(data) / len(data)
            stats_text = f"Avg:{avg_alt:.0f} Max:{max(data):.0f} Min:{min(data):.0f}"
            self.create_text(
                margin_left + 5, self.h - 5,
                text=stats_text,
                fill=self.colors["text_muted"],
                font=("Consolas", 7),
                anchor="sw"
            )
        
        # ── Label ──
        self.create_text(
            margin_left + 5, margin_top - 3,
            text="GND",
            fill=self.colors["terrain_line"],
            font=("Consolas", 7),
            anchor="sw"
        )
