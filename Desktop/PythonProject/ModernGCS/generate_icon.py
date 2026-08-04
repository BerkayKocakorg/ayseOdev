from PIL import Image, ImageDraw
import os

def create_icon():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Modern Amber/Orange color to match HUD
    color = (243, 156, 18, 255)  
    outline = (255, 255, 255, 200) # White outlines for rotors
    
    # Draw body (sleeker, arrow-like shape pointing up)
    draw.polygon([(32, 16), (24, 40), (32, 48), (40, 40)], fill=color)
    
    # Draw arms
    draw.line([26, 24, 12, 16], fill=color, width=3)
    draw.line([38, 24, 52, 16], fill=color, width=3)
    draw.line([28, 44, 14, 52], fill=color, width=3)
    draw.line([36, 44, 50, 52], fill=color, width=3)
    
    # Draw rotors (translucent dark with bright outline)
    rotor_fill = (20, 20, 20, 150)
    draw.ellipse([4, 8, 20, 24], fill=rotor_fill, outline=outline, width=2)
    draw.ellipse([44, 8, 60, 24], fill=rotor_fill, outline=outline, width=2)
    draw.ellipse([6, 44, 22, 60], fill=rotor_fill, outline=outline, width=2)
    draw.ellipse([42, 44, 58, 60], fill=rotor_fill, outline=outline, width=2)
    
    # Save the file
    path = os.path.join(os.path.dirname(__file__), 'drone_icon.png')
    img.save(path)
    print("New sleek drone icon saved to", path)

if __name__ == "__main__":
    create_icon()
