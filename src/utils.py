import cv2
from screeninfo import get_monitors
from PIL import ImageGrab
import os
from openai import OpenAI
import sounddevice as sd
import soundfile as sf
import requests
from pydub import AudioSegment

from dotenv import find_dotenv, load_dotenv

dotenv_file = find_dotenv()
load_dotenv(dotenv_file)

VOICE_FOLDER = os.getenv("VOICE_FOLDER", default=os.path.dirname(__file__))
SCREENSHOTS_FOLDER = os.getenv("SCREENSHOTS_FOLDER", default=os.path.dirname(__file__))

# Create the directories if they do not exist
os.makedirs(VOICE_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)


openai_api_key = os.environ.get('OPENAI_API_KEY')
xi_api_key = os.environ.get('ELEVEN_LABS_API_KEY')

def take_picture():
    cap = cv2.VideoCapture(0)
    ramp_frames = 30 
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return None

    for i in range(ramp_frames):
        ret, frame = cap.read()

    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    else:
        print("Error: Could not read frame.")
        return None

def take_screenshots():
    # returns a list of the filepaths of the monitor screenshots
    num_screens = len(get_monitors())
    if num_screens == 0:
        print("Error: No screens detected.")
        return None
    image_filepaths = []
    for i, screen in enumerate(get_monitors()):
        save_filepath = os.path.join(SCREENSHOTS_FOLDER, f"screen_{i}.png")
        screenshot = ImageGrab.grab(bbox=(0, 0, screen.width, screen.height))
        screenshot.save(save_filepath)
        image_filepaths.append(save_filepath)
    return image_filepaths

def get_text_to_speech(text, voice="Harry"):
    character_dict = {
        "Adam" : "pNInz6obpgDQGcFmaJgB",
        "Arnold" : "VR6AewLTigWG4xSOukaG",
        "Emily" : "LcfcDJNUP1GQjkzn1xUU",
        "Harry" : "SOYHLrjzK2X1ezoPC6cr",
        "Josh": "TxGEqnHWrfWFTfGW9XjX",
        "Patrick" : "ODq5zmih8GrVes37Dizd"
    }
    CHUNK_SIZE = 1024
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{character_dict[voice]}"
    headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": xi_api_key
    }
    data = {
    "text": text,
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
        }
    }
    response = requests.post(url, json=data, headers=headers)
    voice_path_mp3 = os.path.join(VOICE_FOLDER, "yell_voice.mp3")
    with open(voice_path_mp3, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

    voice_path_wav = os.path.join(VOICE_FOLDER, "yell_voice.wav")
    audio = AudioSegment.from_mp3(voice_path_mp3)
    audio.export(voice_path_wav, format="wav")
    return voice_path_wav

def play_text_to_speech(voice_file):
    data, samplerate = sf.read(voice_file)
    sd.play(data, samplerate)
    sd.wait()

def find_virtualenv(start_dir='.'):
    for root, dirs, files in os.walk(start_dir):
        # Проверяем наличие характерных признаков виртуального окружения
        if 'bin' in dirs and 'activate' in os.listdir(os.path.join(root, 'bin')):
            return root
        if 'Scripts' in dirs and 'activate' in os.listdir(os.path.join(root, 'Scripts')):
            return root
        if 'pyvenv.cfg' in files:
            return root
    return None

# def run_applescript(script_path):
#     subprocess.call(['osascript', script_path])

# def mute_applications():
#     run_applescript(os.path.dirname(__file__)+'/mute_apps.applescript')

# def unmute_applications():
#     run_applescript(os.path.dirname(__file__)+'/unmute_apps.applescript')

# if __name__ == "__main__":
#     print(find_virtualenv(start_dir=".."))