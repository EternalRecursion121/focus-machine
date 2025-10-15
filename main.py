import math
from PIL import ImageGrab
from groq import Groq
import base64
import random
from pydantic import BaseModel
import asyncio
from playsound import playsound
import json
from dotenv import load_dotenv
import os

load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')


class ScreenshotResponse(BaseModel):
    isProductive: bool

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def read_txt(file_name):
    with open(file_name, 'r') as prev_msg:
        return prev_msg.read()

def write_txt(text):
    with open("prev_message.txt", 'w') as prev_msg:
        return prev_msg.write(text)

# none of the prompts here are really optimised, so feel free to edit them however you want

PROMPT = '''- You are tasked to help me with staying productive, focused, and excited while working! Analyse this screenshot and give me a little motivational message about what I'm up to.
- If it looks like I'm working (if you see code, technical documents, maths, writing, etc), then motivate me to continue with my persuit.
If it looks like I've become distracted (non-technical writing, social media, youtube, etc), then encourage me to realign my focus on what I know is important.
- I find some of the following ideas important for motivating myself: do not get stuck in the cycle of risk aversion, plan well and trust the process, you can and will build something beautifully radical. do not use all of them though, just if they are relevant.
- You should also personalise your response based on the following description of me. IMPORTANT: do not waffle on
about my personality, this should be just a small amount of supplimentary inference. Do not just repeat facts about
myself. You should prioritise
information about what you see on my screen.''' + read_txt("my_prompt.txt")

async def describe_screenshot():

    # get image base 64 encoded
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
    out = chat_completion.choices[0].message.content
    return out

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
                    {"type": "text", "text": ss_desc }
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

    # uses a weirdly effective "markov" context
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
                    {
                        "type": "text",
                        "text": ss_desc
                    },
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

def capture_screenshot():
    screenshot = ImageGrab.grab(None, True, True, None, None)
    screenshot.save("current-screen.png")

async def main():
    wait = 3
    write_txt("")
    while True:
        print("\n*** checking in... ***\n")
        capture_screenshot()
        ss_desc = await describe_screenshot()
        is_productive = await decide_productivity(ss_desc)
        await analyse_screenshot(ss_desc, is_productive)
        playsound("bloop.mp3")
        if is_productive:
            wait = random.randint(math.floor(wait * 1.2), math.ceil(wait * 1.5))
        else:
            wait = random.randint(math.floor(wait * 0.3), math.ceil(wait * 0.6))
        if wait < 2:
            wait = 2 # or we get trapped in a 1 min loop forever
        print(f"\nI'll check back in {wait} minutes.")
        await asyncio.sleep(wait * 60)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    tasks = [ loop.create_task(main())]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()