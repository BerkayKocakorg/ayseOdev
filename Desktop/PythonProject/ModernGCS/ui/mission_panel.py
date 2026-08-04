import customtkinter as ctk
from tkinter import filedialog, messagebox


class MissionPanel(ctk.CTkFrame):
    """
    Mission planning UI panel.
    
    Features:
    - Scrollable waypoint list with index, type, coordinates, altitude
    - Add mission commands: Takeoff, Waypoint, Loiter, Photo, Land, RTL
    - Remove individual items or clear all
    - Save/Load mission as JSON
    - Total distance and estimated time display
    - Upload mission to drone
    """
    
    def __init__(self, master, mission_planner, telemetry_handler, colors, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.planner = mission_planner
        self.telemetry = telemetry_handler
        self.colors = colors
        
        # Callbacks (set by app_window)
        self.on_upload = None
        self.on_execute = None
        self.on_log = None
        
        self._build_ui()
        
        # Listen for mission changes
        self.planner.on_mission_changed = self._refresh_list
    
    def _build_ui(self):
        # ── Command Buttons ──
        cmd_frame = ctk.CTkFrame(self, fg_color="transparent")
        cmd_frame.pack(fill="x", pady=(0, 4))
        
        # Row 1: Takeoff + Land
        row1 = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        row1.pack(fill="x", pady=1)
        ctk.CTkButton(
            row1, text="🚀 Takeoff", height=26,
            command=self._add_takeoff,
            fg_color=self.colors["accent_emerald"], text_color="black",
            hover_color="#00a844",
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            row1, text="🛬 Land", height=26,
            command=self._add_land,
            fg_color=self.colors["accent_cyan"], text_color="black",
            hover_color="#00b8d4",
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            row1, text="🏠 RTL", height=26,
            command=self._add_rtl,
            fg_color=self.colors["warning"], text_color="black",
            hover_color="#e69a00",
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True)
        
        # Row 2: Loiter + Photo
        row2 = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        row2.pack(fill="x", pady=1)
        ctk.CTkButton(
            row2, text="⏱ Loiter", height=26,
            command=self._add_loiter,
            fg_color=self.colors["bg_input"], text_color=self.colors["text"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            row2, text="📷 Photo", height=26,
            command=self._add_photo,
            fg_color=self.colors["bg_input"], text_color=self.colors["text"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True)
        
        # ── Waypoint List ──
        self.wp_list_frame = ctk.CTkScrollableFrame(
            self, fg_color=self.colors["bg_input"],
            height=150, corner_radius=8,
            scrollbar_button_color=self.colors["border"],
            scrollbar_button_hover_color=self.colors["text_muted"]
        )
        self.wp_list_frame.pack(fill="x", pady=4)
        
        # Placeholder
        self.placeholder_label = ctk.CTkLabel(
            self.wp_list_frame,
            text="Görev listesi boş\nHaritaya sağ tıklayarak waypoint ekleyin",
            text_color=self.colors["text_dim"],
            font=ctk.CTkFont(size=9)
        )
        self.placeholder_label.pack(pady=10)
        
        # ── Info Row (Distance + Time) ──
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", pady=2)
        
        self.lbl_distance = ctk.CTkLabel(
            info_frame, text="📏 0 m",
            text_color=self.colors["text_muted"],
            font=ctk.CTkFont(size=9)
        )
        self.lbl_distance.pack(side="left")
        
        self.lbl_time = ctk.CTkLabel(
            info_frame, text="⏱ 0s",
            text_color=self.colors["text_muted"],
            font=ctk.CTkFont(size=9)
        )
        self.lbl_time.pack(side="right")
        
        # ── Action Buttons ──
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", pady=(2, 0))
        
        # Row: Upload + Clear
        row_uc = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_uc.pack(fill="x", pady=1)
        ctk.CTkButton(
            row_uc, text="📤 UPLOAD", height=28,
            command=self._upload_mission,
            fg_color=self.colors["accent_cyan"], text_color="black",
            hover_color="#00b8d4",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            row_uc, text="🗑 CLEAR", height=28,
            command=self._clear_all,
            fg_color=self.colors["bg_input"], text_color=self.colors["text"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True)
        
        # Execute button
        ctk.CTkButton(
            action_frame, text="▶ EXECUTE AUTO MISSION", height=32,
            command=self._execute_mission,
            fg_color=self.colors["accent_emerald"], text_color="black",
            hover_color="#00a844",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8
        ).pack(fill="x", pady=(2, 1))
        
        # Save / Load
        row_sl = ctk.CTkFrame(action_frame, fg_color="transparent")
        row_sl.pack(fill="x", pady=1)
        ctk.CTkButton(
            row_sl, text="💾 Save", height=24,
            command=self._save_mission,
            fg_color=self.colors["bg_input"], text_color=self.colors["text_muted"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            row_sl, text="📂 Load", height=24,
            command=self._load_mission,
            fg_color=self.colors["bg_input"], text_color=self.colors["text_muted"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9), corner_radius=6
        ).pack(side="left", fill="x", expand=True)
    
    def _refresh_list(self):
        """Refresh the waypoint list display."""
        # Clear existing items
        for widget in self.wp_list_frame.winfo_children():
            widget.destroy()
        
        items = self.planner.mission_items
        
        if not items:
            self.placeholder_label = ctk.CTkLabel(
                self.wp_list_frame,
                text="Görev listesi boş\nHaritaya sağ tıklayarak waypoint ekleyin",
                text_color=self.colors["text_dim"],
                font=ctk.CTkFont(size=9)
            )
            self.placeholder_label.pack(pady=10)
            self.lbl_distance.configure(text="📏 0 m")
            self.lbl_time.configure(text="⏱ 0s")
            return
        
        for i, item in enumerate(items):
            row = ctk.CTkFrame(self.wp_list_frame, fg_color="transparent", height=24)
            row.pack(fill="x", pady=1)
            
            # Index
            ctk.CTkLabel(
                row, text=f"{i+1}.",
                font=ctk.CTkFont(family="Consolas", size=9),
                text_color=self.colors["accent_cyan"], width=20
            ).pack(side="left")
            
            # Command type with color coding
            cmd = item["command"]
            cmd_colors = {
                "NAV_TAKEOFF": self.colors["accent_emerald"],
                "NAV_WAYPOINT": self.colors["accent_cyan"],
                "NAV_LAND": self.colors["accent_amber"],
                "NAV_RETURN_TO_LAUNCH": self.colors["warning"],
                "NAV_LOITER_TIME": self.colors["text_muted"],
                "DO_DIGICAM_CONTROL": self.colors["text"],
            }
            cmd_short = cmd.replace("NAV_", "").replace("DO_", "")[:8]
            
            ctk.CTkLabel(
                row, text=cmd_short,
                font=ctk.CTkFont(size=8, weight="bold"),
                text_color=cmd_colors.get(cmd, self.colors["text"]),
                width=55
            ).pack(side="left")
            
            # Coordinates (if available)
            if item["lat"] != 0.0 or item["lon"] != 0.0:
                coord_text = f"{item['lat']:.5f}, {item['lon']:.5f}"
            else:
                coord_text = "—"
            
            ctk.CTkLabel(
                row, text=coord_text,
                font=ctk.CTkFont(family="Consolas", size=8),
                text_color=self.colors["text_muted"]
            ).pack(side="left", padx=(2, 0))
            
            # Alt
            if item["alt"] > 0:
                ctk.CTkLabel(
                    row, text=f"{item['alt']}m",
                    font=ctk.CTkFont(family="Consolas", size=8),
                    text_color=self.colors["accent_amber"], width=30
                ).pack(side="left", padx=2)
            
            # Delete button
            idx = i  # Capture index for closure
            ctk.CTkButton(
                row, text="✕", width=20, height=18,
                command=lambda idx=idx: self._remove_item(idx),
                fg_color="transparent", text_color=self.colors["danger"],
                hover_color=self.colors["border"],
                font=ctk.CTkFont(size=10), corner_radius=4
            ).pack(side="right")
        
        # Update stats
        dist = self.planner.total_distance()
        time_s = self.planner.estimated_time()
        
        if dist >= 1000:
            dist_text = f"📏 {dist/1000:.1f} km"
        else:
            dist_text = f"📏 {dist:.0f} m"
        
        if time_s >= 60:
            time_text = f"⏱ {int(time_s//60)}m {int(time_s%60)}s"
        else:
            time_text = f"⏱ {time_s:.0f}s"
        
        self.lbl_distance.configure(text=dist_text)
        self.lbl_time.configure(text=time_text)
    
    # ── Command Handlers ──
    
    def _add_takeoff(self):
        self.planner.add_takeoff(altitude=10)
        self._log("Added TAKEOFF command")
    
    def _add_land(self):
        self.planner.add_land()
        self._log("Added LAND command")
    
    def _add_rtl(self):
        self.planner.add_rtl()
        self._log("Added RTL command")
    
    def _add_loiter(self):
        self.planner.add_loiter_time(seconds=10)
        self._log("Added LOITER 10s command")
    
    def _add_photo(self):
        self.planner.add_photo()
        self._log("Added PHOTO command")
    
    def _remove_item(self, index):
        self.planner.remove_item(index)
        self._log(f"Removed mission item #{index + 1}")
    
    def _clear_all(self):
        self.planner.clear()
        self._log("Mission cleared")
    
    def _upload_mission(self):
        if self.on_upload:
            self.on_upload()
    
    def _execute_mission(self):
        if self.on_execute:
            self.on_execute()
    
    def _save_mission(self):
        filepath = filedialog.asksaveasfilename(
            title="Save Mission",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            parent=self.winfo_toplevel()
        )
        if filepath:
            try:
                self.planner.save_to_json(filepath)
                self._log(f"Mission saved: {filepath.split('/')[-1]}")
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {e}", parent=self.winfo_toplevel())
    
    def _load_mission(self):
        filepath = filedialog.askopenfilename(
            title="Load Mission",
            filetypes=[("JSON files", "*.json")],
            parent=self.winfo_toplevel()
        )
        if filepath:
            try:
                self.planner.load_from_json(filepath)
                self._log(f"Mission loaded: {filepath.split('/')[-1]}")
            except Exception as e:
                messagebox.showerror("Error", f"Load failed: {e}", parent=self.winfo_toplevel())
    
    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)
