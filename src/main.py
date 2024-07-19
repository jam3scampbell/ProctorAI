import time
import os
import yaml
import threading
import concurrent.futures
import argparse
from dotenv import find_dotenv, load_dotenv

from api_models import *
from procrastination_event import ProcrastinationEvent
from utils import take_screenshots, get_text_to_speech, play_text_to_speech

dotenv_file = find_dotenv()
load_dotenv(dotenv_file)

SCREENSHOTS_FOLDER = os.getenv("SCREENSHOTS_FOLDER", default=os.path.dirname(__file__))

with open(os.path.dirname(__file__) + "/config_prompts.yaml", "r") as file:
    config = yaml.safe_load(file)


def model_pipeline(
    model: Model,
    judge_model,
    user_prompt: str,
    total_cost: float,
    image_filepaths: list,
    print_CoT=False,
):
    # goes from model to determination of "productive" or "procrastinating"
    response = model.call_model(
        user_prompt, system_prompt=config["system_prompt"], image_paths=image_filepaths
    )
    if print_CoT:
        print(response)
    pricing_info_dict = model.count_tokens(
        config["system_prompt"],
        config["user_prompt"],
        response,
        image_paths=image_filepaths,
    )
    if pricing_info_dict is not None:
        total_cost += pricing_info_dict["total_cost"]
    determination = judge_model.call_model(
        config["user_prompt_judge"] + response,
        system_prompt=config["system_prompt_judge"],
    )
    pricing_info_dict = model.count_tokens(
        config["system_prompt_judge"],
        config["user_prompt_judge"] + response,
        determination,
    )
    if pricing_info_dict is not None:
        total_cost += pricing_info_dict["total_cost"]
    return determination, total_cost


def make_api_call(model, role, user_prompt, system_prompt=None, image_paths=None):
    return {
        "result": model.call_model(user_prompt, system_prompt, image_paths),
        "role": role,
    }


def parallel_api_calls(model, api_params):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                make_api_call,
                model,
                params["role"],
                params["user_prompt"],
                params.get("system_prompt"),
                params.get("image_paths"),
            )
            for params in api_params
        ]
        results = [
            future.result() for future in concurrent.futures.as_completed(futures)
        ]
    return results


def procrastination_sequence(
    user_spec, user_name, proctor_model, tts, voice, countdown_time, image_filepaths
):
    api_params = [
        {
            "role": "heckler",
            "user_prompt": config["user_prompt_heckler"].format(
                user_spec=user_spec, user_name=user_name
            ),
            "system_prompt": config["system_prompt_heckler"].format(
                user_name=user_name
            ),
            "image_paths": image_filepaths,
        },
        {
            "role": "pledge",
            "user_prompt": config["user_prompt_pledge"].format(
                user_spec=user_spec, user_name=user_name
            ),
            "system_prompt": config["system_prompt_pledge"],
            "image_paths": image_filepaths,
        },
        {
            "role": "countdown",
            "user_prompt": config["user_prompt_countdown"].format(user_spec=user_spec),
            "system_prompt": config["system_prompt_countdown"],
            "image_paths": image_filepaths,
        },
    ]

    api_results = parallel_api_calls(proctor_model, api_params)

    for api_result in api_results:
        if api_result["role"] == "heckler":
            heckler_message = api_result["result"]
        if api_result["role"] == "pledge":
            pledge_message = api_result["result"]
        if api_result["role"] == "countdown":
            countdown_message = api_result["result"]

    if tts:
        voice_file = get_text_to_speech(heckler_message, voice)
        tts_thread = threading.Thread(target=play_text_to_speech, args=(voice_file,))
        tts_thread.start()

    procrastination_event = ProcrastinationEvent()
    procrastination_event.show_popup(heckler_message, pledge_message)
    procrastination_event.play_countdown(
        countdown_time,
        brief_message=f"You have {countdown_time} seconds to close "
        + countdown_message.strip(),
    )


