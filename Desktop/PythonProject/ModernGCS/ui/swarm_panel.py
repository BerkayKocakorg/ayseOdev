import customtkinter as ctk


class SwarmPanel(ctk.CTkFrame):
    """
    Multi-drone (Swarm) management UI panel.
    
    Features:
    - Drone list with connection status LED, name, battery, altitude
    - Add/Remove drone buttons
    - Click to select active drone (highlighted)
    - Connection dialog per drone
    - Batch commands: ARM ALL, DISARM ALL, RTL ALL
    """
    
    def __init__(self, master, swarm_manager, colors, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.swarm = swarm_manager
        self.colors = colors
        
        # Callback
        self.on_log = None
        
        self._build_ui()
        
        # Listen for changes
        self.swarm.on_drone_list_changed = self._refresh_list
        self.swarm.on_active_changed = lambda i, d: self._refresh_list()
    
    def _build_ui(self):
        # ── Add / Remove ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 4))
        
        ctk.CTkButton(
            btn_row, text="+ Add Drone", height=26,
            command=self._add_drone,
            fg_color=self.colors["accent_emerald"], text_color="black",
            hover_color="#00a844",
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        ctk.CTkButton(
            btn_row, text="- Remove", height=26,
            command=self._remove_active,
            fg_color=self.colors["bg_input"], text_color=self.colors["text"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True)
        
        # ── Drone List ──
        self.drone_list_frame = ctk.CTkScrollableFrame(
            self, fg_color=self.colors["bg_input"],
            height=120, corner_radius=8,
            scrollbar_button_color=self.colors["border"],
            scrollbar_button_hover_color=self.colors["text_muted"]
        )
        self.drone_list_frame.pack(fill="x", pady=4)
        
        # Placeholder
        self.placeholder = ctk.CTkLabel(
            self.drone_list_frame,
            text="Drone eklenmedi\n'+' ile yeni drone ekleyin",
            text_color=self.colors["text_dim"],
            font=ctk.CTkFont(size=9)
        )
        self.placeholder.pack(pady=10)
        
        # ── Batch Commands ──
        batch_frame = ctk.CTkFrame(self, fg_color="transparent")
        batch_frame.pack(fill="x", pady=(2, 0))
        
        row1 = ctk.CTkFrame(batch_frame, fg_color="transparent")
        row1.pack(fill="x", pady=1)
        
        ctk.CTkButton(
            row1, text="ARM ALL", height=24,
            command=self.swarm.arm_all,
            fg_color=self.colors["danger"], hover_color="#b71c1c",
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        ctk.CTkButton(
            row1, text="DISARM ALL", height=24,
            command=self.swarm.disarm_all,
            fg_color=self.colors["bg_input"], text_color=self.colors["text"],
            hover_color=self.colors["border"],
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        ctk.CTkButton(
            row1, text="RTL ALL", height=24,
            command=self.swarm.rtl_all,
            fg_color=self.colors["warning"], text_color="black",
            hover_color="#e69a00",
            font=ctk.CTkFont(size=9, weight="bold"), corner_radius=6
        ).pack(side="left", fill="x", expand=True)
    
    def _refresh_list(self):
        """Refresh the drone list display."""
        for widget in self.drone_list_frame.winfo_children():
            widget.destroy()
        
        drones = self.swarm.drones
        
        if not drones:
            self.placeholder = ctk.CTkLabel(
                self.drone_list_frame,
                text="Drone eklenmedi\n'+' ile yeni drone ekleyin",
                text_color=self.colors["text_dim"],
                font=ctk.CTkFont(size=9)
            )
            self.placeholder.pack(pady=10)
            return
        
        for i, drone in enumerate(drones):
            is_active = (i == self.swarm.active_index)
            bg = self.colors["bg_card"] if is_active else "transparent"
            
            row = ctk.CTkFrame(self.drone_list_frame, fg_color=bg, corner_radius=6, height=32)
            row.pack(fill="x", pady=1, padx=2)
            row.pack_propagate(False)
            
            # Click to select
            idx = i
            row.bind("<Button-1>", lambda e, idx=idx: self._select_drone(idx))
            
            # Color indicator dot
            dot = ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=14),
                              text_color=drone.color, width=20)
            dot.pack(side="left", padx=(4, 0))
            dot.bind("<Button-1>", lambda e, idx=idx: self._select_drone(idx))
            
            # Connection LED
            led_color = self.colors["accent_emerald"] if drone.telemetry.connected else self.colors["danger"]
            led = ctk.CTkLabel(row, text="⬤", font=ctk.CTkFont(size=8),
                              text_color=led_color, width=14)
            led.pack(side="left", padx=2)
            led.bind("<Button-1>", lambda e, idx=idx: self._select_drone(idx))
            
            # Name
            name_lbl = ctk.CTkLabel(row, text=drone.name,
                                    font=ctk.CTkFont(size=10, weight="bold" if is_active else "normal"),
                                    text_color=self.colors["text"])
            name_lbl.pack(side="left", padx=4)
            name_lbl.bind("<Button-1>", lambda e, idx=idx: self._select_drone(idx))
            
            # Battery + Alt (if connected)
            if drone.telemetry.connected:
                bat = drone.telemetry.data.get("battery", 0)
                alt = drone.telemetry.data.get("altitude", 0.0)
                info_text = f"{bat}% | {alt:.0f}m"
                ctk.CTkLabel(row, text=info_text,
                            font=ctk.CTkFont(family="Consolas", size=9),
                            text_color=self.colors["text_muted"]).pack(side="right", padx=4)
            
            # Connect/Disconnect button
            if drone.telemetry.connected:
                ctk.CTkButton(
                    row, text="DC", width=28, height=20,
                    command=lambda idx=idx: self._disconnect_drone(idx),
                    fg_color=self.colors["danger"], hover_color="#b71c1c",
                    font=ctk.CTkFont(size=8), corner_radius=4
                ).pack(side="right", padx=2)
            else:
                ctk.CTkButton(
                    row, text="CON", width=28, height=20,
                    command=lambda idx=idx: self._connect_dialog(idx),
                    fg_color=self.colors["accent_cyan"], text_color="black",
                    hover_color="#00b8d4",
                    font=ctk.CTkFont(size=8), corner_radius=4
                ).pack(side="right", padx=2)
    
    def _add_drone(self):
        index = self.swarm.add_drone()
        if index >= 0:
            self._log(f"Drone {index + 1} eklendi")
        else:
            self._log(f"Maksimum drone sayısına ulaşıldı ({self.swarm.max_drones})")
    
    def _remove_active(self):
        if self.swarm.active_index >= 0:
            name = self.swarm.active_drone.name if self.swarm.active_drone else "?"
            self.swarm.remove_drone(self.swarm.active_index)
            self._log(f"{name} kaldırıldı")
    
    def _select_drone(self, index):
        self.swarm.set_active(index)
        self._refresh_list()
        drone = self.swarm.drones[index]
        self._log(f"Aktif drone: {drone.name}")
    
    def _connect_dialog(self, index):
        """Show connection dialog for a specific drone."""
        drone = self.swarm.drones[index]
        
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title(f"Connect — {drone.name}")
        dialog.geometry("400x180")
        dialog.configure(fg_color=self.colors["bg_deep"] if "bg_deep" in self.colors else "#0a0a0f")
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"Connect {drone.name}",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=drone.color).pack(pady=10)
        
        entry = ctk.CTkEntry(dialog, width=300, height=32,
                             font=ctk.CTkFont(family="Consolas", size=12),
                             placeholder_text="tcp:127.0.0.1:5762")
        entry.insert(0, drone.connection_string or "tcp:127.0.0.1:5762")
        entry.pack(pady=5)
        
        def connect():
            conn_str = entry.get()
            success, msg = self.swarm.connect_drone(index, conn_str)
            if success:
                self._log(f"{drone.name} bağlandı: {conn_str}")
            else:
                self._log(f"{drone.name} bağlantı hatası: {msg}")
            dialog.destroy()
        
        ctk.CTkButton(dialog, text="CONNECT", height=32,
                     command=connect,
                     fg_color=self.colors["accent_cyan"], text_color="black",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=10)
    
    def _disconnect_drone(self, index):
        drone = self.swarm.drones[index]
        self.swarm.disconnect_drone(index)
        self._log(f"{drone.name} bağlantısı kesildi")
    
    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)
    
    def update_info(self):
        """Periodic update to refresh battery/altitude info."""
        self._refresh_list()
