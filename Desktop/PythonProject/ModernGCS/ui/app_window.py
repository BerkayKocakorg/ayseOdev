import customtkinter as ctk
import threading
import os
from tkinter import messagebox
from .map_widget import MapWidget
from .drone_visuals import DroneVisual
from .compass_widget import CompassWidget
from .tutorial_guide import TutorialGuide
from .log_analyzer import LogAnalyzerWindow
from .fpv_window import FPVWindow
from .mission_panel import MissionPanel
from .swarm_panel import SwarmPanel
from .altitude_profile import AltitudeProfileWidget

from core.video_stream import VideoStream
from core.mission_planner import MissionPlanner
from core.safety_monitor import SafetyMonitor
from core.weather_service import WeatherService


class AppWindow:
    """
    Modern GCS V5.0 — Tactical Dashboard
    
    Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │  TOP BAR: LED | Mode | Alt | Speed | Climb | Battery | GPS    │
    ├──────────────────────────────────────────┬──────────────────────┤
    │                                          │  RIGHT PANEL         │
    │            FULL MAP                      │  Swarm Panel         │
    │                                          │  Quick Actions       │
    │                                          │  Mission Panel       │
    │                                          │  FPV & Camera        │
    │                                          │  Safety & Weather    │
    │                                          │  HUD + Compass       │
    │                                          │  Altitude Profile    │
    │                                          │  Map Controls        │
    │                                          │  Telemetry Recording │
    ├──────────────────────────────────────────┴──────────────────────┤
    │  BOTTOM: Logs + Connection + KILL SWITCH                       │
    └─────────────────────────────────────────────────────────────────┘
    """
    def __init__(self, root, telemetry_handler, swarm_manager=None):
        self.root = root
        self.telemetry = telemetry_handler
        self.swarm = swarm_manager
        
        self.root.title("Modern GCS — Tactical Dashboard V5.0")
        self.root.geometry("1600x900")
        self.root.minsize(1200, 700)
        
        # ── Design System ──
        self.colors = {
            "bg_deep":       "#0a0a0f",
            "bg_panel":      "#12121a",
            "bg_card":       "#1a1a2e",
            "bg_input":      "#0f0f1a",
            "accent_cyan":   "#00e5ff",
            "accent_amber":  "#f39c12",
            "accent_emerald":"#00c853",
            "danger":        "#ff1744",
            "danger_dark":   "#b71c1c",
            "text":          "#eeeeee",
            "text_muted":    "#666680",
            "text_dim":      "#444455",
            "border":        "#2a2a3a",
            "success":       "#00c853",
            "warning":       "#ffab00",
        }
        
        self.root.configure(fg_color=self.colors["bg_deep"])
        
        # Battery warning state
        self._battery_flash = False
        self._battery_warning_level = 0  # 0=normal, 1=low(20%), 2=critical(10%)
        
        # Connection LED animation state
        self._led_pulse = False
        
        # Collapsible panel states
        self._panel_states = {}
        
        # ── Initialize new subsystems ──
        self.video_stream = VideoStream()
        self.mission_planner = MissionPlanner()
        self.safety_monitor = SafetyMonitor(self.telemetry, self.telemetry.voice)
        self.weather_service = WeatherService()
        
        # FPV window reference
        self._fpv_window = None
        
        self._setup_ui()
        self._setup_tutorial()
        self._setup_safety()
        self._setup_weather()
        
        self.telemetry.on_data_updated = self.update_ui
        self.root.after(50, self._periodic_update)
        self.root.after(500, self._battery_flash_tick)
        self.root.after(1000, self._led_pulse_tick)
        self.root.after(5000, self._swarm_info_update)

    # ═══════════════════════════════════════════════════════════════════
    # UI SETUP
    # ═══════════════════════════════════════════════════════════════════

    def _setup_ui(self):
        # ── Top Bar ──
        self.top_bar = ctk.CTkFrame(self.root, fg_color=self.colors["bg_deep"], corner_radius=0, height=65)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)
        self._build_top_bar()
        
        # ── Bottom Bar ──
        self.bottom_bar = ctk.CTkFrame(self.root, fg_color=self.colors["bg_deep"], corner_radius=0, height=160)
        self.bottom_bar.pack(fill="x", side="bottom")
        self.bottom_bar.pack_propagate(False)
        self._build_bottom_bar()
        
        # ── Main Area (Map + Right Panel) ──
        main_area = ctk.CTkFrame(self.root, fg_color=self.colors["bg_deep"], corner_radius=0)
        main_area.pack(fill="both", expand=True)
        
        # Right panel
        self.right_panel = ctk.CTkScrollableFrame(
            main_area, fg_color=self.colors["bg_panel"],
            width=310, corner_radius=0,
            scrollbar_button_color=self.colors["border"],
            scrollbar_button_hover_color=self.colors["text_muted"]
        )
        self.right_panel.pack(side="right", fill="y")
        self._build_right_panel()
        
        # Map (fills remaining space)
        self.map_widget = MapWidget(main_area, self.telemetry)
        self.map_widget.pack(side="left", fill="both", expand=True)
        self.map_widget.on_goto = self._cmd_goto

    # ─── TOP BAR ─────────────────────────────────────────────────────

    def _build_top_bar(self):
        container = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=15, pady=5)
        
        # Connection LED
        led_frame = ctk.CTkFrame(container, fg_color="transparent")
        led_frame.pack(side="left", padx=(5, 15))
        self.led_canvas = ctk.CTkCanvas(led_frame, width=18, height=18,
                                         bg=self.colors["bg_deep"], highlightthickness=0)
        self.led_canvas.pack(pady=12)
        self._draw_led(False)
        
        # Separator
        self._add_vsep(container)
        
        # Stat blocks
        self.lbl_mode = self._create_stat(container, "FLIGHT MODE", "DISARMED", self.colors["text"])
        self._add_vsep(container)
        self.lbl_alt = self._create_stat(container, "ALT (REL)", "0.0 m", self.colors["accent_amber"])
        self._add_vsep(container)
        self.lbl_speed = self._create_stat(container, "GND SPEED", "0.0 m/s", self.colors["accent_cyan"])
        self._add_vsep(container)
        self.lbl_climb = self._create_stat(container, "CLIMB", "0.0 m/s", self.colors["text"])
        self._add_vsep(container)
        self.lbl_bat = self._create_stat(container, "BATTERY", "0%", self.colors["success"])
        self._add_vsep(container)
        self.lbl_voltage = self._create_stat(container, "VOLTAGE", "0.0 V", self.colors["text_muted"], font_size=16)
        self._add_vsep(container)
        self.lbl_current = self._create_stat(container, "CURRENT", "0.0 A", self.colors["text_muted"], font_size=16)
        self._add_vsep(container)
        self.lbl_gps = self._create_stat(container, "GPS", "0 SAT", self.colors["text"], font_size=16)
        self._add_vsep(container)
        self.lbl_gps_fix = self._create_stat(container, "FIX", "NO FIX", self.colors["danger"], font_size=14)
        self._add_vsep(container)
        
        # Safety status indicator
        self.lbl_safety = self._create_stat(container, "SAFETY", "—", self.colors["text_muted"], font_size=14)
        
        # Right side: Tutorial button
        self.btn_tutorial = ctk.CTkButton(
            container, text="❓", command=self.start_tutorial,
            fg_color=self.colors["bg_card"], hover_color=self.colors["border"],
            text_color=self.colors["accent_amber"],
            font=ctk.CTkFont(size=16), width=36, height=36, corner_radius=18
        )
        self.btn_tutorial.pack(side="right", padx=10)

    def _create_stat(self, parent, title, value, color, font_size=22):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=10)
        ctk.CTkLabel(frame, text=title,
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=self.colors["text_muted"]).pack(anchor="w")
        lbl = ctk.CTkLabel(frame, text=value,
                           font=ctk.CTkFont(family="Consolas", size=font_size, weight="bold"),
                           text_color=color)
        lbl.pack(anchor="w")
        return lbl

    def _add_vsep(self, parent):
        sep = ctk.CTkFrame(parent, fg_color=self.colors["border"], width=1, height=40)
        sep.pack(side="left", padx=5, pady=10, fill="y")

    # ─── COLLAPSIBLE SECTION HELPER ──────────────────────────────────

    def _collapsible_section(self, parent, title, default_open=True):
        """Create a collapsible section with toggle button. Returns (card_frame, content_frame)."""
        section_id = title
        self._panel_states[section_id] = default_open
        
        # Container to maintain order when card is hidden
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", pady=0)
        
        # Header with toggle
        header = ctk.CTkFrame(container, fg_color="transparent", height=24)
        header.pack(fill="x", padx=8, pady=(8, 0))
        
        arrow_text = "▾" if default_open else "▸"
        arrow_btn = ctk.CTkButton(
            header, text=f"{arrow_text} {title}", anchor="w",
            fg_color="transparent", hover_color=self.colors["bg_card"],
            text_color=self.colors["text_muted"],
            font=ctk.CTkFont(size=9, weight="bold"),
            height=20, corner_radius=4,
            command=lambda: self._toggle_section(section_id, card, arrow_btn, title)
        )
        arrow_btn.pack(fill="x")
        
        # Card
        card = ctk.CTkFrame(container, fg_color=self.colors["bg_card"], corner_radius=12)
        card.pack(fill="x", padx=8, pady=(2, 2))
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=8)
        
        if not default_open:
            card.pack_forget()
        
        return card, content
    
    def _toggle_section(self, section_id, card, arrow_btn, title):
        """Toggle a collapsible section."""
        is_open = self._panel_states.get(section_id, True)
        
        if is_open:
            card.pack_forget()
            arrow_btn.configure(text=f"▸ {title}")
            self._panel_states[section_id] = False
        else:
            card.pack(fill="x", padx=8, pady=(2, 2))
            arrow_btn.configure(text=f"▾ {title}")
            self._panel_states[section_id] = True

    # ─── RIGHT PANEL ─────────────────────────────────────────────────

    def _build_right_panel(self):
        panel = self.right_panel
        
        # ── Section: Swarm (Multi-Drone) ──
        if self.swarm:
            card, content = self._collapsible_section(panel, "SWARM / MULTI-DRONE", default_open=False)
            self.swarm_panel = SwarmPanel(content, self.swarm, self.colors)
            self.swarm_panel.pack(fill="x")
            self.swarm_panel.on_log = lambda msg: self.log(f"[SWARM] {msg}")
        
        # ── Section: Quick Actions ──
        card, content = self._collapsible_section(panel, "QUICK ACTIONS")
        self._build_quick_actions(content)
        
        # ── Section: Mission Planner ──
        card, content = self._collapsible_section(panel, "MISSION PLANNER")
        self.mission_panel = MissionPanel(content, self.mission_planner, self.telemetry, self.colors)
        self.mission_panel.pack(fill="x")
        self.mission_panel.on_upload = self._cmd_upload_mission
        self.mission_panel.on_execute = self._cmd_start_mission
        self.mission_panel.on_log = lambda msg: self.log(f"[MISSION] {msg}")
        
        # ── Section: FPV & Camera ──
        card, content = self._collapsible_section(panel, "FPV & CAMERA", default_open=False)
        self._build_fpv_section(content)
        
        # ── Section: Safety & Weather ──
        card, content = self._collapsible_section(panel, "SAFETY & WEATHER")
        self._build_safety_section(content)
        
        # ── Section: Map Controls ──
        card, content = self._collapsible_section(panel, "MAP CONTROLS", default_open=False)
        self._build_map_controls(content)
        
        # ── Section: Telemetry Recording ──
        card, content = self._collapsible_section(panel, "TELEMETRY RECORDING", default_open=False)
        self._build_telemetry_section(content)
        
        # ── Section: HUD (Attitude Indicator) ──
        card, content = self._collapsible_section(panel, "ATTITUDE INDICATOR")
        self.drone_visual = DroneVisual(content, self.telemetry,
                                         bg=self.colors["bg_card"],
                                         height=160, width=290)
        self.drone_visual.pack(padx=5, pady=5)
        
        # ── Section: Compass ──
        card, content = self._collapsible_section(panel, "HEADING COMPASS")
        self.compass = CompassWidget(content, self.telemetry,
                                      size=140, bg=self.colors["bg_card"])
        self.compass.pack(padx=5, pady=5)
        
        # ── Section: Altitude Profile ──
        card, content = self._collapsible_section(panel, "ALTITUDE PROFILE")
        self.altitude_profile = AltitudeProfileWidget(
            content, self.telemetry,
            width=290, height=120, bg=self.colors["bg_card"]
        )
        self.altitude_profile.pack(padx=5, pady=5)

    def _build_quick_actions(self, parent):
        """Build the quick actions section content."""
        # Mode selector
        mode_row = ctk.CTkFrame(parent, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 4))
        self.mode_cb = ctk.CTkComboBox(
            mode_row, values=["GUIDED", "LOITER", "RTL", "AUTO", "STABILIZE", "LAND", "ALT_HOLD"],
            width=130, height=28, font=ctk.CTkFont(size=11),
            fg_color=self.colors["bg_input"], border_color=self.colors["border"],
            button_color=self.colors["border"], button_hover_color=self.colors["text_muted"],
            dropdown_fg_color=self.colors["bg_card"]
        )
        self.mode_cb.set("GUIDED")
        self.mode_cb.pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            mode_row, text="SET MODE", height=28,
            command=lambda: self._cmd_set_mode(),
            fg_color=self.colors["accent_amber"], text_color="black",
            hover_color="#e6890a",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True)
        
        # ARM / DISARM
        arm_row = ctk.CTkFrame(parent, fg_color="transparent")
        arm_row.pack(fill="x", pady=2)
        ctk.CTkButton(
            arm_row, text="🔓 ARM", height=30, command=self._cmd_arm,
            fg_color=self.colors["danger"], hover_color=self.colors["danger_dark"],
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(
            arm_row, text="🔒 DISARM", height=30, command=self._cmd_disarm,
            fg_color=self.colors["bg_input"], hover_color=self.colors["border"],
            text_color=self.colors["text"],
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8
        ).pack(side="right", fill="x", expand=True)
        
        # TAKEOFF
        takeoff_row = ctk.CTkFrame(parent, fg_color="transparent")
        takeoff_row.pack(fill="x", pady=2)
        ctk.CTkLabel(takeoff_row, text="Alt:", text_color=self.colors["text_muted"],
                     font=ctk.CTkFont(size=10)).pack(side="left")
        self.takeoff_alt_entry = ctk.CTkEntry(
            takeoff_row, width=50, height=28,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.colors["bg_input"], border_color=self.colors["border"],
            justify="center"
        )
        self.takeoff_alt_entry.insert(0, "10")
        self.takeoff_alt_entry.pack(side="left", padx=3)
        ctk.CTkLabel(takeoff_row, text="m", text_color=self.colors["text_muted"],
                     font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            takeoff_row, text="🚀 TAKEOFF", height=28, command=self._cmd_takeoff,
            fg_color=self.colors["accent_emerald"], text_color="black",
            hover_color="#00a844",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True)
        
        # LAND / RTL
        lr_row = ctk.CTkFrame(parent, fg_color="transparent")
        lr_row.pack(fill="x", pady=2)
        ctk.CTkButton(
            lr_row, text="🛬 LAND", height=30, command=self._cmd_land,
            fg_color=self.colors["accent_cyan"], text_color="black",
            hover_color="#00b8d4",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(
            lr_row, text="🏠 RTL", height=30, command=self._cmd_rtl,
            fg_color=self.colors["warning"], text_color="black",
            hover_color="#e69a00",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8
        ).pack(side="right", fill="x", expand=True)
        
        # PARAMETERS
        param_row = ctk.CTkFrame(parent, fg_color="transparent")
        param_row.pack(fill="x", pady=2)
        ctk.CTkButton(
            param_row, text="⚙️ PARAMETERS", height=28, command=self._cmd_parameters,
            fg_color=self.colors["bg_input"], text_color=self.colors["text"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        ).pack(side="left", fill="x", expand=True)

    def _build_fpv_section(self, parent):
        """Build the FPV & Camera section content."""
        ctk.CTkButton(
            parent, text="📷 OPEN FPV WINDOW", height=32,
            command=self._open_fpv_window,
            fg_color=self.colors["accent_cyan"], text_color="black",
            hover_color="#00b8d4",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8
        ).pack(fill="x", pady=(0, 4))
        
        # Quick info
        self.lbl_fpv_status = ctk.CTkLabel(
            parent, text="FPV: Not connected",
            text_color=self.colors["text_dim"],
            font=ctk.CTkFont(size=9)
        )
        self.lbl_fpv_status.pack(anchor="w")

    def _build_safety_section(self, parent):
        """Build the Safety & Weather section content."""
        # Safety status rows
        safety_grid = ctk.CTkFrame(parent, fg_color="transparent")
        safety_grid.pack(fill="x", pady=(0, 4))
        
        self.safety_labels = {}
        checks = [
            ("battery", "🔋 Battery"),
            ("geofence", "📍 Geofence"),
            ("altitude", "📏 Altitude"),
            ("signal", "📡 Signal"),
            ("gps", "🛰 GPS"),
            ("climb", "📐 Climb"),
        ]
        
        for i, (key, label) in enumerate(checks):
            row = ctk.CTkFrame(safety_grid, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=9),
                        text_color=self.colors["text_muted"], width=80, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(family="Consolas", size=9),
                              text_color=self.colors["text_dim"])
            lbl.pack(side="left", fill="x", expand=True)
            self.safety_labels[key] = lbl
        
        # Geofence setting
        geo_row = ctk.CTkFrame(parent, fg_color="transparent")
        geo_row.pack(fill="x", pady=2)
        ctk.CTkLabel(geo_row, text="Geofence:", text_color=self.colors["text_muted"],
                     font=ctk.CTkFont(size=9)).pack(side="left")
        self.geofence_entry = ctk.CTkEntry(
            geo_row, width=50, height=22,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=self.colors["bg_input"], border_color=self.colors["border"],
            justify="center"
        )
        self.geofence_entry.insert(0, "500")
        self.geofence_entry.pack(side="left", padx=3)
        ctk.CTkLabel(geo_row, text="m", text_color=self.colors["text_muted"],
                     font=ctk.CTkFont(size=9)).pack(side="left")
        ctk.CTkButton(
            geo_row, text="SET", width=40, height=22,
            command=self._set_geofence,
            fg_color=self.colors["border"], hover_color=self.colors["text_muted"],
            text_color=self.colors["text"],
            font=ctk.CTkFont(size=8, weight="bold"), corner_radius=4
        ).pack(side="left", padx=3)
        
        # Weather section
        sep = ctk.CTkFrame(parent, fg_color=self.colors["border"], height=1)
        sep.pack(fill="x", pady=6)
        
        ctk.CTkLabel(parent, text="WEATHER", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=self.colors["text_muted"]).pack(anchor="w")
        
        weather_grid = ctk.CTkFrame(parent, fg_color="transparent")
        weather_grid.pack(fill="x", pady=2)
        
        # Weather info labels
        self.weather_labels = {}
        weather_items = [
            ("condition", "🌤 Durum"),
            ("wind", "💨 Rüzgar"),
            ("temp", "🌡 Sıcaklık"),
            ("flight_ok", "✈ Uçuş"),
        ]
        
        for key, label in weather_items:
            row = ctk.CTkFrame(weather_grid, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=9),
                        text_color=self.colors["text_muted"], width=70, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="—", font=ctk.CTkFont(family="Consolas", size=9),
                              text_color=self.colors["text_dim"])
            lbl.pack(side="left", fill="x", expand=True)
            self.weather_labels[key] = lbl
        
        ctk.CTkButton(
            parent, text="🔄 Refresh Weather", height=24,
            command=self._refresh_weather,
            fg_color=self.colors["bg_input"], text_color=self.colors["text_muted"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9), corner_radius=6
        ).pack(fill="x", pady=(4, 0))

    def _build_map_controls(self, parent):
        """Build the Map Controls section content."""
        self.map_type_var = ctk.StringVar(value="satellite")
        self.map_type_seg = ctk.CTkSegmentedButton(
            parent, values=["satellite", "normal", "terrain"],
            variable=self.map_type_var,
            command=self._on_map_type_change,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=self.colors["bg_input"],
            selected_color=self.colors["accent_cyan"],
            selected_hover_color="#00b8d4",
            unselected_color=self.colors["bg_input"],
            unselected_hover_color=self.colors["border"],
            text_color="black",
            corner_radius=8
        )
        self.map_type_seg.pack(fill="x")

    def _build_telemetry_section(self, parent):
        """Build the Telemetry Recording section content."""
        self.btn_log_toggle = ctk.CTkButton(
            parent, text="⏺ START RECORDING", height=30,
            command=self._cmd_toggle_logging,
            fg_color=self.colors["bg_input"], hover_color=self.colors["border"],
            text_color=self.colors["danger"],
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        )
        self.btn_log_toggle.pack(fill="x", pady=(0, 4))
        
        self.btn_analyze_log = ctk.CTkButton(
            parent, text="📊 ANALYZE LOG", height=30,
            command=self._cmd_analyze_log,
            fg_color=self.colors["accent_cyan"], hover_color="#00b8d4",
            text_color="black", state="disabled",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=8
        )
        self.btn_analyze_log.pack(fill="x")
        
        self.lbl_log_status = ctk.CTkLabel(
            parent, text="Not recording",
            text_color=self.colors["text_dim"],
            font=ctk.CTkFont(size=9)
        )
        self.lbl_log_status.pack(anchor="w", pady=(2, 0))

    # ─── BOTTOM BAR ──────────────────────────────────────────────────

    def _build_bottom_bar(self):
        # Left: Connection + Logs
        left_section = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        left_section.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        # Connection row
        conn_row = ctk.CTkFrame(left_section, fg_color="transparent")
        conn_row.pack(fill="x", pady=(2, 4))
        
        ctk.CTkLabel(conn_row, text="DATALINK",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=self.colors["text_muted"]).pack(side="left", padx=(0, 8))
        
        self.port_entry = ctk.CTkEntry(
            conn_row, width=200, height=28,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=self.colors["bg_input"], border_color=self.colors["border"],
            placeholder_text="tcp:127.0.0.1:5762"
        )
        self.port_entry.insert(0, "tcp:127.0.0.1:5762")
        self.port_entry.pack(side="left", padx=(0, 6))
        
        self.btn_connect = ctk.CTkButton(
            conn_row, text="CONNECT", height=28,
            command=self.toggle_connection,
            fg_color=self.colors["accent_cyan"], text_color="black",
            hover_color="#00b8d4",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=8,
            width=120
        )
        self.btn_connect.pack(side="left")
        
        # Log textbox
        self.log_box = ctk.CTkTextbox(
            left_section,
            fg_color=self.colors["bg_input"],
            text_color=self.colors["text"],
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=8,
            border_width=1,
            border_color=self.colors["border"]
        )
        self.log_box.pack(fill="both", expand=True, pady=(0, 2))
        self.log_box.insert("end", "[SYS] TACTICAL DASHBOARD V5.0 LOADED\n")
        self.log_box.insert("end", "[SYS] Right-click map to add waypoints or navigate\n")
        self.log_box.configure(state="disabled")
        
        # Right: KILL SWITCH
        kill_section = ctk.CTkFrame(self.bottom_bar, fg_color="transparent", width=200)
        kill_section.pack(side="right", fill="y", padx=10, pady=8)
        kill_section.pack_propagate(False)
        
        ctk.CTkLabel(kill_section, text="EMERGENCY",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=self.colors["danger"]).pack(pady=(0, 4))
        
        self.btn_kill = ctk.CTkButton(
            kill_section, text="⚠ KILL\nSWITCH",
            command=self._cmd_emergency_stop,
            fg_color=self.colors["danger"], hover_color=self.colors["danger_dark"],
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
            corner_radius=12
        )
        self.btn_kill.pack(fill="both", expand=True)

    # ═══════════════════════════════════════════════════════════════════
    # SETUP METHODS
    # ═══════════════════════════════════════════════════════════════════

    def _setup_safety(self):
        """Initialize safety monitor."""
        self.safety_monitor.on_safety_update = self._on_safety_update
        self.safety_monitor.start()
    
    def _setup_weather(self):
        """Initialize weather service."""
        self.weather_service.on_weather_updated = self._on_weather_update
        self.weather_service.start()
    
    def _on_safety_update(self, overall_state, checks):
        """Called by SafetyMonitor when safety state changes."""
        try:
            self.root.after(0, lambda: self._apply_safety_update(overall_state, checks))
        except Exception:
            pass
    
    def _apply_safety_update(self, overall_state, checks):
        """Apply safety update on UI thread."""
        # Update top bar safety indicator
        state_map = {
            "SAFE": (self.colors["success"], "SAFE ✓"),
            "WARNING": (self.colors["warning"], "WARN ⚠"),
            "CRITICAL": (self.colors["danger"], "CRIT ⛔"),
        }
        color, text = state_map.get(overall_state, (self.colors["text_muted"], "—"))
        self.lbl_safety.configure(text=text, text_color=color)
        
        # Update individual safety check labels
        for key, lbl in self.safety_labels.items():
            check = checks.get(key, {})
            state = check.get("state", "SAFE")
            message = check.get("message", "—")
            
            state_colors = {
                "SAFE": self.colors["success"],
                "WARNING": self.colors["warning"],
                "CRITICAL": self.colors["danger"],
            }
            lbl.configure(text=message, text_color=state_colors.get(state, self.colors["text_dim"]))
    
    def _on_weather_update(self, weather_data):
        """Called by WeatherService when weather is fetched."""
        try:
            self.root.after(0, lambda: self._apply_weather_update(weather_data))
        except Exception:
            pass
    
    def _apply_weather_update(self, data):
        """Apply weather update on UI thread."""
        if not data.get("available"):
            return
        
        self.weather_labels["condition"].configure(
            text=data["weather_text"],
            text_color=self.colors["text"]
        )
        
        arrow = self.weather_service.get_wind_arrow()
        wind_text = f"{data['wind_speed']} m/s {arrow} (gust: {data['wind_gusts']})"
        
        safety = data["flight_safety"]
        safety_colors = {
            "SAFE": self.colors["success"],
            "CAUTION": self.colors["warning"],
            "DANGEROUS": self.colors["danger"],
        }
        
        self.weather_labels["wind"].configure(
            text=wind_text,
            text_color=safety_colors.get(safety, self.colors["text"])
        )
        self.weather_labels["temp"].configure(
            text=f"{data['temperature']}°C | {data['humidity']}% RH",
            text_color=self.colors["text"]
        )
        self.weather_labels["flight_ok"].configure(
            text=safety,
            text_color=safety_colors.get(safety, self.colors["text"])
        )

    # ═══════════════════════════════════════════════════════════════════
    # COMMANDS
    # ═══════════════════════════════════════════════════════════════════

    def log(self, msg, color=None):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def toggle_connection(self):
        if not self.telemetry.connected:
            port = self.port_entry.get()
            self.log(f"Connecting to {port}...")
            success, msg = self.telemetry.connect(port)
            if success:
                self.btn_connect.configure(
                    text="DISCONNECT",
                    fg_color=self.colors["danger"],
                    hover_color=self.colors["danger_dark"],
                    text_color="white"
                )
                self.log("DATALINK ESTABLISHED ✓")
                
                # Update weather location from drone position
                lat = self.telemetry.data.get("lat", 0.0)
                lon = self.telemetry.data.get("lon", 0.0)
                if lat != 0.0 and lon != 0.0:
                    self.weather_service.set_location(lat, lon)
            else:
                self.log(f"DATALINK FAILED: {msg}")
        else:
            self.telemetry.disconnect()
            self.btn_connect.configure(
                text="CONNECT",
                fg_color=self.colors["accent_cyan"],
                hover_color="#00b8d4",
                text_color="black"
            )
            self.log("DATALINK DISCONNECTED")

    def _cmd_arm(self):
        # Pre-Flight Checklist
        checklist = ctk.CTkToplevel(self.root)
        checklist.title("PRE-FLIGHT CHECKLIST")
        checklist.geometry("300x350")
        checklist.configure(fg_color=self.colors["bg_deep"])
        checklist.lift()
        checklist.focus_force()
        checklist.grab_set()
        
        ctk.CTkLabel(checklist, text="SYSTEM CHECKS", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors["accent_cyan"]).pack(pady=10)
        
        data = self.telemetry.data
        checks_passed = True
        
        # GPS Check
        has_gps = data['gps_fix'] >= 3
        if not has_gps: checks_passed = False
        gps_color = self.colors["success"] if has_gps else self.colors["danger"]
        gps_text = f"GPS Fix: {'OK' if has_gps else 'FAIL (Need 3D)'}"
        ctk.CTkLabel(checklist, text=gps_text, text_color=gps_color).pack(pady=5)
        
        # Battery Check
        has_bat = data['battery'] >= 80 or data['battery'] == 0
        if not has_bat: checks_passed = False
        bat_color = self.colors["success"] if has_bat else self.colors["danger"]
        bat_text = f"Battery: {'OK' if has_bat else 'LOW (<80%)'}"
        ctk.CTkLabel(checklist, text=bat_text, text_color=bat_color).pack(pady=5)
        
        # Mode Check
        mode_ok = data['mode'] in ["GUIDED", "LOITER", "STABILIZE"]
        if not mode_ok: checks_passed = False
        mode_color = self.colors["success"] if mode_ok else self.colors["danger"]
        mode_text = f"Mode: {'OK' if mode_ok else 'UNSAFE (' + data['mode'] + ')'}"
        ctk.CTkLabel(checklist, text=mode_text, text_color=mode_color).pack(pady=5)
        
        # Weather Check (NEW in V5.0)
        weather_ok = self.weather_service.data.get("flight_safety", "UNKNOWN") != "DANGEROUS"
        if not weather_ok: checks_passed = False
        weather_color = self.colors["success"] if weather_ok else self.colors["danger"]
        weather_text = f"Weather: {'OK' if weather_ok else 'DANGEROUS CONDITIONS'}"
        ctk.CTkLabel(checklist, text=weather_text, text_color=weather_color).pack(pady=5)
        
        def arm_drone():
            self.log("ARMING DRONE...")
            self.telemetry.arm()
            # Set home position for safety monitor
            lat = self.telemetry.data.get("lat", 0.0)
            lon = self.telemetry.data.get("lon", 0.0)
            self.safety_monitor.set_home(lat, lon)
            checklist.destroy()
            
        if checks_passed:
            ctk.CTkLabel(checklist, text="ALL SYSTEMS GO", text_color=self.colors["success"], font=ctk.CTkFont(weight="bold")).pack(pady=10)
            ctk.CTkButton(checklist, text="🚀 ARM", command=arm_drone, fg_color=self.colors["success"], hover_color="#00a844").pack(pady=10)
        else:
            ctk.CTkLabel(checklist, text="CHECKS FAILED", text_color=self.colors["danger"], font=ctk.CTkFont(weight="bold")).pack(pady=10)
            ctk.CTkButton(checklist, text="⚠️ FORCE ARM", command=arm_drone, fg_color=self.colors["danger"], hover_color=self.colors["danger_dark"]).pack(pady=10)
            
        ctk.CTkButton(checklist, text="CANCEL", command=checklist.destroy, fg_color=self.colors["bg_input"], hover_color=self.colors["border"]).pack(pady=5)

    def _cmd_disarm(self):
        self.log("DISARMING DRONE...")
        self.telemetry.disarm()

    def _cmd_set_mode(self):
        mode = self.mode_cb.get()
        self.log(f"Setting mode: {mode}")
        self.telemetry.set_mode(mode)

    def _cmd_parameters(self):
        if not self.telemetry.connected:
            messagebox.showerror("Error", "Connect to drone first!")
            return
            
        param_win = ctk.CTkToplevel(self.root)
        param_win.title("Parameter Editor")
        param_win.geometry("400x250")
        param_win.configure(fg_color=self.colors["bg_deep"])
        param_win.lift()
        param_win.focus_force()
        param_win.grab_set()
        
        ctk.CTkLabel(param_win, text="SET PARAMETER", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.colors["accent_cyan"]).pack(pady=10)
        
        p_frame = ctk.CTkFrame(param_win, fg_color="transparent")
        p_frame.pack(pady=10)
        
        ctk.CTkLabel(p_frame, text="Param Name (e.g. WPNAV_SPEED):").grid(row=0, column=0, padx=5, pady=5)
        name_entry = ctk.CTkEntry(p_frame, width=150)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(p_frame, text="Value (Float):").grid(row=1, column=0, padx=5, pady=5)
        val_entry = ctk.CTkEntry(p_frame, width=150)
        val_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def set_param():
            p_name = name_entry.get().upper().encode('utf-8')
            try:
                p_val = float(val_entry.get())
                if self.telemetry.mav:
                    self.telemetry.mav.mav.param_set_send(
                        self.telemetry.mav.target_system,
                        self.telemetry.mav.target_component,
                        p_name,
                        p_val,
                        9 # MAV_PARAM_TYPE_REAL32
                    )
                    self.log(f"Sent Param Set: {name_entry.get().upper()} = {p_val}")
                    param_win.destroy()
            except ValueError:
                messagebox.showerror("Error", "Invalid value format. Must be float.", parent=param_win)
                
        ctk.CTkButton(param_win, text="SEND PARAMETER", command=set_param, fg_color=self.colors["accent_emerald"], text_color="black").pack(pady=15)

    def _cmd_takeoff(self):
        try:
            alt = float(self.takeoff_alt_entry.get())
        except ValueError:
            self.log("ERROR: Invalid altitude value")
            return
        
        if alt < 1 or alt > 500:
            self.log("ERROR: Altitude must be between 1-500m")
            return
            
        confirm = messagebox.askyesno(
            "Takeoff Confirmation",
            f"Drone {alt}m irtifaya kalkış yapacak.\nOnaylıyor musunuz?",
            parent=self.root
        )
        if confirm:
            self.log(f"TAKEOFF to {alt}m...")
            self.telemetry.takeoff(alt)

    def _cmd_land(self):
        self.log("LANDING...")
        self.telemetry.land()

    def _cmd_rtl(self):
        self.log("RETURNING TO LAUNCH...")
        self.telemetry.rtl()

    def _cmd_emergency_stop(self):
        confirm = messagebox.askyesno(
            "⚠ EMERGENCY KILL SWITCH",
            "DİKKAT: Bu komut drone'u ANINDA kapatacak!\n"
            "Drone havadaysa DÜŞECEK!\n\n"
            "Emin misiniz?",
            icon="warning",
            parent=self.root
        )
        if confirm:
            self.log("⚠ EMERGENCY STOP ACTIVATED ⚠")
            self.telemetry.emergency_stop()

    def _cmd_goto(self, lat, lon):
        alt = self.telemetry.data.get("altitude", 20)
        if alt < 5:
            alt = 20
        self.log(f"GOTO: {lat:.6f}, {lon:.6f} @ {alt:.0f}m")
        self.telemetry.goto(lat, lon, alt)
        
        # Also add as waypoint to mission planner
        self.mission_planner.add_waypoint(lat, lon, alt)

    def _cmd_clear_wp(self):
        self.map_widget.clear_waypoints()
        self.mission_planner.clear()
        self.log("WAYPOINTS CLEARED")

    def _cmd_upload_mission(self):
        items = self.mission_planner.get_waypoints_for_upload()
        if not items:
            # Fallback to map waypoints if mission planner is empty
            wps = self.map_widget.waypoints
            if len(wps) < 1:
                self.log("ERROR: No waypoints to upload")
                return
            mission_wps = [{"lat": w["lat"], "lon": w["lon"], "alt": w.get("alt", 20)} for w in wps]
        else:
            mission_wps = [{"lat": i["lat"], "lon": i["lon"], "alt": i["alt"]} for i in items if i["lat"] != 0.0 or i["lon"] != 0.0]
        
        if not mission_wps:
            self.log("ERROR: No navigation waypoints in mission")
            return
        
        self.log(f"UPLOADING {len(mission_wps)} WAYPOINTS...")
        
        def _upload_thread():
            success, msg = self.telemetry.upload_mission(mission_wps)
            self.root.after(0, lambda: self._on_upload_complete(success, msg, len(mission_wps)))
        
        threading.Thread(target=_upload_thread, daemon=True).start()

    def _on_upload_complete(self, success, msg, wp_count):
        if success:
            self.log(f"MISSION UPLOAD SUCCESSFUL ✓ ({wp_count} WPs)")
        else:
            self.log(f"UPLOAD FAILED: {msg}")

    def _cmd_start_mission(self):
        self.log("RESETTING MISSION INDEX...")
        self.telemetry.reset_mission_current()
        self.log("EXECUTING AUTO MISSION ▶")
        self.telemetry.set_mode("AUTO")

    def _on_map_type_change(self, value):
        self.map_widget.set_map_type(value)
        self.log(f"Map type: {value}")

    def _cmd_toggle_logging(self):
        if self.telemetry.is_logging:
            self.telemetry.stop_logging()
            self.btn_log_toggle.configure(
                text="⏺ START RECORDING",
                fg_color=self.colors["bg_input"],
                text_color=self.colors["danger"]
            )
            self.lbl_log_status.configure(text="Not recording")
            self.log("Telemetry recording STOPPED")
            
            if hasattr(self, '_last_log_path') and self._last_log_path:
                self.btn_analyze_log.configure(state="normal")
        else:
            success, result = self.telemetry.start_logging()
            if success:
                self._last_log_path = result
                self.btn_log_toggle.configure(
                    text="⏹ STOP RECORDING",
                    fg_color=self.colors["danger"],
                    text_color="white"
                )
                self.btn_analyze_log.configure(state="disabled")
                self.lbl_log_status.configure(text=f"Recording to: {result.split(os.sep)[-1]}")
                self.log(f"Telemetry recording STARTED")
            else:
                self.log(f"Recording failed: {result}")

    def _cmd_analyze_log(self):
        if not hasattr(self, '_last_log_path') or not self._last_log_path:
            self.log("ERROR: No log file available to analyze.")
            return
            
        if not os.path.exists(self._last_log_path):
            self.log("ERROR: Log file not found.")
            return
            
        self.log(f"Opening Log Analyzer for: {self._last_log_path}")
        LogAnalyzerWindow(self.root, self._last_log_path)

    def _open_fpv_window(self):
        """Open or focus the FPV window."""
        if self._fpv_window is None or not self._fpv_window.winfo_exists():
            self._fpv_window = FPVWindow(self.root, self.video_stream)
            self.lbl_fpv_status.configure(text="FPV: Window open")
            self.log("FPV window opened")
        else:
            self._fpv_window.lift()
            self._fpv_window.focus_force()
    
    def _set_geofence(self):
        """Set geofence radius from entry."""
        try:
            radius = int(self.geofence_entry.get())
            self.safety_monitor.geofence_radius = radius
            self.log(f"Geofence set to {radius}m")
        except ValueError:
            self.log("ERROR: Invalid geofence value")
    
    def _refresh_weather(self):
        """Manually refresh weather data."""
        # Update location from drone if connected
        if self.telemetry.connected:
            lat = self.telemetry.data.get("lat", 0.0)
            lon = self.telemetry.data.get("lon", 0.0)
            if lat != 0.0 and lon != 0.0:
                self.weather_service.set_location(lat, lon)
        
        self.log("Refreshing weather data...")
        
        def _fetch():
            success = self.weather_service.fetch_now()
            if not success:
                self.root.after(0, lambda: self.log("Weather fetch failed"))
        
        threading.Thread(target=_fetch, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════
    # UI UPDATES
    # ═══════════════════════════════════════════════════════════════════

    def update_ui(self):
        data = self.telemetry.data
        
        # Altitude
        self.lbl_alt.configure(text=f"{data['altitude']:.1f} m")
        
        # Speed
        self.lbl_speed.configure(text=f"{data['groundspeed']:.1f} m/s")
        
        # Climb rate with color
        climb = data['climb_rate']
        climb_color = self.colors["accent_emerald"] if climb > 0.3 else (self.colors["danger"] if climb < -0.3 else self.colors["text"])
        self.lbl_climb.configure(text=f"{climb:+.1f} m/s", text_color=climb_color)
        
        # Battery with warning
        bat = data['battery']
        if bat > 20:
            bat_color = self.colors["success"]
            self._battery_warning_level = 0
        elif bat > 10:
            bat_color = self.colors["warning"]
            self._battery_warning_level = 1
        else:
            bat_color = self.colors["danger"]
            self._battery_warning_level = 2
        self.lbl_bat.configure(text=f"{bat}%", text_color=bat_color)
        
        # Voltage / Current
        self.lbl_voltage.configure(text=f"{data['voltage']:.1f} V")
        self.lbl_current.configure(text=f"{data['current']:.1f} A")
        
        # GPS
        self.lbl_gps.configure(text=f"{data['satellites']} SAT")
        
        # GPS Fix type
        fix_map = {
            0: ("NO FIX", self.colors["danger"]),
            1: ("NO FIX", self.colors["danger"]),
            2: ("2D FIX", self.colors["warning"]),
            3: ("3D FIX", self.colors["success"]),
            4: ("DGPS", self.colors["accent_cyan"]),
            5: ("RTK FLOAT", self.colors["accent_cyan"]),
            6: ("RTK FIX", self.colors["accent_emerald"]),
        }
        fix_text, fix_color = fix_map.get(data['gps_fix'], ("UNKNOWN", self.colors["text_muted"]))
        self.lbl_gps_fix.configure(text=fix_text, text_color=fix_color)
        
        # Mode + Armed status
        mode = data['mode']
        is_armed = data['armed']
        mode_str = f"{mode} | {'ARMED' if is_armed else 'DISARMED'}"
        self.lbl_mode.configure(text=mode_str)
        self.lbl_mode.configure(text_color=self.colors["danger"] if is_armed else self.colors["success"])
        
        # Update heartbeat for safety monitor
        self.safety_monitor.heartbeat_received()

    def _periodic_update(self):
        # Redraw instruments and update text stats
        self.drone_visual.draw_drone()
        self.compass.draw()
        self.update_ui()
        
        # Altitude profile update
        self.altitude_profile.update_altitude()
        self.altitude_profile.draw()
        
        if self.telemetry.connected:
            self.map_widget.update_drone_position()
            self.map_widget.update_flight_trail()
            self._draw_led(True)
            
            # Update multi-drone markers on map
            if self.swarm and len(self.swarm.drones) > 1:
                self._update_swarm_markers()
        else:
            self._draw_led(False)
        
        # FPV status update
        if self.video_stream.running:
            det_count = len(self.video_stream.get_current_detections())
            tracking = "🎯" if self.video_stream.tracking_enabled else ""
            self.lbl_fpv_status.configure(
                text=f"FPV: {self.video_stream.fps:.0f} FPS | {det_count} obj {tracking}",
                text_color=self.colors["accent_emerald"]
            )
        
        self.root.after(50, self._periodic_update)

    def _update_swarm_markers(self):
        """Update multi-drone markers on the map."""
        if not self.swarm:
            return
        positions = self.swarm.get_all_positions()
        for pos in positions:
            drone = self.swarm.drones[pos["index"]]
            if pos["index"] != self.swarm.active_index:
                # Update or create marker for non-active drones
                if not drone.marker:
                    drone.marker = self.map_widget.map_view.set_marker(
                        pos["lat"], pos["lon"],
                        text=pos["name"],
                        marker_color_circle=pos["color"],
                        marker_color_outside="#111111"
                    )
                else:
                    drone.marker.set_position(pos["lat"], pos["lon"])

    def _swarm_info_update(self):
        """Periodic swarm panel info update (slower rate)."""
        if self.swarm and hasattr(self, 'swarm_panel'):
            try:
                self.swarm_panel.update_info()
            except Exception:
                pass
        self.root.after(5000, self._swarm_info_update)

    # ─── Connection LED ──────────────────────────────────────────────

    def _draw_led(self, connected):
        self.led_canvas.delete("all")
        color = self.colors["success"] if connected else self.colors["danger"]
        
        # Outer glow
        if connected and self._led_pulse:
            self.led_canvas.create_oval(1, 1, 17, 17, fill="", outline=color, width=1)
        
        # Inner dot
        self.led_canvas.create_oval(4, 4, 14, 14, fill=color, outline="")

    def _led_pulse_tick(self):
        self._led_pulse = not self._led_pulse
        self.root.after(800, self._led_pulse_tick)

    # ─── Battery Warning Flash ───────────────────────────────────────

    def _battery_flash_tick(self):
        if self._battery_warning_level >= 1:
            self._battery_flash = not self._battery_flash
            if self._battery_flash:
                flash_color = self.colors["danger"] if self._battery_warning_level == 2 else self.colors["warning"]
                self.lbl_bat.configure(text_color=flash_color)
            else:
                self.lbl_bat.configure(text_color=self.colors["bg_deep"])
        
        interval = 300 if self._battery_warning_level == 2 else 600
        self.root.after(interval, self._battery_flash_tick)

    # ─── Tutorial ────────────────────────────────────────────────────

    def _setup_tutorial(self):
        self.tutorial = TutorialGuide(self.root)
        
    def start_tutorial(self):
        self.tutorial.steps = []
        self.tutorial.add_step(self.btn_connect, "BAĞLANTI",
                               "Portu yazıp CONNECT ile drone'a bağlanın.")
        self.tutorial.add_step(self.top_bar, "TELEMETRİ",
                               "Üst barda tüm uçuş verileri: İrtifa, Hız, Batarya, GPS, Voltaj.")
        self.tutorial.add_step(self.drone_visual, "ATTITUDE INDICATOR",
                               "Drone'un pitch ve roll açılarını gösteren yapay ufuk.")
        self.tutorial.add_step(self.compass, "PUSULA",
                               "Drone'un baktığı yönü gösteren heading pusulası.")
        self.tutorial.add_step(self.btn_kill, "KILL SWITCH",
                               "ACİL DURUM butonu — drone'u anında kapatır!")
        self.tutorial.start()