def control_sequence(
    call_when_procrastinate: callable,
    call_when_procrast_args,
    model,
    judge_model,
    total_cost,
    user_spec,
    print_CoT,
    user_prompt_label,
):
    image_filepaths = take_screenshots()
    determination, total_cost = model_pipeline(
        model,
        judge_model,
        config[user_prompt_label].format(user_spec=user_spec),
        total_cost,
        image_filepaths,
        print_CoT=print_CoT,
    )
    print(f"{api_name_to_colloquial[model.model_name]} Determination: ", determination)

    if "productive" in determination.lower():
        pass
    elif "procrastinating" in determination.lower():
        if call_when_procrastinate.__name__ == "procrastination_sequence":
            call_when_procrast_args.append(image_filepaths)
        call_when_procrastinate(*call_when_procrast_args)
    else:
        print(
            f"{api_name_to_colloquial[model.model_name]} Determination: ERROR, LLM Output: ",
            determination,
        )


def main(
    model_name="claude-3-5-sonnet-20240620",
    tts=False,
    cli_mode=False,
    voice="Patrick",
    delay_time=0,
    initial_delay=0,
    countdown_time=15,
    user_name="Procrastinator",
    print_CoT=False,
    two_tier=False,
    router_model_name="llava",
):
    os.makedirs(
        SCREENSHOTS_FOLDER, exist_ok=True
    )

    if cli_mode:
        user_spec = input("What do you plan to work on?\n")
    else:
        user_spec = input()

    proctor_model = create_model(model_name)

    if two_tier:
        router_model = create_model(router_model_name)

    total_cost = 0

    time.sleep(initial_delay)

    while True:
        procrast_seq_args = [
            user_spec,
            user_name,
            proctor_model,
            tts,
            voice,
            countdown_time,
        ]
        control_args = [
            procrastination_sequence,
            procrast_seq_args,
            proctor_model,
            proctor_model,
            total_cost,
            user_spec,
            print_CoT,
            "user_prompt",
        ]
        if two_tier:
            # essentially, this code runs control sequence with the router_model and then re-runs it again with proctor_model if the router_model determines the user is procrastinating
            control_sequence(
                control_sequence,
                control_args,
                router_model,
                proctor_model,
                total_cost,
                user_spec,
                print_CoT,
                "user_prompt_strict",
            )
        elif not two_tier:
            control_sequence(*control_args)

        time.sleep(delay_time)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model_name",
        help="Set model name",
        default="claude-3-5-sonnet-20240620",
        type=str,
    )
    parser.add_argument("--tts", help="Enable heckling", action="store_true")
    parser.add_argument("--voice", help="Set voice", default="Patrick", type=str)
    parser.add_argument("--cli_mode", help="Enable CLI mode", action="store_true")
    parser.add_argument("--delay_time", help="Set delay time", default=0, type=int)
    parser.add_argument(
        "--initial_delay",
        help="Initial delay so user can open relevant apps",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--countdown_time", help="Set countdown time", default=15, type=int
    )
    parser.add_argument(
        "--user_name", help="Set user name", default="Procrastinator", type=str
    )
    parser.add_argument(
        "--print_CoT", help="Show model's chain of thought", action="store_true"
    )
    parser.add_argument(
        "--two_tier", help="Enable two-tier model pipeline", action="store_true"
    )
    parser.add_argument(
        "--router_model", help="Set router model", default="llava", type=str
    )

    args = parser.parse_args()
    main(
        model_name=args.model_name,
        tts=args.tts,
        cli_mode=args.cli_mode,
        voice=args.voice,
        delay_time=args.delay_time,
        initial_delay=args.initial_delay,
        countdown_time=args.countdown_time,
        user_name=args.user_name,
        print_CoT=args.print_CoT,
        two_tier=args.two_tier,
        router_model_name=args.router_model,
    )
