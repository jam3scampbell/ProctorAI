import os
import json
import matplotlib.pyplot as plt
from api_models import create_model
import yaml
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


def annotate_screenshots(screenshots, model, config):
    """
    For each screenshot (a dict with filepath and timestamp), call the model
    using the analytics prompt and return a list of annotations.
    """
    annotations = []
    analytics_prompt = config.get("analytics_prompt", 
                                  "Analyze the screenshot and describe the user's activity briefly.")
    for shot in tqdm(screenshots):
        filepath = shot["filepath"]
        timestamp = shot["timestamp"]
        response = model.call_model(analytics_prompt, image_paths=[filepath])
        annotations.append({
            "timestamp": timestamp,
            "filepath": filepath,
            "annotation": response.strip()
        })
    return annotations

def annotate_single_shot(shot, model, analytics_prompt):
    """
    Annotates a single screenshot.
    """
    filepath = shot["filepath"]
    timestamp = shot["timestamp"]
    response = model.call_model(analytics_prompt, image_paths=[filepath])
    return {
        "timestamp": timestamp,
        "filepath": filepath,
        "annotation": response.strip()
    }

def annotate_screenshots_parallel(screenshots, model, config):
    """
    Annotates all screenshots in parallel.
    
    Parameters:
        screenshots (list): List of dicts, each with 'filepath' and 'timestamp'
        model: The model instance used for annotation.
        config (dict): Configuration dictionary containing the 'analytics_prompt'.
    
    Returns:
        List of annotation dictionaries.
    """
    analytics_prompt = config.get(
        "analytics_prompt",
        "Analyze the screenshot and briefly describe what activity is being performed on the screen."
    )
    annotations = []
    with ThreadPoolExecutor() as executor:
        future_to_shot = {
            executor.submit(annotate_single_shot, shot, model, analytics_prompt): shot
            for shot in screenshots
        }
        for future in as_completed(future_to_shot):
            try:
                annotation = future.result()
                annotations.append(annotation)
                print(annotation)
            except Exception as exc:
                shot = future_to_shot[future]
                print(f"Screenshot {shot['filepath']} generated an exception: {exc}")
    return annotations

def save_annotations(annotations, log_file="session_log.json"):
    # Convert any datetime objects in annotations to strings
    for ann in annotations:
        if isinstance(ann["timestamp"], datetime):
            ann["timestamp"] = ann["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "w") as f:
        json.dump(annotations, f, indent=4)
    print(f"Annotations saved to {log_file}")

def load_annotations(log_file="session_log.json"):
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            return json.load(f)
    else:
        print("No annotation log found.")
        return []

def generate_visual_summary(annotations):
    """
    Generates a pie chart that shows the distribution of activity categories.
    A simple keyword search maps the annotation text to a category.
    """
    categories = {
        "coding": 0,
        "browsing": 0,
        "social media": 0,
        "other": 0
    }
    for ann in annotations:
        text = ann["annotation"].lower()
        if "code" in text or "terminal" in text or "ide" in text:
            categories["coding"] += 1
        elif "browser" in text or "internet" in text or "email" in text:
            categories["browsing"] += 1
        elif "twitter" in text or "facebook" in text or "instagram" in text:
            categories["social media"] += 1
        else:
            categories["other"] += 1

    labels = list(categories.keys())
    sizes = list(categories.values())

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    plt.title("Session Activity Summary")
    plt.show()
    
def load_screenshots(screenshots_dir):
    """
    Loads all screenshots from the given directory.
    Assumes screenshots are named in the format: screen_{screen}_{timestamp}.png
    """
    screenshots = []
    for filename in os.listdir(screenshots_dir):
        if filename.endswith(".png"):
            filepath = os.path.join(screenshots_dir, filename)
            # Try to extract timestamp from filename
            try:
                # Expecting something like "screen_1_20250219_154530.png"
                timestamp_str = filename.rsplit("_", 1)[-1].replace(".png", "")
                # Optionally convert string to datetime object
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except Exception as e:
                # Fallback: use the file's modification time
                timestamp = datetime.fromtimestamp(os.path.getmtime(filepath))
            screenshots.append({"filepath": filepath, "timestamp": timestamp})
    return screenshots

if __name__ == "__main__":
    # Load config prompts
    with open(os.path.join(os.path.dirname(__file__), "config_prompts.yaml"), "r") as f:
        config = yaml.safe_load(f)
    
    # Instantiate a model for analytics (you might choose a cheaper one)
    model = create_model("gpt-4o-mini")
    
    # For demonstration, load screenshots from a log or define them here.
    # In practice, you would pass the list returned by take_screenshots().
    screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
    screenshots = load_screenshots(screenshots_dir)        
    
    if screenshots:
        annotations = annotate_screenshots_parallel(screenshots, model, config)
        save_annotations(annotations)
        generate_visual_summary(annotations)
    else:
        print("No screenshots to analyze.")
