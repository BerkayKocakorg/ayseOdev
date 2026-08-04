import tkinter as tk
import math

class CompassWidget(tk.Canvas):
    """
    Modern circular compass widget showing drone heading.
    Drawn entirely with tkinter Canvas.
    
    Features:
    - Rotating compass rose with N/S/E/W labels
    - Degree tick marks every 10°, major ticks every 30°
    - Fixed heading indicator triangle at top
    - Digital heading readout
    """
    def __init__(self, parent, telemetry_handler, size=160, **kwargs):
        bg = kwargs.pop("bg", "#0a0a0f")
        super().__init__(parent, bg=bg, width=size, height=size, highlightthickness=0, **kwargs)
        self.telemetry = telemetry_handler
        self.size = size
        
        self.colors = {
            "ring": "#2a2a3a",
            "tick": "#888888",
            "major_tick": "#cccccc",
            "text": "#eeeeee",
            "north": "#ff1744",
            "indicator": "#00e5ff",
            "heading_text": "#f39c12",
            "bg": bg
        }
        
    def _rotate_point(self, px, py, cx, cy, angle_deg):
        angle_rad = math.radians(angle_deg)
        tx = px - cx
        ty = py - cy
        rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
        ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)
        return rx + cx, ry + cy

    def draw(self):
        self.delete("all")
        
        heading = self.telemetry.data.get("heading", 0)
        cx = self.size / 2
        cy = self.size / 2
        radius = (self.size / 2) - 15
        
        # 1. Outer ring
        self.create_oval(
            cx - radius - 2, cy - radius - 2,
            cx + radius + 2, cy + radius + 2,
            outline=self.colors["ring"], width=3
        )
        
        # 2. Tick marks and labels (rotate with heading)
        cardinal = {0: "N", 90: "E", 180: "S", 270: "W"}
        
        for deg in range(0, 360, 10):
            # Draw from drone's perspective: rotate ticks by -heading
            draw_angle = deg - heading - 90  # -90 because 0° = top
            
            rad = math.radians(draw_angle)
            
            is_major = (deg % 30 == 0)
            tick_inner = radius - (12 if is_major else 6)
            tick_outer = radius
            
            x1 = cx + tick_inner * math.cos(rad)
            y1 = cy + tick_inner * math.sin(rad)
            x2 = cx + tick_outer * math.cos(rad)
            y2 = cy + tick_outer * math.sin(rad)
            
            color = self.colors["north"] if deg == 0 else (self.colors["major_tick"] if is_major else self.colors["tick"])
            width = 3 if deg == 0 else (2 if is_major else 1)
            
            self.create_line(x1, y1, x2, y2, fill=color, width=width)
            
            # Labels for cardinal and intercardinal directions
            if deg in cardinal:
                label_r = radius - 22
                lx = cx + label_r * math.cos(rad)
                ly = cy + label_r * math.sin(rad)
                label_color = self.colors["north"] if deg == 0 else self.colors["text"]
                font_size = 12 if deg == 0 else 10
                self.create_text(lx, ly, text=cardinal[deg], fill=label_color,
                               font=("Segoe UI", font_size, "bold"))
        
        # 3. Fixed heading indicator triangle at top
        tri_size = 8
        self.create_polygon(
            cx, cy - radius - 8,
            cx - tri_size, cy - radius + 4,
            cx + tri_size, cy - radius + 4,
            fill=self.colors["indicator"], outline=""
        )
        
        # 4. Center heading readout
        self.create_text(cx, cy - 5, text=f"{int(heading)}°",
                        fill=self.colors["heading_text"],
                        font=("Consolas", 16, "bold"))
        self.create_text(cx, cy + 14, text="HDG",
                        fill=self.colors["tick"],
                        font=("Segoe UI", 8, "bold"))
        
        # 5. Small center dot
        self.create_oval(cx - 2, cy + 24, cx + 2, cy + 28,
                        fill=self.colors["indicator"], outline="")
