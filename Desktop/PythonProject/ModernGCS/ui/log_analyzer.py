import customtkinter as ctk
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

class LogAnalyzerWindow(ctk.CTkToplevel):
    def __init__(self, master, log_filepath):
        super().__init__(master)
        
        self.title("Flight Log Analysis")
        self.geometry("1200x800")
        self.minsize(1000, 600)
        
        # Bring to front
        self.lift()
        self.focus_force()
        self.grab_set()  # Make it modal-ish so they focus on it
        
        self.colors = {
            "bg": "#1a1a2e",
            "text": "#eeeeee",
            "accent_cyan": "#00e5ff",
            "accent_amber": "#f39c12",
            "accent_emerald": "#00c853",
            "danger": "#ff1744"
        }
        self.configure(fg_color=self.colors["bg"])
        
        # Configure Matplotlib dark style
        plt.style.use('dark_background')
        
        self.log_filepath = log_filepath
        
        self._build_ui()
        self._load_and_plot()

    def _build_ui(self):
        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=50)
        top_bar.pack(fill="x", padx=20, pady=10)
        
        title_label = ctk.CTkLabel(
            top_bar, 
            text="FLIGHT LOG DASHBOARD", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors["accent_cyan"]
        )
        title_label.pack(side="left")
        
        path_label = ctk.CTkLabel(
            top_bar, 
            text=f"Source: {self.log_filepath.split('/')[-1].split(chr(92))[-1]}", 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        path_label.pack(side="left", padx=20)
        
        close_btn = ctk.CTkButton(
            top_bar, text="CLOSE", width=100,
            command=self.destroy,
            fg_color="#333", hover_color="#555"
        )
        close_btn.pack(side="right")
        
        # Chart container
        self.chart_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _load_and_plot(self):
        times = []
        altitudes = []
        speeds = []
        batteries = []
        voltages = []
        rolls = []
        pitches = []
        lats = []
        lons = []
        alts_for_path = []  # Altitude values matched to GPS points
        
        try:
            with open(self.log_filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_time = None
                for row in reader:
                    if not row.get("timestamp"): continue
                    
                    try:
                        # Parse timestamp string, handle different formats or just fallback to index if fails
                        dt = datetime.fromisoformat(row["timestamp"])
                        if first_time is None:
                            first_time = dt
                        
                        rel_time = (dt - first_time).total_seconds()
                        times.append(rel_time)
                        
                        altitudes.append(float(row.get("altitude", 0)))
                        speeds.append(float(row.get("groundspeed", 0)))
                        batteries.append(float(row.get("battery", 0)))
                        voltages.append(float(row.get("voltage", 0)))
                        rolls.append(float(row.get("roll", 0)))
                        pitches.append(float(row.get("pitch", 0)))
                        
                        lat = float(row.get("lat", 0))
                        lon = float(row.get("lon", 0))
                        if lat != 0 and lon != 0:
                            lats.append(lat)
                            lons.append(lon)
                            alts_for_path.append(float(row.get("altitude", 0)))
                            
                    except Exception:
                        continue
        except Exception as e:
            ctk.CTkLabel(self.chart_frame, text=f"Error reading log: {e}", text_color="red").pack()
            return
            
        if not times:
            ctk.CTkLabel(self.chart_frame, text="Log file is empty or invalid.", text_color="orange").pack()
            return

        # Create Figure
        fig, axs = plt.subplots(2, 2, figsize=(10, 6))
        fig.patch.set_facecolor(self.colors["bg"])
        
        for ax in axs.flat:
            ax.set_facecolor(self.colors["bg"])
            ax.tick_params(colors=self.colors["text"])
            ax.xaxis.label.set_color(self.colors["text"])
            ax.yaxis.label.set_color(self.colors["text"])
            for spine in ax.spines.values():
                spine.set_color('#444')
        
        # 1. Energy (Battery & Voltage)
        ax1 = axs[0, 0]
        ax1.set_title("Energy Consumption", color=self.colors["accent_amber"], pad=10)
        ax1.plot(times, batteries, color=self.colors["accent_emerald"], label="Battery (%)", linewidth=2)
        ax1.set_ylabel("Battery %")
        ax1.set_xlabel("Time (s)")
        
        ax1_twin = ax1.twinx()
        ax1_twin.plot(times, voltages, color=self.colors["accent_amber"], label="Voltage (V)", linewidth=2, alpha=0.7)
        ax1_twin.set_ylabel("Voltage (V)")
        ax1_twin.tick_params(colors=self.colors["text"])
        ax1_twin.spines['right'].set_color('#444')
        
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines + lines2, labels + labels2, loc='lower left', frameon=False)

        # 2. Flight Profile (Altitude & Speed)
        ax2 = axs[0, 1]
        ax2.set_title("Flight Profile", color=self.colors["accent_cyan"], pad=10)
        ax2.plot(times, altitudes, color=self.colors["accent_cyan"], label="Alt (m)", linewidth=2)
        ax2.set_ylabel("Altitude (m)")
        ax2.set_xlabel("Time (s)")
        
        ax2_twin = ax2.twinx()
        ax2_twin.plot(times, speeds, color=self.colors["danger"], label="Speed (m/s)", linewidth=2, alpha=0.7)
        ax2_twin.set_ylabel("Ground Speed (m/s)")
        ax2_twin.tick_params(colors=self.colors["text"])
        ax2_twin.spines['right'].set_color('#444')
        
        lines, labels = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2_twin.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='upper left', frameon=False)
        
        # 3. Attitude (Roll & Pitch)
        ax3 = axs[1, 0]
        ax3.set_title("Attitude / Stability", color="#b39ddb", pad=10)
        ax3.plot(times, rolls, color="#64b5f6", label="Roll (deg)", linewidth=1.5, alpha=0.8)
        ax3.plot(times, pitches, color="#ffb74d", label="Pitch (deg)", linewidth=1.5, alpha=0.8)
        ax3.axhline(0, color='white', linewidth=0.5, linestyle='--')
        ax3.set_ylabel("Angle (degrees)")
        ax3.set_xlabel("Time (s)")
        ax3.legend(loc='upper right', frameon=False)
        
        # 4. 2D Flight Path
        ax4 = axs[1, 1]
        ax4.set_title("2D Mission Path", color="#a5d6a7", pad=10)
        if lats and lons:
            # Use scatter with color mapping to altitude (matched list sizes)
            scatter = ax4.scatter(lons, lats, c=alts_for_path, cmap='viridis', s=10, alpha=0.8)
            ax4.plot(lons, lats, color="gray", linewidth=0.5, alpha=0.5)
            cbar = fig.colorbar(scatter, ax=ax4, pad=0.02)
            cbar.set_label('Altitude (m)', color=self.colors["text"])
            cbar.ax.yaxis.set_tick_params(color=self.colors["text"])
            cbar.outline.set_edgecolor('#444')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=self.colors["text"])
        
        ax4.set_xlabel("Longitude")
        ax4.set_ylabel("Latitude")
        
        # Adjust layout
        fig.tight_layout()
        
        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
