
import base64
import os
from openai import OpenAI
import tiktoken
from PIL import Image
import google.generativeai as genai
import anthropic
import subprocess
import json
from abc import ABC, abstractmethod
from functools import partial

anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
openai_api_key = os.environ.get('OPENAI_API_KEY')
gemini_api_key = os.environ.get('GEMINI_API_KEY')

class Conversation(ABC):
    @abstractmethod
    def __init__(self, user_prompt, system_prompt=None):
        pass

    @abstractmethod
    def add_message(self, message):
        pass        


class OpenAIConversation(Conversation):
    def __init__(self, user_prompt, system_prompt=None):
        self.messages = []
        if system_prompt is not None:
            self.messages.append({"role":"system","content":system_prompt})
        first_message = {"role":"user", "content":user_prompt}
        self.messages.append(first_message)

    def add_message(self, message):
        self.messages.append(message)

class GeminiConversation(Conversation):
    def __init__(self, user_prompt, system_prompt=None):
        self.messages = []
        if system_prompt is not None:
            self.messages.append({"role":"user","parts":system_prompt})
            self.messages.append({"role":"model","parts":"Understood."})
        first_message = {"role":"user", "parts":user_prompt}
        self.messages.append(first_message)
    
    def add_message(self, message):
        assert type(message["parts"]) == list, "Message must be in Gemini format"
        self.messages.append(message)

class AnthropicConversation(Conversation):
    def __init__(self, user_prompt, system_prompt=None):
        # Anthropic system prompt goes in API call
        self.messages = []
        first_message = {"role":"user", "content":user_prompt}
        self.messages.append(first_message)

    def add_message(self, message):
        self.messages.append(message)

class OLlamaConversation(Conversation):
    def __init__(self, user_prompt, system_prompt=None):
        self.messages = []
        if system_prompt is not None:
            self.messages.append({"role":"system","content":system_prompt})
        self.add_message(user_prompt)

    def add_message(self, message):
        self.messages.append(message)


