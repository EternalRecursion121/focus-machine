import math
from PIL import ImageGrab
from groq import Groq
import base64
import random
from pydantic import BaseModel
import asyncio
import subprocess
import json
from dotenv import load_dotenv
import os
import tkinter as tk
from threading import Thread
from queue import Queue

load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Message queue for thread-safe communication
message_queue = Queue()


class NotificationManager:
    """Manages notifications on the main thread (required by macOS)"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window
        self.notification_window = None
        self._check_queue()
    
    def _check_queue(self):
        """Poll the message queue from the main thread"""
        try:
            while not message_queue.empty():
                message, is_productive = message_queue.get_nowait()
                self._show_notification(message, is_productive)
        except:
            pass
        self.root.after(100, self._check_queue)
    
    def _show_notification(self, message, is_productive, duration=12000):
        """Create and show a notification window"""
        print("[notification] Creating window...")
        
        # Close existing notification if any
        if self.notification_window:
            try:
                self.notification_window.destroy()
            except:
                pass
        
        win = tk.Toplevel(self.root)
        self.notification_window = win
        
        # Colors based on productivity
        bg_color = "#1a1a2e" if is_productive else "#2e1a1a"
        accent_color = "#4ade80" if is_productive else "#f87171"
        text_color = "#e2e8f0"
        
        # Configure window
        win.configure(bg=accent_color)
        win.overrideredirect(True)  # Remove window decorations
        
        # Main frame with accent border
        frame = tk.Frame(win, bg=accent_color, padx=3, pady=3)
        frame.pack(fill='both', expand=True)
        
        inner_frame = tk.Frame(frame, bg=bg_color, padx=18, pady=14)
        inner_frame.pack(fill='both', expand=True)
        
        # Status indicator
        status_text = "✓ On track" if is_productive else "⚡ Refocus"
        status_label = tk.Label(
            inner_frame,
            text=status_text,
            font=("Helvetica", 10, "bold"),
            fg=accent_color,
            bg=bg_color
        )
        status_label.pack(anchor='w')
        
        # Message text with word wrap - show full message
        msg_label = tk.Label(
            inner_frame,
            text=message,
            font=("Helvetica", 11),
            fg=text_color,
            bg=bg_color,
            wraplength=380,
            justify='left'
        )
        msg_label.pack(anchor='w', pady=(8, 0))
        
        # Set minimum size and update
        win.minsize(380, 100)
        win.update_idletasks()
        
        # Position: top-right corner (more visible, avoids dock)
        width = max(win.winfo_width(), 380)
        height = win.winfo_height()
        screen_width = win.winfo_screenwidth()
        x = screen_width - width - 20
        y = 40  # Below menu bar
        win.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make sure it's on top and visible
        win.attributes('-topmost', True)
        win.attributes('-alpha', 0.95)
        win.lift()
        win.focus_force()
        
        # Click to dismiss
        for widget in [win, frame, inner_frame, status_label, msg_label]:
            widget.bind('<Button-1>', lambda e: win.destroy())
        
        print(f"[notification] Window shown at {x},{y} ({width}x{height})")
        
        # Auto-dismiss with fade
        self._schedule_fade(win, duration)
    
    def _schedule_fade(self, win, delay):
        """Schedule fade out after delay"""
        win.after(delay, lambda: self._fade_out(win))
    
    def _fade_out(self, win):
        """Fade out animation"""
        try:
            alpha = win.attributes('-alpha')
            if alpha > 0.1:
                win.attributes('-alpha', alpha - 0.1)
                win.after(30, lambda: self._fade_out(win))
            else:
                win.destroy()
        except:
            pass
    
    def run(self):
        """Start the tkinter main loop"""
        self.root.mainloop()


def show_notification(message, is_productive=True):
    """Thread-safe way to queue a notification"""
    message_queue.put((message, is_productive))


class ScreenshotResponse(BaseModel):
    isProductive: bool


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def read_txt(file_name):
    with open(file_name, 'r') as prev_msg:
        return prev_msg.read()


def write_txt(text):
    with open("prev_message.txt", 'w') as prev_msg:
        return prev_msg.write(text)


PROMPT = '''- You are tasked to help me with staying productive, focused, and excited while working! Analyse this screenshot and give me a little motivational message about what I'm up to.
- If it looks like I'm working (if you see code, technical documents, maths, writing, etc), then motivate me to continue with my persuit.
If it looks like I've become distracted (non-technical writing, social media, youtube, etc), then encourage me to realign my focus on what I know is important.
- I find some of the following ideas important for motivating myself: do not get stuck in the cycle of risk aversion, plan well and trust the process, you can and will build something beautifully radical. do not use all of them though, just if they are relevant.
- You should also personalise your response based on the following description of me. IMPORTANT: do not waffle on
about my personality, this should be just a small amount of supplimentary inference. Do not just repeat facts about
myself. You should prioritise
information about what you see on my screen.''' + read_txt("my_prompt.txt")


async def describe_screenshot():
    base64_image = encode_image("current-screen.png")
    client = Groq(api_key=GROQ_API_KEY)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe the following screenshot, in very fine detail. IMPORTANT: "
                                             "INCLUDE A TRANSCRIPT OF AS MUCH RELEVANT TEXT ON THE SCREEN AS YOU CAN."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                        },
                    }
                ],
            }
        ],
        model="meta-llama/llama-4-scout-17b-16e-instruct",
    )
    return chat_completion.choices[0].message.content


async def decide_productivity(ss_desc):
    client = Groq(api_key=GROQ_API_KEY)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "you are a binary classifier. based on the following image description, "
                                             "decide whether i am being "
                                             "productive or not. define productive to mean avidly in-line with the "
                                             "following goals: rigorous technical understanding, organised "
                                             "admin work, making meaningful progress on tasks that are personally "
                                             "important to me. IF I AM PRODUCTIVE, RETURN TRUE. OTHERWISE, "
                                             "RETURN FALSE"},
                    {"type": "text", "text": ss_desc}
                ],
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "decide_productivity",
                "schema": ScreenshotResponse.model_json_schema()
            }
        },
        model="moonshotai/kimi-k2-instruct-0905",
    )
    out = ScreenshotResponse.model_validate(json.loads(chat_completion.choices[0].message.content))
    return out.model_dump()["isProductive"]


async def analyse_screenshot(ss_desc, is_productive):
    client = Groq(api_key=GROQ_API_KEY)

    try:
        prev = read_txt("prev_message.txt")
    except:
        prev = ""

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "text", "text": ss_desc},
                    {"type": "text",
                     "text": f"the previous message sent was as follows, do not repeat yourself, and use this as "
                             f"context: {prev}"},
                    {"type": "text",
                     "text": f"AN EXTERNAL SOURCE HAS DECIDED THAT THE STATEMENT \"i am productive\" is currently"
                             f" {is_productive}"}
                ],
            }
        ],
        model="llama-3.3-70b-versatile",
    )
    out = chat_completion.choices[0].message.content
    write_txt(out)
    print(out)
    show_notification(out, is_productive)


def capture_screenshot():
    screenshot = ImageGrab.grab(None, True, True, None, None)
    screenshot.save("current-screen.png")


async def worker_loop():
    """Background worker that does the actual work"""
    wait = 3
    write_txt("")
    while True:
        print("\n*** checking in... ***\n")
        capture_screenshot()
        ss_desc = await describe_screenshot()
        is_productive = await decide_productivity(ss_desc)
        await analyse_screenshot(ss_desc, is_productive)
        subprocess.run(["afplay", "bloop.mp3"], check=False)
        if is_productive:
            wait = random.randint(math.floor(wait * 1.2), math.ceil(wait * 1.5))
        else:
            wait = random.randint(math.floor(wait * 0.3), math.ceil(wait * 0.6))
        if wait < 2:
            wait = 2
        print(f"\nI'll check back in {wait} minutes.")
        await asyncio.sleep(wait * 60)


def run_async_worker():
    """Run the async worker in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(worker_loop())


if __name__ == '__main__':
    # Start async worker in background thread
    worker_thread = Thread(target=run_async_worker, daemon=True)
    worker_thread.start()
    
    # Run tkinter on main thread (required by macOS)
    manager = NotificationManager()
    manager.run()
