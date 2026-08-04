print("[SYS] Importing customtkinter...")
import customtkinter as ctk
import tkinter as tk
import time

print("[SYS] Importing TelemetryHandler...")
from core.telemetry_handler import TelemetryHandler

print("[SYS] Importing SwarmManager...")
from core.swarm_manager import SwarmManager

print("[SYS] Importing AppWindow...")
from ui.app_window import AppWindow

print("[SYS] All imports complete.")


# Splash screen removed to prevent tkinter blocking issues



def main():
    print("[SYS] Starting main...")
    # Set modern dark theme globally
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    print("[SYS] Creating root window...")
    root = ctk.CTk()
    root.title("Modern GCS V5.0")
    
    try:
        print("[SYS] Initializing SwarmManager...")
        # Initialize backend
        swarm = SwarmManager()
        
        # Add first drone automatically
        swarm.add_drone("Drone 1")
        telemetry = swarm.active_telemetry
        
        print("[SYS] Initializing AppWindow...")
        # Initialize frontend UI
        app = AppWindow(root, telemetry, swarm_manager=swarm)
        
        print("[SYS] Entering mainloop...")
        # Run the application
        root.mainloop()
    except Exception as e:
        import traceback
        print(f"[ERROR] Fatal error in main: {e}")
        traceback.print_exc()
    finally:
        print("[SYS] Cleaning up...")
        if 'swarm' in locals():
            swarm.stop_all()

if __name__ == "__main__":
    main()
