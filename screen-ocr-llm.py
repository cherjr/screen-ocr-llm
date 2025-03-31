import mss
import pyperclip
import requests
import base64
import threading
import os
import tkinter as tk
from tkinter import Canvas
from pynput import keyboard
from pynput.keyboard import Controller, Key
from dotenv import load_dotenv
import platform
import time
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-exp:free"
MAX_RETRIES = 3
INITIAL_DELAY = 1.0

# Platform-specific configurations
SYSTEM = platform.system()
HOTKEY_CONFIG = {
    "Windows": ("<ctrl>+<cmd>+e", "Ctrl+Win+E"),
    "Linux": ("<ctrl>+<super>+e", "Ctrl+Super+E"),
    "Darwin": ("<ctrl>+<cmd>+e", "Ctrl+Cmd+E")
}
HOTKEY, HOTKEY_DISPLAY = HOTKEY_CONFIG.get(SYSTEM, ("<ctrl>+<cmd>+e", "Ctrl+Win+E"))

# Global state management
is_processing = False
selection_coords = {"start_x": None, "start_y": None, "end_x": None, "end_y": None}
keyboard_controller = Controller()
selection_rect = None

def log(message):
    """Log messages with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def release_modifiers():
    """Release modifier keys to prevent stuck states"""
    for key in [Key.ctrl, Key.cmd, Key.shift, Key.alt]:
        try:
            keyboard_controller.release(key)
        except Exception as e:
            log(f"Error releasing {key}: {str(e)}")

def validate_image(image_path):
    """Ensure the screenshot is valid before processing"""
    if not os.path.exists(image_path):
        raise FileNotFoundError("Screenshot file not created")
    if os.path.getsize(image_path) < 1024:
        raise ValueError("Screenshot file is too small")

def capture_and_extract(region, monitor_info=None):
    """Capture screenshot and extract text using OpenRouter API"""
    global is_processing
    is_processing = True
    
    try:
        for attempt in range(MAX_RETRIES):
            try:
                with mss.mss() as sct:
                    # If monitor info is provided, adjust region based on monitor position
                    capture_region = region.copy()
                    if monitor_info:
                        # Adjust region coordinates to be relative to the specific monitor
                        if SYSTEM == "Windows":
                            capture_region["top"] += monitor_info["top"]
                            capture_region["left"] += monitor_info["left"]
                    
                    log(f"Capturing region: {capture_region}")
                    screenshot = sct.grab(capture_region)
                    mss.tools.to_png(screenshot.rgb, screenshot.size, output="screenshot.png")
                
                validate_image("screenshot.png")
                
                with open("screenshot.png", "rb") as img_file:
                    log("Encoding image to base64...")
                    image_data = base64.b64encode(img_file.read()).decode("utf-8")
                
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/cherjr/screen-ocr-llm",
                    "X-Title": "Screen OCR Tool"
                }
                
                payload = {
                    "model": MODEL,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": (
                                "Perform OCR on this image. Return ONLY the raw extracted text with:\n"
                                "- No formatting\n"
                                "- No XML/HTML tags\n"
                                "- No markdown\n"
                                "- No explanations\n"
                                "If no text found, return 'NO_TEXT_FOUND'"
                            )},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                        ]
                    }],
                    "temperature": 0.1
                }
                
                time.sleep(INITIAL_DELAY)
                log(f"Sending API request (Attempt {attempt + 1})...")
                response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                
                extracted_text = response.json()["choices"][0]["message"]["content"].strip()
                
                if not extracted_text or "</image>" in extracted_text:
                    raise ValueError("Invalid API response structure")
                
                if extracted_text == "NO_TEXT_FOUND":
                    log("No text detected in image")
                    return
                
                pyperclip.copy(extracted_text)
                log(f"Text copied to clipboard ({len(extracted_text)} characters)")
                log("Clipboard Content:\n--------------------\n" + extracted_text + "\n--------------------")
                return
            
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                log(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                time.sleep(1.5)
    
    except Exception as e:
        log(f"Critical error: {str(e)}")
    finally:
        if os.path.exists("screenshot.png"):
            try:
                os.remove("screenshot.png")
            except Exception as e:
                log(f"Cleanup error: {str(e)}")
        is_processing = False
        release_modifiers()  # Ensure modifiers are released after processing

def get_monitor_info():
    """Get information about the current monitor setup"""
    with mss.mss() as sct:
        # Log monitor information for debugging
        for i, monitor in enumerate(sct.monitors):
            log(f"Monitor {i}: {monitor}")
        
        # Return the primary monitor (usually index 1, as 0 is all monitors combined)
        # For Windows, we'll use this to adjust coordinates
        return sct.monitors[1] if len(sct.monitors) > 1 else None

def start_selection():
    """Create a screen overlay for region selection"""
    global selection_rect
    
    # Get monitor information
    monitor_info = get_monitor_info() if SYSTEM == "Windows" else None
    
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    root.config(cursor="cross")
    
    # Store screen dimensions for later use
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    log(f"Screen dimensions: {screen_width}x{screen_height}")
    
    canvas = Canvas(root)
    canvas.pack(fill="both", expand=True)
    
    canvas.create_text(
        screen_width // 2,
        screen_height // 2,
        text="Drag to select region • ESC to cancel",
        fill="white",
        font=("Arial", 24, "bold"),
        anchor="center"
    )
    
    def on_mouse_down(event):
        global selection_rect
        selection_coords.update(start_x=event.x, start_y=event.y)
        selection_rect = [
            canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#ffffff", width=6, dash=(5,5)),
            canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#ff0000", width=4, dash=(5,5))
        ]
        log(f"Selection started at ({event.x}, {event.y})")
    
    def on_mouse_move(event):
        if selection_rect:
            for rect in selection_rect:
                canvas.coords(rect, selection_coords["start_x"], selection_coords["start_y"], event.x, event.y)
    
    def on_mouse_up(event):
        x1, y1 = selection_coords["start_x"], selection_coords["start_y"]
        x2, y2 = event.x, event.y
        log(f"Selection ended at ({event.x}, {event.y})")
        
        if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
            region = {
                "top": min(y1, y2),
                "left": min(x1, x2),
                "width": abs(x2 - x1),
                "height": abs(y2 - y1)
            }
            log(f"Raw selection region: {region}")
            root.destroy()
            # Add a small delay before capture starts to ensure the window is fully closed
            time.sleep(0.3)
            threading.Thread(target=capture_and_extract, args=(region, monitor_info), daemon=True).start()
        else:
            root.destroy()
    
    def on_escape(event=None):
        release_modifiers()
        root.destroy()
    
    # Debug info display
    debug_text = canvas.create_text(
        10, 10, 
        text=f"System: {SYSTEM}, Monitor Info: {monitor_info}", 
        fill="white", 
        font=("Arial", 10),
        anchor="nw"
    )
    
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.bind("<Escape>", on_escape)
    
    root.after(100, root.focus_force)
    root.mainloop()
    release_modifiers()  # Additional cleanup after window closes

def on_activate():
    """Hotkey press handler"""
    if not is_processing:
        log("Hotkey pressed. Starting region selection...")
        release_modifiers()  # Release modifiers before starting
        time.sleep(0.1)  # Allow time for key releases
        threading.Thread(target=start_selection, daemon=True).start()

if __name__ == "__main__":
    log(f"Screen OCR Tool (Active with {HOTKEY_DISPLAY})")
    log("Press Ctrl+C to exit")
    
    listener = keyboard.GlobalHotKeys({HOTKEY: on_activate})
    listener.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Exiting...")
        listener.stop()