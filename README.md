# ProctorAI👁️
## 🔍 Overview
ProctorAI is a multimodal AI that watches your screen and calls you out if it sees you procrastinating. Proctor works by taking screenshots of your computer every few seconds (at a specified interval) and feeding them into a multimodal model, such as Claude-3.5-Sonnet, GPT-4o, or LLaVA-1.5. If ProctorAI determines that you are not focused, it will take control of your screen and yell at you with a personalized message. After making you pledge to stop procrastinating, ProctorAI will then give you 15 seconds to close the source of procrastination or will continue to bug you.

<p align="center">
  <img src="./assets/demo.gif" alt="Project demo" width="400">
</p>

***An intelligent system that knows what does and doesn't count as procrastination.*** Compared to traditional site blockers, ProctorAI is *intelligent* and capable of understanding nuanced workflows. *This makes a big difference*. Before every Proctor session, the user types out their session specification, where they explicitly tell Proctor what they're planning to work on, what behaviors are allowed during the session, and what behaviors are not allowed. Thus, Proctor can handle nuanced rules such as "I'm allowed to go on YouTube, but only to watch Karpathy's lecture on Makemore". No other productivity software can handle this level of flexibility.

<p align="center">
  <img src="./assets/slap.png" alt="Description of the image" width="350">
</p>
<p align="center" style="color: gray; font-size: 11px;">
  ProctorAI aims to be this woman, but available all the time, snarkier, and with full context of your work.
</p>

***It's alive!*** A big design goal with Proctor is that it should to *feel alive*. In my experience, I tend not to break the rules because I can intuitively *feel* the AI watching me--just like how test-takers are much less likely to cheat when they can *feel* the proctor of an exam watching them.

## 🚀 Setup and Installation
To start the GUI, just type ./run.sh. You might get some popups asking to allow terminal access to certain utilities, which you should enable.  
```
git clone https://github.com/jam3scampbell/ProctorAI
python venv -m focusenv
source focusenv/bin/activate
pip install -r requirements.txt
./run.sh
```

Depending on which models you want to use under-the-hood, you should define the following API keys as environment variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `ELEVEN_LABS_API_KEY`

To keep the running API price low, I recommend using `two_tier` mode, with a local model such as LLaVA as the router model. For this, you will need [Ollama](https://ollama.com) and to install the [llava](https://ollama.com/library/llava) model. Make sure Ollama is running in the background before starting ProctorAI.


## ⚙️ Options/Settings 
The following can all be toggled in the settings page or used as arguments to `main.py`:
| | |
|------------------|---------------------------------------------------------------------------------------------------------|
| `model_name`     | API name of the main model                                                                             |
| `tts`            | Enable Eleven Labs text-to-speech                                                           |
| `voice`          | Select the voice of Eleven Labs speaker                                                               |
| `cli_mode`       | Run without GUI                                                                                        |
| `delay_time`     | The amount of time between each screenshot                                                                   |
| `initial_delay`  | The amount of time to wait before Proctor starts watching your screen (useful for giving you time to open what you want to work on)                                                            |
| `countdown_time` | The amount of time Proctor gives to close the source of procrastination                                                            |
| `user_name`      | Enter your name to make the experience more personalized                                                       |
| `print_CoT`      | Print the model's chain-of-thought to the console                                                       |
| `two_tier`       | If activated, first sends image to router_model and only sends up to the main model if the router_model thinks the user is procrastinating. Useful for bringing down API costs. The router model is given a stricter prompt so that it leans towards flagging behavior it thinks is suspicious.                                          |
| `router_model`   | API name of the model to use as the router                                                                           |


## 🎯 Understanding This Repository

Right now, basically all functionality is contained in the following files:
- `main.py`: contains the main control loop that takes screenshots, calls the model, and initiates procrastination events
- `user_interface.py`: runs the GUI written in PyQT5
- `api_models.py`: houses a unified interface for calling different model families
- `procrastination_event.py`: contains methods for displaying the popup when the user is caught procrastinating as well as the timer telling the user to leave what they were doing
- `utils.py`: functions for taking screenshots, tts, etc
- `config_prompts.yaml`: all prompts used in the LLM scaffolded system

As the program runs, it'll create a `settings.json` file and a `screenshots` folder in the root directory. If TTS is enabled, it'll also write `yell_voice.mp3` to the `src` folder.

## 🌐 Roadmap and Future Improvements
This project is still very much under active development. Some features I'm hoping to add next:
- finetuning a LLaVA model specifically for the task/distribution
- scheduling sessions, have it start running when you open your computer
- make it extremely annoying to quit the program (at least until the user finishes their pre-defined session)
- logging, time-tracking, & summary statistics
- improve chat feature and give model greater awareness of state/context
- having a drafts folder for prompts so you don't have to re-type it out if you're doing the same task as you were the other day
- mute all other sounds on computer when the TTS plays (so it isn't drowned out by music)