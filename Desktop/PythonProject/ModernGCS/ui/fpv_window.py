import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import threading


class FPVWindow(ctk.CTkToplevel):
    """
    FPV (First Person View) Camera Window with object detection and target tracking.
    
    Features:
    - Full-size video display from VideoStream
    - YOLOv8 detection overlay (bounding boxes + labels)
    - Click-to-track: click on a detection to start tracking
    - FPS and detection count HUD
    - Source selection (camera index, RTSP, video file)
    - Resizable and maximizable
    """
    
    def __init__(self, master, video_stream):
        super().__init__(master)
        self.video_stream = video_stream
        
        self.title("FPV — Camera & Detection")
        self.geometry("800x600")
        self.minsize(640, 480)
        
        self.colors = {
            "bg": "#0a0a0f",
            "panel": "#12121a",
            "accent_cyan": "#00e5ff",
            "accent_amber": "#f39c12",
            "accent_emerald": "#00c853",
            "danger": "#ff1744",
            "text": "#eeeeee",
            "text_muted": "#666680",
        }
        
        self.configure(fg_color=self.colors["bg"])
        
        # State
        self._current_frame = None
        self._current_detections = []
        self._current_track_bbox = None
        self._photo_image = None  # Keep reference to prevent GC
        
        self._build_ui()
        self._setup_callbacks()
        
        # Start the video stream if not already running
        if not self.video_stream.running:
            self.video_stream.start()
        
        # Bring to front
        self.lift()
        self.focus_force()
    
    def _build_ui(self):
        # ── Top Controls ──
        controls = ctk.CTkFrame(self, fg_color=self.colors["panel"], height=50, corner_radius=0)
        controls.pack(fill="x")
        controls.pack_propagate(False)
        
        inner = ctk.CTkFrame(controls, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Source selection
        ctk.CTkLabel(inner, text="SOURCE:", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=self.colors["text_muted"]).pack(side="left", padx=(0, 5))
        
        self.source_entry = ctk.CTkEntry(
            inner, width=200, height=28,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.colors["bg"], border_color="#2a2a3a",
            placeholder_text="0 / rtsp://... / video.mp4"
        )
        self.source_entry.insert(0, "0")
        self.source_entry.pack(side="left", padx=(0, 5))
        
        ctk.CTkButton(
            inner, text="▶ CONNECT", height=28, width=100,
            command=self._connect_source,
            fg_color=self.colors["accent_cyan"], text_color="black",
            hover_color="#00b8d4",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        ).pack(side="left", padx=(0, 10))
        
        # Detection toggle
        self.detect_var = ctk.BooleanVar(value=False)
        self.detect_switch = ctk.CTkSwitch(
            inner, text="🤖 YOLO Detection", variable=self.detect_var,
            command=self._toggle_detection,
            font=ctk.CTkFont(size=10),
            progress_color=self.colors["accent_emerald"]
        )
        self.detect_switch.pack(side="left", padx=10)
        
        # Tracking button
        self.btn_stop_track = ctk.CTkButton(
            inner, text="🎯 Stop Tracking", height=28, width=120,
            command=self._stop_tracking,
            fg_color=self.colors["danger"], hover_color="#b71c1c",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8,
            state="disabled"
        )
        self.btn_stop_track.pack(side="left", padx=5)
        
        # FPS Label
        self.lbl_fps = ctk.CTkLabel(
            inner, text="FPS: 0",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self.colors["accent_amber"]
        )
        self.lbl_fps.pack(side="right", padx=10)
        
        # Detection count
        self.lbl_detections = ctk.CTkLabel(
            inner, text="Objects: 0",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=self.colors["text"]
        )
        self.lbl_detections.pack(side="right", padx=10)
        
        # ── Video Canvas ──
        self.canvas = tk.Canvas(self, bg=self.colors["bg"], highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        
        # Click handler for tracking
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # Placeholder text
        self.canvas.create_text(
            400, 300, text="Kamera bağlantısı bekleniyor...\n\nKaynak girin ve CONNECT'e tıklayın",
            fill=self.colors["text_muted"], font=("Segoe UI", 14), justify="center"
        )
    
    def _setup_callbacks(self):
        """Register callback to receive frames from VideoStream."""
        self.video_stream.on_frame = self._on_frame
        # Start periodic UI update (30 FPS display)
        self._update_display()
    
    def _on_frame(self, frame, detections, track_bbox):
        """Called by VideoStream thread — store data for UI thread to display."""
        self._current_frame = frame.copy()
        self._current_detections = detections
        self._current_track_bbox = track_bbox
    
    def _update_display(self):
        """Periodic UI update — runs on main thread."""
        if not self.winfo_exists():
            return
        
        frame = self._current_frame
        if frame is not None:
            self._draw_frame(frame, self._current_detections, self._current_track_bbox)
        
        # Update HUD
        self.lbl_fps.configure(text=f"FPS: {self.video_stream.fps:.1f}")
        self.lbl_detections.configure(text=f"Objects: {len(self._current_detections)}")
        
        # Update tracking button state
        if self.video_stream.tracking_enabled:
            self.btn_stop_track.configure(state="normal")
        else:
            self.btn_stop_track.configure(state="disabled")
        
        self.after(33, self._update_display)  # ~30 FPS
    
    def _draw_frame(self, frame, detections, track_bbox):
        """Draw video frame with overlays on canvas."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w < 10 or canvas_h < 10:
            return
        
        # Resize frame to fit canvas while maintaining aspect ratio
        h, w = frame.shape[:2]
        scale = min(canvas_w / w, canvas_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(frame, (new_w, new_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Draw detection boxes and tracking box on the image
        pil_img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil_img)
        
        # Draw detection boxes
        for det in detections:
            x, y, bw, bh = det["bbox"]
            # Scale to display coordinates
            sx = int(x * scale)
            sy = int(y * scale)
            sw = int(bw * scale)
            sh = int(bh * scale)
            
            color = "#00e5ff"
            label = f"{det['label']} {det['confidence']:.0%}"
            
            draw.rectangle([sx, sy, sx + sw, sy + sh], outline=color, width=2)
            # Label background
            draw.rectangle([sx, sy - 18, sx + len(label) * 7 + 4, sy], fill=color)
            draw.text((sx + 2, sy - 16), label, fill="black")
        
        # Draw tracking box
        if track_bbox:
            tx, ty, tw, th = track_bbox
            sx = int(tx * scale)
            sy = int(ty * scale)
            sw = int(tw * scale)
            sh = int(th * scale)
            
            draw.rectangle([sx, sy, sx + sw, sy + sh], outline="#ff1744", width=3)
            draw.text((sx + 2, sy - 18), "🎯 TRACKING", fill="#ff1744")
        
        # Convert to PhotoImage
        self._photo_image = ImageTk.PhotoImage(pil_img)
        
        # Center on canvas
        offset_x = (canvas_w - new_w) // 2
        offset_y = (canvas_h - new_h) // 2
        
        self.canvas.delete("all")
        self.canvas.create_image(offset_x, offset_y, anchor="nw", image=self._photo_image)
        
        # Store scale and offset for click detection
        self._display_scale = scale
        self._display_offset = (offset_x, offset_y)
        self._display_size = (new_w, new_h)
    
    def _on_canvas_click(self, event):
        """Handle click on video — start tracking if clicking on a detection."""
        if not self._current_frame is not None or not self._current_detections:
            return
        
        if not hasattr(self, '_display_scale'):
            return
        
        # Convert click coordinates back to frame coordinates
        scale = self._display_scale
        ox, oy = self._display_offset
        
        frame_x = (event.x - ox) / scale
        frame_y = (event.y - oy) / scale
        
        # Check if click is within any detection box
        for det in self._current_detections:
            x, y, w, h = det["bbox"]
            if x <= frame_x <= x + w and y <= frame_y <= y + h:
                # Start tracking this object
                self.video_stream.start_tracking(self._current_frame, (x, y, w, h))
                self.video_stream.track_label = det["label"]
                return
    
    def _connect_source(self):
        """Connect to video source."""
        source = self.source_entry.get().strip()
        
        # Try to parse as integer (camera index)
        try:
            source = int(source)
        except ValueError:
            pass  # Keep as string (RTSP URL or file path)
        
        self.video_stream.set_source(source)
        if not self.video_stream.running:
            self.video_stream.start()
    
    def _toggle_detection(self):
        """Toggle YOLO detection on/off."""
        self.video_stream.enable_detection(self.detect_var.get())
    
    def _stop_tracking(self):
        """Stop target tracking."""
        self.video_stream.stop_tracking()
    
    def destroy(self):
        """Clean up when window is closed."""
        self.video_stream.on_frame = None
        super().destroy()
