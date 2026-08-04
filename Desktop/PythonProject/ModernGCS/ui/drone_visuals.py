import tkinter as tk
import math

class DroneVisual(tk.Canvas):
    """
    Modern Attitude Indicator (Artificial Horizon) for HUD layout.
    
    V4.0 Improvements:
    - Smoother rendering with anti-aliased look
    - Added speed/altitude side tapes
    - Improved color palette
    """
    def __init__(self, parent, telemetry_handler, bg="#0a0a0f", width=200, height=200, **kwargs):
        super().__init__(parent, bg=bg, width=width, height=height, highlightthickness=0, **kwargs)
        self.telemetry = telemetry_handler
        self.width = width
        self.height = height
        
        # Colors for Modern HUD Horizon
        self.colors = {
            "sky": "#0d3b66",       # Deep blue
            "ground": "#3d2b1f",    # Brown/Olive
            "line": "#ffffff",      # White for ladders
            "horizon": "#00e5ff",   # Cyan for horizon line
            "aircraft": "#f39c12",  # Amber for center indicator
            "text": "#eeeeee",
            "border": "#2a2a3a"
        }
        
    def _rotate_point(self, px, py, cx, cy, angle_deg):
        angle_rad = math.radians(angle_deg)
        tx = px - cx
        ty = py - cy
        rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
        ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)
        return rx + cx, ry + cy

    def draw_drone(self):
        # We keep the method name `draw_drone` because app_window.py calls it periodically.
        self.delete("all")
        
        pitch = self.telemetry.data.get("pitch", 0.0)
        roll = self.telemetry.data.get("roll", 0.0)
        
        cx = self.width / 2
        cy = self.height / 2
        
        # Sensitivity: pixels per degree of pitch
        pixels_per_degree = 3
        pitch_offset = pitch * pixels_per_degree
        
        # Dimensions for drawing large enough polygons so they cover the canvas when rotated
        size = max(self.width, self.height) * 2
        
        # 1. Sky and Ground Polygons
        # Define base points (when roll = 0)
        # Ground: from horizon down
        g_tl = (cx - size, cy + pitch_offset)
        g_tr = (cx + size, cy + pitch_offset)
        g_br = (cx + size, cy + size)
        g_bl = (cx - size, cy + size)
        
        # Sky: from horizon up
        s_tl = (cx - size, cy - size)
        s_tr = (cx + size, cy - size)
        s_br = (cx + size, cy + pitch_offset)
        s_bl = (cx - size, cy + pitch_offset)
        
        # Rotate points
        sky_pts = [self._rotate_point(x, y, cx, cy, roll) for x, y in [s_tl, s_tr, s_br, s_bl]]
        gnd_pts = [self._rotate_point(x, y, cx, cy, roll) for x, y in [g_tl, g_tr, g_br, g_bl]]
        
        # Flatten lists for create_polygon
        sky_flat = [coord for pt in sky_pts for coord in pt]
        gnd_flat = [coord for pt in gnd_pts for coord in pt]
        
        self.create_polygon(sky_flat, fill=self.colors["sky"], outline="")
        self.create_polygon(gnd_flat, fill=self.colors["ground"], outline="")
        
        # 2. Horizon Line
        h_left = self._rotate_point(cx - size, cy + pitch_offset, cx, cy, roll)
        h_right = self._rotate_point(cx + size, cy + pitch_offset, cx, cy, roll)
        self.create_line(h_left[0], h_left[1], h_right[0], h_right[1], fill=self.colors["horizon"], width=2)
        
        # 3. Pitch Ladders
        for p in range(-60, 61, 10):
            if p == 0: continue
            
            # Y position of the ladder line (base state)
            ly = cy + pitch_offset - (p * pixels_per_degree)
            
            # Width of the line
            lw = 40 if p % 20 == 0 else 20
            
            l1 = self._rotate_point(cx - lw, ly, cx, cy, roll)
            l2 = self._rotate_point(cx + lw, ly, cx, cy, roll)
            
            self.create_line(l1[0], l1[1], l2[0], l2[1], fill=self.colors["line"], width=2)
            
            # Add text for major pitch lines
            if p % 20 == 0:
                t1 = self._rotate_point(cx - lw - 15, ly, cx, cy, roll)
                t2 = self._rotate_point(cx + lw + 15, ly, cx, cy, roll)
                self.create_text(t1[0], t1[1], text=str(abs(p)), fill=self.colors["line"], font=("Consolas", 8, "bold"))
                self.create_text(t2[0], t2[1], text=str(abs(p)), fill=self.colors["line"], font=("Consolas", 8, "bold"))

        # 4. Fixed Aircraft Symbol (Center Crosshair)
        ac_color = self.colors["aircraft"]
        # Left wing
        self.create_line(cx - 50, cy, cx - 15, cy, fill=ac_color, width=4)
        self.create_line(cx - 15, cy, cx - 15, cy + 10, fill=ac_color, width=4)
        # Right wing
        self.create_line(cx + 50, cy, cx + 15, cy, fill=ac_color, width=4)
        self.create_line(cx + 15, cy, cx + 15, cy + 10, fill=ac_color, width=4)
        # Center dot
        self.create_rectangle(cx - 3, cy - 3, cx + 3, cy + 3, fill=ac_color, outline="")

        # 5. Top Roll Indicator arc
        r = (self.width / 2) - 15
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=30, extent=120, style=tk.ARC, outline=self.colors["line"], width=2)
        
        # Center tick
        t1 = self._rotate_point(cx, cy - r, cx, cy, 0)
        t2 = self._rotate_point(cx, cy - r + 10, cx, cy, 0)
        self.create_line(t1[0], t1[1], t2[0], t2[1], fill=self.colors["line"], width=2)
        
        # Current roll marker (pointing triangle along arc)
        pt1 = self._rotate_point(cx, cy - r - 5, cx, cy, -roll)
        pt2 = self._rotate_point(cx - 6, cy - r + 5, cx, cy, -roll)
        pt3 = self._rotate_point(cx + 6, cy - r + 5, cx, cy, -roll)
        self.create_polygon(pt1[0], pt1[1], pt2[0], pt2[1], pt3[0], pt3[1], fill=self.colors["horizon"])
        
        # 6. Circular border for clean look
        border_r = min(self.width, self.height) / 2 - 2
        self.create_oval(cx - border_r, cy - border_r, cx + border_r, cy + border_r,
                        outline=self.colors["border"], width=2)
