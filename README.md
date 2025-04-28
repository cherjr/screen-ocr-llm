# Screen OCR LLM Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A cross-platform Python tool that allows you to capture a selected region of your screen using a hotkey, send it to a Large Language Model (LLM) via the OpenRouter API for Optical Character Recognition (OCR), and automatically copy the extracted text to your clipboard.

## Features

*   **Hotkey Activation:** Trigger screen capture with a configurable global hotkey (Default: `Ctrl+Win+E` on Windows, `Ctrl+Super+E` on Linux, `Ctrl+Cmd+E` on macOS).
*   **Region Selection:** An overlay allows you to precisely select the screen area for OCR.
*   **LLM-Powered OCR:** Leverages powerful Vision Language Models via OpenRouter for potentially higher accuracy OCR compared to traditional methods.
*   **OpenRouter Integration:** Easily switch between different compatible models supported by OpenRouter.
*   **Clipboard Output:** Extracted text is automatically copied to the clipboard for immediate use.
*   **Configurable Logging:** Enable/disable detailed file logging via the `.env` file for debugging.
*   **Cross-Platform Attempt:** Includes default hotkey configurations for Windows, macOS, and Linux.
*   **(Optional) Build Executable:** Can be packaged into a standalone executable using PyInstaller.


## Requirements

*   **Python:** 3.8+ recommended.
*   **pip:** Python package installer.
*   **OpenRouter API Key:** You need an account and API key from [OpenRouter.ai](https://openrouter.ai/).

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/cherjr/screen-ocr-llm.git
    cd screen-ocr-llm
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Optional: It's recommended to use a Python virtual environment)*
    ```bash
    # Example using venv
    python -m venv venv
    # Activate (Windows Powershell)
    .\venv\Scripts\Activate.ps1
    # Activate (Linux/macOS Bash)
    # source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Create `.env` file:**
    Copy the example file:
    ```bash
    # Windows
    copy .env.example .env
    # Linux/macOS
    # cp .env.example .env
    ```
    Now, **edit the `.env` file** with your actual credentials and preferences.

## Configuration

Edit the `.env` file to configure the tool:

*   **`OPENROUTER_API_KEY`**: (Required) Your API key obtained from [OpenRouter.ai](https://openrouter.ai/). **Keep this secret!**
*   **`MODEL`**: (Required) The identifier for the OpenRouter model you want to use. Must be a model compatible with image input (Vision Language Model). You can find available models on the OpenRouter site. Example: `qwen/qwen2.5-vl-72b-instruct:free`
*   **`ENABLE_FILE_LOGGING`**: (Optional) Set to `True` to enable detailed logging to `screen_ocr_debug.log` in the application's directory. Set to `False` or omit to disable logging. Useful for debugging.

## Usage

1.  **Run the script:**
    ```bash
    python screen-ocr-llm.py
    ```
    The script will run in the background and listen for the hotkey. You'll see log messages in the console (or the log file if enabled).

2.  **Press the Hotkey:**
    *   Windows: `Ctrl + Win + E`
    *   Linux: `Ctrl + Super + E` (Super is often the Windows key)
    *   macOS: `Ctrl + Command + E`

3.  **Select Region:**
    Your screen will dim slightly. Click and drag your mouse to draw a rectangle around the area you want to OCR. Release the mouse button.

4.  **Get Text:**
    The script will capture the selected region, send it to the configured OpenRouter model, and copy the extracted text to your clipboard. You can then paste the text anywhere.

5.  **Stop the script:** Press `Ctrl + C` in the terminal where the script is running.

## Building an Executable (Optional)

You can create a standalone `.exe` file for Windows using PyInstaller.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Build the executable:**
    Run this command from the script's directory:
    ```bash
    pyinstaller --onefile --windowed --name ScreenOCRTool screen-ocr-llm.py
    ```

3.  **Prepare for Distribution:**
    *   The executable will be in the `dist` folder (`dist/ScreenOCRTool.exe`).
    *   **Crucially, copy your `.env` file into the `dist` folder** next to the executable. The `.exe` needs this file to run correctly.

4.  **Run:** Double-click `ScreenOCRTool.exe`. It will run silently in the background.

## Running on Startup (Optional)

To make the tool run automatically when you log in:

*   **Windows:**
    *   Create a shortcut to the `.exe` (located in its permanent folder alongside `.env`).
    *   Press `Win + R`, type `shell:startup`, press Enter.
    *   Paste the shortcut into the Startup folder that opens.
    *   *Alternatively:* Use Task Scheduler for more control (configure it to run the `.exe` at logon, making sure to set the "Start in" directory to the folder containing the `.exe` and `.env`).
*   **macOS:** Use `launchd` (create a `.plist` file).
*   **Linux:** Use your desktop environment's autostart settings or systemd user services.

## Troubleshooting

*   **Hotkey Not Working:**
    *   Ensure the script is running in the background.
    *   Check if another application is using the same hotkey combination. Try changing the `HOTKEY_CONFIG` in the script temporarily to test.
    *   Some systems/permissions might interfere with global hotkeys.
*   **Errors / No Text Copied:**
    *   Check your internet connection.
    *   Verify your `OPENROUTER_API_KEY` is correct in the `.env` file.
    *   Ensure the specified `MODEL` in `.env` is valid and supports image input on OpenRouter.
    *   Check your OpenRouter account for any API limits or billing issues.
    *   If built into an `.exe`, ensure the `.env` file is in the *same directory* as the `.exe`.
*   **Debugging:** Set `ENABLE_FILE_LOGGING=True` in your `.env` file and check `screen_ocr_debug.log` (created in the same directory as the script/exe) for detailed error messages after trying to use the tool.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This tool relies on several fantastic libraries:

*   [mss](https://github.com/BoboTiG/python-mss): For screen capture.
*   [pynput](https://github.com/moses-palmer/pynput): For global hotkey listening and control.
*   [requests](https://github.com/psf/requests): For making API calls.
*   [python-dotenv](https://github.com/theskumar/python-dotenv): For loading environment variables.
*   [pyperclip](https://github.com/asweigart/pyperclip): For cross-platform clipboard operations.
*   Tkinter (built-in): For the region selection GUI.