# Screen OCR LLM

A lightweight, cross-platform screen OCR tool that uses your favorite LLM model (via OpenRouter API) to extract text from any part of your screen.

## Features

- **Global Hotkey**: Activate OCR capture from anywhere with a simple keyboard shortcut
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Visual Selection**: Easy-to-use visual selection tool to capture exactly what you need
- **Clipboard Integration**: Extracted text is automatically copied to your clipboard
- **Multilingual Support**: Recognizes text in multiple languages
- **Smart Retries**: Built-in retry mechanism for reliable operation

## Requirements

- Python 3.8+
- OpenRouter API key (free tier available)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/cherjr/screen-ocr-llm.git
   cd screen-ocr-llm
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project directory with your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

## Usage

1. Run the application:
   ```
   python screen-ocr-llm.py
   ```

2. Press the hotkey (default: Ctrl+Win+E on Windows, Ctrl+Super+E on Linux, Ctrl+Cmd+E on macOS) to activate
3. Select a region of the screen containing text
4. The extracted text will be automatically copied to your clipboard

## Customization

You can customize the following parameters in the script:

- `MODEL`: The LLM model used for OCR (default: Google Gemini 2.0 Flash)
- `HOTKEY_CONFIG`: Keyboard shortcuts for different operating systems
- `MAX_RETRIES`: Number of retry attempts for API calls
- `INITIAL_DELAY`: Delay before sending API request

## Troubleshooting

### Windows Screenshot Alignment Issues

If you're experiencing issues where the screenshot doesn't align with your selection:

1. Make sure you're running the app with administrator privileges
2. Check your Windows display scaling settings (Settings > Display > Scale and layout)
3. If using multiple monitors, try the selection on your primary monitor

### API Key Issues

If you're getting authentication errors:
1. Ensure your OpenRouter API key is correct
2. Check that you have credit available in your OpenRouter account
3. Verify that your `.env` file is in the correct location

## Dependencies

- `mss`: Cross-platform screen capture
- `pyperclip`: Clipboard access
- `requests`: HTTP client for API access
- `pynput`: Keyboard monitoring for hotkeys
- `tkinter`: GUI for region selection
- `python-dotenv`: Environment variable management

## License

MIT

## Acknowledgments

- This tool uses the OpenRouter API 
- Inspired by the need for a lightweight, cross-platform OCR solution
