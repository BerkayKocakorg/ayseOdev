import tkinter as tk

class TutorialGuide:
    """
    Creates an overlay on the main window to guide first-time users.
    Highlights specific widgets and shows instructional text.
    
    V4.0: Updated styling to match new dark theme.
    """
    def __init__(self, root):
        self.root = root
        self.overlay = None
        self.steps = []
        self.current_step = 0
        
    def add_step(self, widget, title, description):
        """
        Adds a step to the tutorial.
        :param widget: The tkinter widget to highlight
        :param title: The title of the step
        :param description: What this widget does
        """
        self.steps.append({"widget": widget, "title": title, "desc": description})
        
    def start(self):
        if not self.steps:
            return
            
        self.current_step = 0
        self._create_overlay()
        self._show_step()
        
    def _create_overlay(self):
        if self.overlay:
            self.overlay.destroy()
            
        # Create a borderless Toplevel for the overlay
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-alpha", 0.88)
        self.overlay.configure(bg="#0a0a0f")
        
        # We want the overlay to cover the whole main window
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        
        # Make a canvas to draw highlight boxes
        self.canvas = tk.Canvas(self.overlay, bg="#0a0a0f", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Bind click to go to next step
        self.canvas.bind("<Button-1>", self._next_step)
        
    def _show_step(self):
        self.canvas.delete("all")
        
        if self.current_step >= len(self.steps):
            self.overlay.destroy()
            self.overlay = None
            return
            
        step = self.steps[self.current_step]
        widget = step["widget"]
        title = step["title"]
        desc = step["desc"]
        
        # Step counter
        total = len(self.steps)
        step_text = f"Step {self.current_step + 1} / {total}"
        
        # Get widget position relative to root
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        
        wx = widget.winfo_rootx() - root_x
        wy = widget.winfo_rooty() - root_y
        ww = widget.winfo_width()
        wh = widget.winfo_height()
        
        # Draw a highlight box around the widget
        self.canvas.create_rectangle(wx - 5, wy - 5, wx + ww + 5, wy + wh + 5, 
                                     outline="#00e5ff", width=3, dash=(6, 3))
        
        # Glow effect (subtle)
        self.canvas.create_rectangle(wx - 8, wy - 8, wx + ww + 8, wy + wh + 8, 
                                     outline="#00e5ff", width=1)
                                     
        # Determine text placement
        tx = wx + ww / 2
        ty = wy + wh + 25
        
        # If text would go off screen, place above
        canvas_h = self.canvas.winfo_height() or self.root.winfo_height()
        if ty + 100 > canvas_h:
            ty = wy - 100
        
        # Draw text background
        box_w = 180
        box_h = 50
        self.canvas.create_rectangle(
            tx - box_w, ty, tx + box_w, ty + box_h + 40,
            fill="#12121a", outline="#00e5ff", width=2
        )
        
        # Step counter (top right of box)
        self.canvas.create_text(
            tx + box_w - 10, ty + 12,
            text=step_text, fill="#666680",
            font=("Segoe UI", 8), anchor="e"
        )
        
        # Title
        self.canvas.create_text(
            tx, ty + 22,
            text=title, fill="#ffffff",
            font=("Segoe UI", 14, "bold")
        )
        
        # Description
        self.canvas.create_text(
            tx, ty + 52,
            text=desc, fill="#cccccc",
            font=("Segoe UI", 10),
            justify="center", width=340
        )
        
        # Continue instruction
        self.canvas.create_text(
            tx, ty + box_h + 55,
            text="▶ Devam etmek için tıklayın",
            fill="#666680",
            font=("Segoe UI", 9)
        )

    def _next_step(self, event):
        self.current_step += 1
        self._show_step()