class Model(ABC):
    def __init__(self, model_name):
        self.model_name = model_name

    @abstractmethod
    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        pass        
    
    def count_tokens(self, system_prompt, user_prompt, assistant_response, image_paths=None):
        pass

    def encode_image(self, image_path):
        # goes from image filepath to base64 encoding needed for APIs
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
        
    def resize_image(self, image_path, max_size_mb=5, quality=85):
        file_size = os.path.getsize(image_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size <= max_size_bytes:
            return image_path

        with Image.open(image_path) as img:
            width, height = img.size
            # Iteratively resize the image until it's under the size limit
            while file_size > max_size_bytes:
                width = int(width * 0.9)
                height = int(height * 0.9)
                                
                img.resize((width, height), Image.LANCZOS).save(image_path, quality=quality, optimize=True)
                
                file_size = os.path.getsize(image_path)
            
            return image_path


def create_model(model_name):
    if model_name == "gpt-4o":
        return GPTModel(model_name)
    elif model_name == "gemini-1.5-flash":
        return GeminiModel(model_name)
    elif model_name == "claude-3-5-sonnet-20240620":
        return ClaudeModel(model_name)
    elif model_name == "llava:34b":
        return OLlamaModel(model_name)
    elif model_name == "llava":
        return OLlamaModel(model_name)
    else:
        raise NotImplementedError("Model not supported.")


api_name_to_colloquial = {
    "gpt-4o": "GPT-4o",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet",
    "llava:34b": "LLAVA 34B",
    "llava": "LLAVA"
}


class GPTModel(Model):
    def __init__(self, model_name="gpt-4o"):
        self.client = OpenAI(api_key=openai_api_key)
        self.model_name = model_name
        self.convo = None

    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        if image_paths is not None:
            resize_with_max_size = partial(self.resize_image, max_size_mb=20) #GPT has upper limit of 20MB for images
            image_paths = list(map(resize_with_max_size, image_paths))
            encoded_images = list(map(self.encode_image, image_paths))
            user_prompt = [
                {"type": "text", "text": user_prompt},
                *map(lambda x: {"type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{x}"}}, encoded_images)
                ]
            
        self.convo = OpenAIConversation(user_prompt=user_prompt, system_prompt=system_prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.convo.messages,
        )
        response_string = response.choices[0].message.content
        return response_string
    
    def count_tokens(self, system_prompt, user_prompt, assistant_response, image_paths=None):
        encoder = tiktoken.encoding_for_model(self.model_name)
        
        image_token_count = 0
        if image_paths is not None:
            image_tiles = []
            for image_path in image_paths:
                width, height = self.get_image_dimensions(image_path)
                num_w_tiles = width // 512
                num_w_tiles = num_w_tiles + 1 if width % 512 != 0 else num_w_tiles
                num_h_tiles = height // 512
                num_h_tiles = num_h_tiles + 1 if height % 512 != 0 else num_h_tiles
                num_tiles = num_w_tiles*num_h_tiles
                if num_tiles > 4:
                    num_tiles = 4
                image_tiles.append(num_tiles)

            tokens_per_tile = 170

            image_token_count = sum([num_tiles * tokens_per_tile for num_tiles in image_tiles])

        system_tokens = encoder.encode(system_prompt)
        user_tokens = encoder.encode(user_prompt)
        assistant_tokens = encoder.encode(assistant_response)

        system_token_count = len(system_tokens)
        user_token_count = len(user_tokens)
        assistant_token_count = len(assistant_tokens)

        # Define pricing
        if self.model_name == "gpt-4o":
            price_per_million_input_tokens = 5.00
            price_per_million_output_tokens = 15.00
        else:
            raise NotImplementedError("Pricing not defined for this model.")

        total_input_tokens = system_token_count + user_token_count + image_token_count
        input_cost = (total_input_tokens / 1_000_000) * price_per_million_input_tokens
        output_cost = (assistant_token_count / 1_000_000) * price_per_million_output_tokens

        total_cost = input_cost + output_cost

        output_dict = {
            "system_tokens": system_token_count,
            "user_tokens": user_token_count,
            "image_tokens": image_token_count,
            "total_input_tokens": total_input_tokens,
            "input_cost": input_cost,
            "output_tokens": assistant_token_count,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

        return output_dict
    
    def get_image_dimensions(self, image_path):
        with Image.open(image_path) as img:
            width, height = img.size
            return width, height
        

class GeminiModel(Model):
    def __init__(self, model_name="gemini-1.5-pro"):
        genai.configure(api_key=gemini_api_key)
        self.model_name = model_name
        self.convo = None
        self.model = genai.GenerativeModel(self.model_name)
    
    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        if image_paths is not None:
            img_objects = list(map(Image.open, image_paths))
            user_prompt = [user_prompt, *img_objects]

        self.convo = GeminiConversation(user_prompt=user_prompt, system_prompt=system_prompt)
        response = self.model.generate_content(self.convo.messages)
        return response.text
    
    def count_tokens(self, system_prompt, user_prompt, assistant_response, image_paths=None):
        # still need to test if this is exact but should be in the ballpark
        system_token_count = self.model.count_tokens(system_prompt).total_tokens
        user_token_count = self.model.count_tokens(user_prompt).total_tokens
        image_token_count = 0
        if image_paths is not None:
            for image_path in image_paths:
                image_token_count = self.model.count_tokens(image_path).total_tokens

        total_input_tokens = system_token_count + user_token_count + image_token_count

        assistant_token_count = self.model.count_tokens(assistant_response).total_tokens

        # Define pricing
        # FLASH trains on API data!!!
        if self.model_name == "gemini-1.5-flash":
            price_per_million_input_tokens = 0
            price_per_million_output_tokens = 0
        elif self.model_name == "gemini-1.5-pro":
            #need to implement a system where you check account to see if threshold has been passed
            price_per_million_input_tokens = 0
            price_per_million_output_tokens = 0 
        else:
            raise NotImplementedError("Pricing not defined for this model.")

        # Gemini 1.5 Flash pricing free up to:
        # 15 RPM (requests per minute)
        # 1 million TPM (tokens per minute)
        # 1,500 RPD (requests per day)

        # Gemini 1.5 Pro pricing free up to:
        # 2 RPM (requests per minute)
        # 32,000 TPM (tokens per minute)
        # 50 RPD (requests per day)

        input_cost = (total_input_tokens / 1_000_000) * price_per_million_input_tokens
        output_cost = (assistant_token_count / 1_000_000) * price_per_million_output_tokens
        total_cost = input_cost + output_cost

        output_dict = {
            "system_tokens": system_token_count,
            "user_tokens": user_token_count,
            "image_tokens": image_token_count,
            "total_input_tokens": total_input_tokens,
            "input_cost": input_cost,
            "output_tokens": assistant_token_count,
            "output_cost": output_cost,
            "total_cost": total_cost
        }

        return output_dict


class ClaudeModel(Model):
    def __init__(self, model_name="claude-3-5-sonnet-20240620"):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model_name = model_name
        self.convo = None

    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        if image_paths is not None:
            resize_with_max_size = partial(self.resize_image, max_size_mb=5) #Claude has upper limit of 5MB for images
            image_paths = list(map(resize_with_max_size, image_paths))
            encoded_images = list(map(self.encode_image, image_paths))
            user_prompt = [
                {"type": "text", "text": user_prompt},
                *map(lambda x: {"type": "image", 
                                "source": {"type": "base64", "media_type": "image/png", "data": x}}, encoded_images)
                ]
        self.convo = AnthropicConversation(user_prompt=user_prompt)
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1000,
            temperature=0.0,
            system=system_prompt, 
            messages=self.convo.messages
        )
        response_string = response.content[0].text
        return response_string


class OLlamaModel(Model):
    def __init__(self, model_name="llava:34b"):
        self.model_name = model_name
        self.convo = None

    def call_model(self, user_prompt, system_prompt=None, image_paths=None):
        if image_paths is not None:
            encoded_images = list(map(self.encode_image, image_paths))
            user_prompt = {"role":"user", "content":user_prompt, "images":encoded_images}
        else:
            user_prompt = {"role":"user", "content":user_prompt}
        self.convo = OLlamaConversation(user_prompt=user_prompt, system_prompt=system_prompt)
        json_data = json.dumps({
            "model": self.model_name,
            "messages": self.convo.messages,
            "stream": False
        })
        result = subprocess.run(
            ["curl", "http://localhost:11434/api/chat", "-d", "@-"],
            input=json_data,
            capture_output=True,
            text=True
        )
        json_output = result.stdout.strip() 
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None  # Return None or handle the error as needed

        response_string = data["message"]["content"]
        assert response_string is not None, "Make sure OLlama is turned on!"
        return response_string