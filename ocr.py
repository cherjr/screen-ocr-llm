import mss
import pyperclip
import requests
import base64
from pynput import keyboard
import threading
import os
import tkinter as tk
from tkinter import Canvas
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API details from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-exp:free"  # Check OpenRouter for exact model name

# Shortcut constant (default: Ctrl+Win+E)
HOTKEY_COMBINATION = '<ctrl>+<cmd>+e'  # Ctrl + Windows key + E

# Flag to prevent multiple captures at once
is_processing = False
start_x, start_y, end_x, end_y = None, None, None, None
rect = None

def capture_and_extract(region):
    global is_processing
    if is_processing:
        return
    is_processing = True
    
    try:
        # Create a new mss instance within the thread
        with mss.mss() as sct:
            screenshot = sct.grab(region)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output="screenshot.png")
        
        # Encode image as base64
        with open("screenshot.png", "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode("utf-8")
        
        # Prepare OpenRouter API request
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Perform OCR on this image and output only the extracted text, nothing else."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]
                }
            ]
        }
        
        # Send request to OpenRouter
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        extracted_text = response.json()["choices"][0]["message"]["content"]
        
        # Copy to clipboard
        pyperclip.copy(extracted_text)
        print("Text extracted and copied to clipboard:", extracted_text)
        
        # Clean up
        os.remove("screenshot.png")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        is_processing = False

def start_selection():
    global start_x, start_y, end_x, end_y, rect
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)
    root.attributes('-topmost', True)
    canvas = Canvas(root, cursor="cross")
    canvas.pack(fill="both", expand=True)
    
    def on_mouse_down(event):
        global start_x, start_y, rect
        start_x, start_y = event.x, event.y
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_mouse_move(event):
        global end_x, end_y, rect
        if rect:
            end_x, end_y = event.x, event.y
            canvas.coords(rect, start_x, start_y, end_x, end_y)

    def on_mouse_up(event):
        global end_x, end_y
        end_x, end_y = event.x, event.y
        root.destroy()
        left = min(start_x, end_x)
        top = min(start_y, end_y)
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
        region = {"top": top, "left": left, "width": width, "height": height}
        threading.Thread(target=capture_and_extract, args=(region,), daemon=True).start()

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()

def on_hotkey():
    threading.Thread(target=start_selection, daemon=True).start()

# Set up the hotkey using the constant
hotkey = keyboard.HotKey(keyboard.HotKey.parse(HOTKEY_COMBINATION), on_hotkey)

def start_listener():
    with keyboard.Listener(
        on_press=lambda k: hotkey.press(listener.canonical(k)),
        on_release=lambda k: hotkey.release(listener.canonical(k))
    ) as listener:
        listener.join()

print("Running in background. Press Ctrl+Shift+S to select a region. Press Ctrl+C to exit.")
threading.Thread(target=start_listener, daemon=True).start()

try:
    while True:
        pass
except KeyboardInterrupt:
    print("Exiting...")