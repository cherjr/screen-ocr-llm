import sys
import os
import base64
import threading
import time
import platform
import tkinter as tk
from tkinter import Canvas
from datetime import datetime

# --- Early Import Error Handling ---
try:
    import mss
    import pyperclip
    import requests
    from pynput import keyboard
    from pynput.keyboard import Controller, Key
    from dotenv import load_dotenv
    import warnings
except ImportError as e:
    try:
        err_log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
        err_log_path = os.path.join(err_log_dir, "screen_ocr_IMPORT_ERROR.log")
        with open(err_log_path, "a", encoding='utf-8') as ef:
            ef.write(f"--- Import Error Log Start: {datetime.now()} ---\n")
            ef.write(f"Fatal Import Error: {e}\n")
            ef.write(f"sys.path: {sys.path}\n")
            ef.write("--- Log End ---\n")
    except Exception as log_e:
        print(f"CRITICAL: Import error ({e}) AND failed to write import error log ({log_e})", file=sys.__stderr__)
    sys.exit(f"Fatal Import Error: {e}")

# --- Determine Base Directory ---
base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)

# --- Load Environment Variables ---
def log_early(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

try:
    log_early("Attempting to load .env file...")
    dotenv_path = os.path.join(base_dir, '.env')
    log_early(f"Expected .env path: {dotenv_path}")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        log_early(".env file loaded successfully.")
    else:
        log_early("WARNING: .env file not found at expected location. Attempting default search.")
        load_dotenv()
        log_early("Attempted default load_dotenv().")
except Exception as e:
    log_early(f"ERROR loading .env file: {e}")

# --- Get Logging Configuration ---
enable_logging_str = os.getenv("ENABLE_FILE_LOGGING", "False")
file_logging_enabled = enable_logging_str.lower() == 'true'
log_file = None

# --- Conditional File Logging Setup ---
if file_logging_enabled:
    log_file_path = os.path.join(base_dir, "screen_ocr_debug.log")
    try:
        log_file = open(log_file_path, "a", encoding='utf-8', buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        print(f"\n--- Log Start (File Logging Enabled): {datetime.now()} ---", flush=True)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] File logging is ENABLED. Output directed to: {log_file_path}", flush=True)
    except Exception as e:
        print(f"FATAL: Failed to redirect stdout/stderr to log file: {e}", file=sys.__stderr__, flush=True)
        file_logging_enabled = False
        log_file = None
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
else:
    log_early("File logging is DISABLED.")

# --- Define the main log function ---
def log(message):
    """Log messages with timestamps to the configured output."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", flush=True)
    except Exception as e:
        print(f"[{datetime.now()}] Logging function error: {e}", file=sys.__stderr__, flush=True)

# --- Initial Configuration Logging ---
log("Initial imports successful.")
warnings.filterwarnings("ignore")
log("Warnings filter applied.")

# --- Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.getenv("MODEL")
MAX_RETRIES = 3
INITIAL_DELAY = 1.0

log(f"API Key loaded: {'Yes' if OPENROUTER_API_KEY else 'NO - CRITICAL'}")
log(f"Model loaded: {MODEL if MODEL else 'NO - CRITICAL'}")

# Platform-specific configurations
SYSTEM = platform.system()
HOTKEY_CONFIG = {
    "Windows": ("<ctrl>+<cmd>+e", "Ctrl+Win+E"),
    "Linux": ("<ctrl>+<super>+e", "Ctrl+Super+E"),
    "Darwin": ("<ctrl>+<cmd>+e", "Ctrl+Cmd+E")
}
DEFAULT_HOTKEY, DEFAULT_HOTKEY_DISPLAY = ("<ctrl>+<cmd>+e", "Ctrl+Win+E")
HOTKEY, HOTKEY_DISPLAY = HOTKEY_CONFIG.get(SYSTEM, (DEFAULT_HOTKEY, DEFAULT_HOTKEY_DISPLAY))
log(f"System detected: {SYSTEM}")
log(f"Using Hotkey: {HOTKEY} (Display: {HOTKEY_DISPLAY})")

# --- Global state management ---
is_processing = False
selection_coords = {"start_x": None, "start_y": None, "end_x": None, "end_y": None}
selection_rect = None
try:
    keyboard_controller = Controller()
    log("Pynput Controller initialized.")
except Exception as e:
    log(f"CRITICAL ERROR initializing pynput Controller: {e}")
    sys.exit(f"Failed to initialize keyboard controller: {e}")

# --- Helper Functions ---

def release_modifiers():
    """Release modifier keys to prevent stuck states"""
    log("Attempting to release modifier keys...")
    # Removed Key.win_l and Key.win_r as they don't exist in pynput.Key
    mod_keys = [
        Key.ctrl, Key.cmd, Key.shift, Key.alt,
        Key.ctrl_l, Key.ctrl_r, Key.alt_l, Key.alt_r,
        Key.cmd_l, Key.cmd_r # Key.cmd covers the Win/Super/Cmd key itself
    ]
    for key in mod_keys:
        try:
            keyboard_controller.release(key)
        except Exception:
            # Ignore errors, just try to release each one
            pass
    log("Modifier key release attempted.")

def validate_image(image_path):
    """Ensure the screenshot is valid before processing"""
    log(f"Validating image: {image_path}")
    if not os.path.exists(image_path):
        log("Validation Error: Screenshot file not found.")
        raise FileNotFoundError("Screenshot file not created")
    size = os.path.getsize(image_path)
    log(f"Image size: {size} bytes")
    if size < 100:
        log("Validation Warning: Screenshot file is very small.")
    log("Image validation check done.")

def capture_and_extract(region, monitor_info=None):
    """Capture screenshot and extract text using OpenRouter API"""
    global is_processing
    if is_processing:
        log("Warning: Capture triggered but already processing. Skipping.")
        return
    is_processing = True
    log("Starting capture_and_extract process.")
    screenshot_path = os.path.join(base_dir, "screenshot.png")

    try:
        if not OPENROUTER_API_KEY or not MODEL:
            log("CRITICAL ERROR: API Key or Model is missing. Cannot proceed.")
            return

        for attempt in range(MAX_RETRIES):
            log(f"Attempt {attempt + 1} of {MAX_RETRIES}")
            try:
                # --- Screenshot Capture ---
                with mss.mss() as sct:
                    capture_region = region.copy()
                    mon_details = "N/A"
                    if monitor_info and SYSTEM == "Windows":
                        mon_top = monitor_info.get("top", 0)
                        mon_left = monitor_info.get("left", 0)
                        capture_region["top"] += mon_top
                        capture_region["left"] += mon_left
                        mon_details = f"Adjusted for Monitor Top:{mon_top}, Left:{mon_left}"

                    log(f"Raw region: {region}, {mon_details}, Final Capture region: {capture_region}")
                    screenshot = sct.grab(capture_region)
                    log(f"Screenshot captured (Size: {screenshot.size})")
                    mss.tools.to_png(screenshot.rgb, screenshot.size, output=screenshot_path)
                    log(f"Screenshot saved to {screenshot_path}")

                # --- Image Validation & Encoding ---
                validate_image(screenshot_path)
                with open(screenshot_path, "rb") as img_file:
                    log("Encoding image to base64...")
                    image_data = base64.b64encode(img_file.read()).decode("utf-8")
                    log(f"Base64 encoding complete.")

                # --- API Request ---
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/cherjr/screen-ocr-llm", # Adjust if needed
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
                                "- Preserve line breaks accurately from the visual layout.\n"
                                "If no text found, return 'NO_TEXT_FOUND'"
                            )},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                        ]
                    }],
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
                log(f"API Payload prepared for model {MODEL}.")

                delay = INITIAL_DELAY * (1.5 ** attempt)
                log(f"Waiting {delay:.2f} seconds before API request...")
                time.sleep(delay)

                log(f"Sending API request (Attempt {attempt + 1})...")
                response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=45)
                log(f"API Response Status Code: {response.status_code}")
                response.raise_for_status()

                # --- Process Response ---
                response_data = response.json()
                if not response_data.get("choices") or not response_data["choices"][0].get("message") or "content" not in response_data["choices"][0]["message"]:
                    log("API Error: Unexpected response structure.")
                    raise ValueError("Invalid API response structure")

                extracted_text = response_data["choices"][0]["message"]["content"].strip()
                log(f"API Raw Extracted Text Received (Length: {len(extracted_text)})")

                if not extracted_text or extracted_text == "NO_TEXT_FOUND":
                    log("No text detected or returned by API.")
                    return

                extracted_text = extracted_text.replace("</image>", "").strip()

                log("Attempting to copy text to clipboard...")
                pyperclip.copy(extracted_text)
                log(f"Text copied to clipboard ({len(extracted_text)} chars). Start: '{extracted_text[:50].replace(os.linesep, '//')}'")
                return # Success

            except requests.exceptions.RequestException as e:
                log(f"API Request Error (Attempt {attempt + 1}): {str(e)}")
                if attempt == MAX_RETRIES - 1: raise
            except Exception as e:
                log(f"Error during processing (Attempt {attempt + 1}): {type(e).__name__} - {str(e)}")
                if file_logging_enabled:
                    import traceback
                    log(f"Traceback: {traceback.format_exc()}")
                if attempt == MAX_RETRIES - 1: raise

    except Exception as e:
        log(f"CRITICAL error in capture_and_extract: {type(e).__name__} - {str(e)}")
        if file_logging_enabled:
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
    finally:
        log("Executing finally block in capture_and_extract.")
        if os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
                log(f"Temporary screenshot file removed: {screenshot_path}")
            except Exception as e:
                log(f"Cleanup error: Failed to remove screenshot file: {str(e)}")
        is_processing = False
        log("is_processing flag set to False.")
        release_modifiers()

def get_monitor_info():
    """Get information about the primary monitor"""
    log("Getting monitor info...")
    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            log(f"Found {len(monitors)} monitor entries.")
            if len(monitors) > 1:
                primary_monitor = monitors[1]
                log(f"Selected primary monitor (index 1): {primary_monitor}")
                return primary_monitor
            elif len(monitors) == 1:
                 log("Warning: Only one monitor entry found (likely composite view). Using index 0.")
                 return monitors[0]
            else:
                log("Error: No monitors detected by mss.")
                return None
    except Exception as e:
        log(f"Error getting monitor info: {e}")
        return None

def start_selection():
    """Create a screen overlay for region selection"""
    log("Starting region selection process...")
    global selection_rect

    monitor_info = get_monitor_info() if SYSTEM == "Windows" else None

    try:
        root = tk.Tk()
        log("Tk root window created.")
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.3)
        root.attributes("-topmost", True)
        root.config(cursor="cross")
        log("Tk root window configured.")

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        log(f"Screen dimensions detected by Tk: {screen_width}x{screen_height}")

        canvas = Canvas(root, bg='black', highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        log("Tk Canvas created and packed.")

        instruction_id = None
        try:
            instruction_id = canvas.create_text(
                screen_width / 2, screen_height / 2,
                text="Drag to select region  •  ESC to cancel",
                fill="white", font=("Arial", 20, "bold"), anchor="center"
            )
            log("Instruction text created on canvas.")
        except tk.TclError as e:
             log(f"Warning: Could not create instruction text: {e}")

        def on_mouse_down(event):
            global selection_rect
            if selection_rect:
                try: canvas.delete(selection_rect)
                except tk.TclError: pass
            selection_coords.update(start_x=event.x, start_y=event.y, end_x=event.x, end_y=event.y)
            selection_rect = canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline="#FF0000", width=2
            )
            log(f"Selection started (mouse down) at ({event.x}, {event.y}). Rect ID: {selection_rect}")
            if instruction_id:
                try: canvas.itemconfig(instruction_id, state='hidden')
                except tk.TclError: pass

        def on_mouse_move(event):
            if selection_rect:
                selection_coords.update(end_x=event.x, end_y=event.y)
                try:
                    canvas.coords(selection_rect,
                                  selection_coords["start_x"], selection_coords["start_y"],
                                  event.x, event.y)
                except tk.TclError: pass

        def on_mouse_up(event):
            log(f"Selection ended (mouse up) at ({event.x}, {event.y})")
            x1, y1 = selection_coords["start_x"], selection_coords["start_y"]
            x2, y2 = selection_coords["end_x"], selection_coords["end_y"]

            if x1 is None or y1 is None:
                 log("Error: Mouse up event without valid start coordinates. Cancelling.")
                 root.destroy()
                 release_modifiers()
                 return

            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                final_region = {
                    "top": min(y1, y2), "left": min(x1, x2),
                    "width": abs(x2 - x1), "height": abs(y2 - y1)
                }
                log(f"Valid selection region determined: {final_region}")
                root.destroy()
                log("Selection window destroyed.")
                time.sleep(0.1)
                log("Starting capture thread...")
                threading.Thread(target=capture_and_extract, args=(final_region, monitor_info), daemon=True).start()
            else:
                log("Selection too small or invalid, cancelling.")
                root.destroy()
                log("Selection window destroyed (selection too small).")
                release_modifiers()

        def on_escape(event=None):
            log("Escape key pressed, cancelling selection.")
            root.destroy()
            log("Selection window destroyed (Escape pressed).")
            release_modifiers()

        # Bind events
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        root.bind("<Escape>", on_escape)
        log("Event bindings set for mouse and Escape key.")

        root.after(50, lambda: root.focus_force())
        log("Focus forced to Tk window.")
        root.mainloop()
        log("Tk mainloop finished.")

    except Exception as e:
        log(f"CRITICAL error during Tkinter setup or mainloop: {e}")
        if file_logging_enabled:
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
    finally:
        log("Executing finally block in start_selection.")
        release_modifiers()

# --- Hotkey Activation ---
def on_activate():
    global is_processing
    log("Hotkey activated!")
    if is_processing:
        log("Processing already in progress. Ignoring hotkey press.")
        return

    log("Not currently processing. Proceeding with selection.")
    release_modifiers() # Call the corrected function
    time.sleep(0.05)
    log("Starting selection thread...")
    threading.Thread(target=start_selection, daemon=True).start()

# --- Main Execution Block ---
if __name__ == "__main__":
    log(f"--- Script Start ---")
    log(f"Screen OCR Tool initializing (PID: {os.getpid()})")
    log(f"Base directory: {base_dir}")
    log(f"File Logging Enabled: {file_logging_enabled}")

    listener = None

    try:
        log(f"Setting up global hotkey listener for: {HOTKEY_DISPLAY} ({HOTKEY})")
        listener = keyboard.GlobalHotKeys({HOTKEY: on_activate})
        log("GlobalHotKeys object created.")
        listener.start()
        log("Listener thread started successfully.")
        log(f"--- Ready and Listening for {HOTKEY_DISPLAY} ---")
        listener.join()

    except Exception as e:
        # Log the exception that caused listener.join() to exit
        log(f"CRITICAL ERROR in main loop (likely from listener thread): {e}")
        if file_logging_enabled:
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
    finally:
        log("--- Initiating Shutdown ---")
        if listener and listener.is_alive():
            log("Stopping listener thread...")
            try:
                listener.stop()
                log("Listener stop() called.")
            except Exception as e:
                 log(f"Error stopping listener: {e}")
        else:
            log("Listener was not running or already stopped.")

        if file_logging_enabled and log_file and not log_file.closed:
            log("Closing log file.")
            print(f"--- Log End: {datetime.now()} ---", flush=True)
            log_file.close()
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print("Log file closed. Standard streams restored.")
        else:
            log("Log file was not opened or already closed.")
            print("Shutdown complete.")

        log("--- Application Exit ---")