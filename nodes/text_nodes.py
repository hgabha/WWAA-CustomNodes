import math, string, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
import torch.nn.functional as F
import os, folder_paths
import random
from pathlib import Path
from typing import List, Dict, Any
import comfy.model_management as model_management
import json

debug = False

class WWAA_LineCount:
    DESCRIPTION = "Reads a multi-line string and counts how many lines exist while ignoring blank lines. Useful for determining the number of prompts or entries in text data."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "string_text": ("STRING", {
                    "multiline": True,
                    "default":"String goes here\nSecond line."
                }),


            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("Line Count",)

    FUNCTION = "executeLineCount"
    CATEGORY = "🪠️ WWAA"

    def executeLineCount(self, string_text):
        #count lines
        string_text = string_text.strip() #strip extra line feeds
        string_text = string_text.strip()
        string_text = re.sub(r'((\n){2,})', '\n', string_text)
        lines = string_text.split('\n')
        print(lines if debug else "")
        num_lines = len(lines)
        print(num_lines if debug else "")
        return (num_lines,)

class WWAA_BuildString:
    DESCRIPTION = "Combines a string with defined prefix and suffix text. Originally designed to build LoRA strings for inclusion into prompts, for example creating '<lora:Name:1>' where prefix is '<lora:' and suffix is ':1>'. Useful for any string concatenation needs."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pre_text": ("STRING", {
                    "multiline": False,
                    "default":"Pre-text"
                }),
                "input_text": ("STRING", {
                    "forceInput": True,
                }),
                "post_text": ("STRING", {
                    "multiline": False,
                    "default":"Post-text"
                }),

            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Joined String",)

    FUNCTION = "executeBuildString"
    CATEGORY = "🪠️ WWAA"

    def executeBuildString(self, pre_text, input_text, post_text):
        #Concatenate and build string
        joinString = pre_text + input_text + post_text
        print(joinString if debug else "")
        return (joinString,)

class WWAA_PromptWriter:
    DESCRIPTION = "Writes prompts to text files using image filenames, making it ready for LoRA training. Feed it prompts related to images and it will create corresponding text files with the same base name as the image. Supports optional prefix text and subdirectory organization."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "image_filename": ("STRING", {}),
                "output_path": ("STRING", {"default": ""}),
                "overwrite": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "prefix_text": ("STRING", {"default": ""}),
                "subdirectory": ("STRING", {}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("log_output",)
    FUNCTION = "write_text_file"
    OUTPUT_NODE = True
    CATEGORY = "🪠️ WWAA"

    def write_text_file(self, text, image_filename, output_path, overwrite, prefix_text="", subdirectory=""):
        # Initialize log string
        log_output = ""

        # Log input parameters
        log_output += f"Input Parameters:\n"
        log_output += f"- Image Filename: {image_filename}\n"
        log_output += f"- Output Path: {output_path}\n"
        log_output += f"- Overwrite: {overwrite}\n"
        log_output += f"- Prefix Text: {bool(prefix_text)}\n"
        log_output += f"- Subdirectory: {subdirectory or 'None'}\n\n"

        # Remove file extension from image filename
        base_filename = os.path.splitext(image_filename)[0]
        output_filename = f"{base_filename}.txt"
        log_output += f"Generated Output Filename: {output_filename}\n"

        # Determine full output path
        if not output_path:
            # If no path provided, use ComfyUI's default output directory
            output_path = folder_paths.get_output_directory()
            log_output += f"Using default output directory: {output_path}\n"

        # Add subdirectory if provided
        if subdirectory:
            output_path = os.path.join(output_path, subdirectory)
            log_output += f"Using subdirectory: {subdirectory}\n"

        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        log_output += f"Ensuring output directory exists: {output_path}\n"

        # Full path for the output file
        full_path = os.path.join(output_path, output_filename)
        log_output += f"Full output file path: {full_path}\n"

        # Determine write mode based on overwrite flag
        mode = 'w' if overwrite else 'x'
        log_output += f"File write mode: {'overwrite' if overwrite else 'no overwrite'}\n"

        try:
            # Combine prefix text and main text
            if prefix_text:
                full_content = (prefix_text + text).strip()
                log_output += "Prefix text added to main text\n"
            else:
                full_content = text
                log_output += "No prefix text used\n"

            # Try to write the file
            try:
                with open(full_path, mode, encoding='utf-8') as f:
                    f.write(full_content)
                log_output += f"Text successfully written to {full_path}\n"
                log_output += f"Total characters written: {len(full_content)}\n"
            except FileExistsError:
                log_output += f"File {full_path} already exists. Skipping to prevent overwriting.\n"
                return (log_output,)

            return (log_output,)
        except Exception as e:
            log_output += f"Error writing to file: {e}\n"
            return (log_output,)

class WWAA_ImageToTextFile:
    DESCRIPTION = "Appends prompts from multiple images one by one to the same file, creating a batched file for LoRA testing. Takes prompts from LLM image analysis and writes them all to a single text file, with each entry on a new line. Supports optional prefix text for each entry."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "output_path": ("STRING", {"default": ""}),
            },
            "optional": {
                "filename": ("STRING", {"default": "output.txt"}),
                "prefix_text": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("log_output",)
    FUNCTION = "append_text"
    OUTPUT_NODE = True
    CATEGORY = "🪠️ WWAA"

    def clean_text(self, text):
        # Replace any combination of \r\n, \r, or \n with a space
        cleaned = re.sub(r'[\r\n]+', ' ', text)
        # Remove special characters except:
        # - alphanumeric (\w)
        # - space (\s)
        # - comma (,)
        # - period (\.)
        # - quote (")
        # - hyphen (-)
        # - semi-colon (;)
        cleaned = re.sub(r'[^\w\s,."-;]', '', cleaned)
        # Replace multiple spaces with a single space and strip
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def append_text(self, text, output_path, filename="output.txt", prefix_text=""):
        # Initialize log string
        log_output = ""

        # Log input parameters
        log_output += f"Input Parameters:\n"
        log_output += f"- Filename: {filename}\n"
        log_output += f"- Output Path: {output_path}\n"
        log_output += f"- Prefix Text: {bool(prefix_text)}\n\n"

        # Clean the input text and prefix
        cleaned_text = self.clean_text(text)
        cleaned_prefix = self.clean_text(prefix_text) if prefix_text else ""
        log_output += "Text cleaned: removed line breaks and excess whitespace\n"

        # Determine full output path
        if not output_path:
            # If no path provided, use ComfyUI's default output directory
            output_path = folder_paths.get_output_directory()
            log_output += f"Using default output directory: {output_path}\n"

        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        log_output += f"Ensuring output directory exists: {output_path}\n"

        # Full path for the output file
        full_path = os.path.join(output_path, filename)
        log_output += f"Full output file path: {full_path}\n"

        try:
            # Prepare content
            if cleaned_prefix:
                full_content = f"{cleaned_prefix} {cleaned_text}"
                log_output += "Prefix text added to content\n"
            else:
                full_content = cleaned_text
                log_output += "No prefix text used\n"

            # Check if file exists to determine if we need to add a newline
            file_exists = os.path.exists(full_path)

            # Open file in append mode
            with open(full_path, 'a', encoding='utf-8') as f:
                if file_exists:
                    # Add newline before content if file exists
                    f.write(f"\n{full_content}")
                    log_output += f"Appended text to existing file: {full_path}\n"
                else:
                    # Write content without leading newline for new file
                    f.write(full_content)
                    log_output += f"Created new file and wrote text: {full_path}\n"

            log_output += f"Total characters written: {len(full_content)}\n"
            return (log_output,)

        except Exception as e:
            log_output += f"Error writing to file: {e}\n"
            return (log_output,)

class WWAA_AdvancedTextFileReader:
    DESCRIPTION = "Reads text files like those produced by LLM Prompt to Text File and outputs them as strings for Clip Text Encoders. Supports multiple traversal modes (forward, reverse, random) with line skipping and hold functionality. Can output individual lines with tracking of current position and remaining lines."

    def __init__(self):
        self.current_index = 0
        self.lines = []
        self.total_lines = 0
        self.current_file = ""
        self.random_indices = set()
        self.last_traversal_mode = "forward"  # Track the last used traversal mode
        self.last_non_held_index = None  # Store the last index used when not holding
        self.held_index = None  # Store the index to hold

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
                "traversal_mode": (["forward", "reverse", "random"], {"default": "forward"}),
                "skip_lines": ("INT", {"default": 0, "min": 0, "max": 10}),
                "reset_counter": ("BOOLEAN", {"default": False}),
                "reload_file": ("BOOLEAN", {"default": False}),
                "hold_current_text": ("BOOLEAN", {"default": False}),  # New boolean parameter
            },
            "optional": {
                "starting_index": ("INT", {"default": 0, "min": 0, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "INT")
    RETURN_NAMES = ("current_line_text", "current_line_number", "total_lines", "remaining_lines")
    FUNCTION = "process_file"
    CATEGORY = "🪠️ WWAA"

    def should_reload_file(self, file_path, reload_file):
        """Determine if we should reload the file contents"""
        if reload_file:
            return True
        return file_path != self.current_file

    def load_file(self, file_path):
        """Load and prepare file contents"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
            self.lines = [line.strip() for line in file.readlines()]

        self.current_file = file_path
        self.total_lines = len(self.lines)

        if self.total_lines == 0:
            raise ValueError(f"No lines found in file: {file_path}")

    def adjust_index_for_mode_change(self, new_mode):
        """Adjust the current index when changing traversal modes"""
        if new_mode != self.last_traversal_mode:
            if new_mode == "random":
                # When switching to random, initialize the random indices
                self.random_indices = set(range(self.total_lines))
                # Remove the current index to avoid repetition
                if self.current_index in self.random_indices:
                    self.random_indices.remove(self.current_index)
            elif new_mode == "reverse" and self.last_traversal_mode == "forward":
                # When switching from forward to reverse, adjust the index
                # to get the previous item on the next iteration
                self.current_index = (self.current_index - 1) % self.total_lines
            elif new_mode == "forward" and self.last_traversal_mode == "reverse":
                # When switching from reverse to forward, adjust the index
                # to get the next item on the next iteration
                self.current_index = (self.current_index + 1) % self.total_lines

            self.last_traversal_mode = new_mode

    def get_next_index(self, traversal_mode, skip_lines):
        """Get the next line index based on traversal mode"""
        if not self.lines:
            return 0

        skip_amount = skip_lines + 1  # Include the natural advancement

        if traversal_mode == "forward":
            next_index = self.current_index
            self.current_index = (self.current_index + skip_amount) % self.total_lines
            return next_index

        elif traversal_mode == "reverse":
            next_index = self.current_index
            self.current_index = (self.current_index - skip_amount) % self.total_lines
            return next_index

        else:  # random mode
            if not self.random_indices:
                self.random_indices = set(range(self.total_lines))

            if not self.random_indices:  # All indices used
                self.random_indices = set(range(self.total_lines))

            next_index = random.choice(list(self.random_indices))
            self.random_indices.remove(next_index)

            # Skip additional lines if requested
            for _ in range(skip_lines):
                if self.random_indices:
                    self.random_indices.remove(random.choice(list(self.random_indices)))

            return next_index

    def get_remaining_lines(self, traversal_mode):
        """Calculate remaining lines based on traversal mode"""
        if not self.lines:
            return 0

        if traversal_mode == "random":
            return len(self.random_indices)
        elif traversal_mode == "forward":
            return self.total_lines - self.current_index
        else:  # reverse
            return self.current_index + 1

    def process_file(self, file_path, traversal_mode="forward", skip_lines=0,
                    reset_counter=False, reload_file=False, hold_current_text=False,
                    starting_index=None):
        # Convert to Path object for consistent handling
        file_path = str(Path(file_path))

        # Handle file reloading and counter reset
        if self.should_reload_file(file_path, reload_file):
            self.load_file(file_path)
            self.current_index = starting_index if starting_index is not None else 0
            self.last_traversal_mode = traversal_mode
            self.last_non_held_index = None
            self.held_index = None
        elif reset_counter:
            self.current_index = starting_index if starting_index is not None else 0
            self.last_traversal_mode = traversal_mode
            if traversal_mode == "random":
                self.random_indices = set(range(self.total_lines))
            self.last_non_held_index = None
            self.held_index = None
        elif starting_index is not None and self.current_index == 0:
            self.current_index = starting_index

        # Handle traversal mode changes
        self.adjust_index_for_mode_change(traversal_mode)

        # Get current line
        if not self.lines:
            return ("", 0, 0, 0)

        if hold_current_text:
            # If holding is active and we have a held index, use it
            if self.held_index is not None:
                line_index = self.held_index
            # If first time holding, use last non-held index if available
            # or get new index if not available
            else:
                if self.last_non_held_index is not None:
                    line_index = self.last_non_held_index
                else:
                    line_index = self.get_next_index(traversal_mode, skip_lines)
                self.held_index = line_index
        else:
            # Normal operation - get next index
            line_index = self.get_next_index(traversal_mode, skip_lines)
            # Update our tracking variables
            self.last_non_held_index = line_index
            self.held_index = None  # Reset held index when not holding

        current_line_text = self.lines[line_index]
        current_line_number = line_index + 1  # 1-based line numbering
        remaining_lines = self.get_remaining_lines(traversal_mode)

        return (current_line_text, current_line_number, self.total_lines, remaining_lines)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Always process to allow for proper line sequencing"""
        return float("nan")

class WWAA_SearchReplaceText:
    """
    A node that searches for a string in the input text and replaces it with another string.
    """

    DESCRIPTION = "Performs text search and replace operations on multi-line strings. Searches for all occurrences of a specified string and replaces them with another string. Useful for batch text modifications, prompt adjustments, and string manipulation tasks."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        """
        Define the input types for this node
        """
        return {
            "required": {
                "text_input": ("STRING", {"multiline": True}),
                "search_string": ("STRING", {"multiline": False}),
                "replace_string": ("STRING", {"multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("modified_text",)
    FUNCTION = "search_and_replace"
    CATEGORY = "🪠️ WWAA"

    def search_and_replace(self, text_input, search_string, replace_string):
        """
        Search for search_string in text_input and replace it with replace_string
        """
        if not search_string:
            # If search string is empty, return original text to avoid errors
            return (text_input,)

        # Perform the search and replace operation
        modified_text = text_input.replace(search_string, replace_string)

        return (modified_text,)

class WWAA_JSONPromptBuilder:
    """
    A node that builds structured JSON prompts with dropdown options for common values.
    Designed to create detailed, hierarchical prompts for image generation or LLM consumption.
    """

    DESCRIPTION = "Builds structured JSON prompts with hierarchical organization. Supports scene descriptions, subject details (with nested attributes like hair, face, body), environment settings, style options, and output parameters. Includes dropdown menus for common values and custom text fields for flexibility."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types with dropdowns for common values"""
        return {
            "required": {
                # Scene description
                "scene_description": ("STRING", {
                    "multiline": True,
                    "default": "A retro indoor photo shoot with pastel balloons."
                }),

                # Subject category and basic info
                "subject_category": (["human", "animal", "object", "abstract", "landscape", "architecture"],
                                    {"default": "human"}),
                "enable_subject_details": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                # Subject details (for human subjects - automatically ignored for non-human categories)
                "gender_presentation": (["male", "female", "non-binary", "androgynous", "N/A"],
                                       {"default": "N/A"}),
                "age_bracket": (["child", "teen", "young_adult", "middle_aged", "elderly", "N/A"],
                               {"default": "N/A"}),

                # Hair details (human only)
                "hair_length": (["bald", "very_short", "short", "medium", "long", "very_long", "N/A"],
                               {"default": "N/A"}),
                "hair_style": ("STRING", {"default": ""}),
                "hair_color": ("STRING", {"default": ""}),

                # Face details (adaptable for any subject with a face)
                "facial_expression": ("STRING", {"default": ""}),
                "makeup_details": ("STRING", {"default": ""}),
                "face_accessories": ("STRING", {"default": ""}),

                # Body/Physical details (adaptable for any subject)
                "body_pose": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "clothing": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "body_features": ("STRING", {"default": ""}),

                # General subject description (for any category)
                "subject_description": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),

                # Environment
                "background": ("STRING", {
                    "multiline": True,
                    "default": "plain white wall with colorful balloons"
                }),
                "floor": ("STRING", {"default": "white or light-colored, scattered balloons"}),
                "lighting": (["natural_soft", "natural_harsh", "studio_soft", "studio_harsh",
                             "direct_flash", "rim_light", "backlighting", "golden_hour", "blue_hour", "custom"],
                            {"default": "direct_flash"}),
                "lighting_custom": ("STRING", {"default": "high contrast, vintage tone"}),
                "mood": (["joyful", "serene", "melancholic", "energetic", "mysterious",
                         "romantic", "dramatic", "playful", "chaotic", "custom"],
                        {"default": "playful"}),
                "mood_custom": ("STRING", {"default": "retro, slightly chaotic energy"}),

                # Style
                "photography_style": (["digital_modern", "film_35mm", "film_medium_format",
                                      "disposable_camera", "polaroid", "vintage_90s",
                                      "black_and_white", "cinematic", "documentary", "custom"],
                                     {"default": "disposable_camera"}),
                "photography_custom": ("STRING", {"default": "90s disposable camera look, slightly grainy"}),
                "color_palette": ("STRING", {"default": "warm whites, soft pinks, reds, and blues"}),
                "aspect_ratio": (["1:1", "3:4", "4:3", "16:9", "9:16", "2:3", "3:2", "custom"],
                                {"default": "3:4"}),
                "aspect_ratio_custom": ("STRING", {"default": ""}),
                "render_intent": (["photo", "illustration", "3d_render", "painting",
                                  "sketch", "mixed_media"],
                                 {"default": "photo"}),

                # Output settings
                "camera_angle": (["eye_level", "high_angle", "low_angle", "bird_eye",
                                 "worm_eye", "dutch_angle", "over_shoulder", "custom"],
                                {"default": "high_angle"}),
                "camera_angle_custom": ("STRING", {"default": "subject looking up"}),
                "depth_of_field": (["shallow", "medium", "deep", "bokeh"],
                                  {"default": "shallow"}),
                "output_lighting": ("STRING", {"default": "harsh frontal flash"}),

                # Advanced options
                "include_empty_fields": ("BOOLEAN", {"default": False}),
                "indent_json": ("BOOLEAN", {"default": True}),
                "custom_fields": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("json_prompt",)
    FUNCTION = "build_json_prompt"
    CATEGORY = "🪠️ WWAA"

    def build_json_prompt(self, scene_description, subject_category, enable_subject_details,
                         gender_presentation="N/A", age_bracket="N/A",
                         hair_length="N/A", hair_style="", hair_color="",
                         facial_expression="", makeup_details="", face_accessories="",
                         body_pose="", clothing="", body_features="",
                         subject_description="",
                         background="", floor="", lighting="natural_soft", lighting_custom="",
                         mood="joyful", mood_custom="",
                         photography_style="digital_modern", photography_custom="",
                         color_palette="", aspect_ratio="1:1", aspect_ratio_custom="",
                         render_intent="photo",
                         camera_angle="eye_level", camera_angle_custom="",
                         depth_of_field="medium", output_lighting="",
                         include_empty_fields=False, indent_json=True,
                         custom_fields=""):

        # Build the JSON structure
        prompt_dict = {}

        # Scene
        if scene_description:
            prompt_dict["scene"] = scene_description

        # Subject
        if enable_subject_details:
            subject = {"category": subject_category}

            # Add general subject description if provided (works for any category)
            if subject_description:
                subject["description"] = subject_description

            # Only add human-specific fields if category is human
            if subject_category == "human":
                if gender_presentation != "N/A":
                    subject["gender_presentation"] = gender_presentation
                if age_bracket != "N/A":
                    subject["age_bracket"] = age_bracket

                # Hair details (human only)
                hair = {}
                if hair_length != "N/A":
                    hair["length"] = hair_length
                if hair_style:
                    hair["style"] = hair_style
                if hair_color:
                    hair["color"] = hair_color
                if hair or include_empty_fields:
                    subject["hair"] = hair

            # Face details (can apply to humans and animals)
            if subject_category in ["human", "animal"]:
                face = {}
                if facial_expression:
                    face["expression"] = facial_expression
                if makeup_details:
                    face["makeup"] = makeup_details
                if face_accessories:
                    face["accessories"] = face_accessories
                if face or include_empty_fields:
                    subject["face"] = face

            # Body/Physical details (can apply to most categories)
            if subject_category in ["human", "animal"]:
                body = {}
                if body_pose:
                    body["pose"] = body_pose
                if clothing:
                    body["clothing"] = clothing
                if body_features:
                    # Use more generic term for non-humans
                    feature_key = "tattoos" if subject_category == "human" else "features"
                    body[feature_key] = body_features
                if body or include_empty_fields:
                    subject["body"] = body

            prompt_dict["subject"] = subject

        # Environment
        environment = {}
        if background:
            environment["background"] = background
        if floor:
            environment["floor"] = floor

        # Lighting
        if lighting == "custom" and lighting_custom:
            environment["lighting"] = lighting_custom
        elif lighting != "custom":
            environment["lighting"] = lighting.replace("_", " ")

        # Mood
        if mood == "custom" and mood_custom:
            environment["mood"] = mood_custom
        elif mood != "custom":
            environment["mood"] = mood

        if environment or include_empty_fields:
            prompt_dict["environment"] = environment

        # Style
        style = {}

        # Photography style
        if photography_style == "custom" and photography_custom:
            style["photography"] = photography_custom
        elif photography_style != "custom":
            style["photography"] = photography_style.replace("_", " ")

        if color_palette:
            style["color_palette"] = color_palette

        # Aspect ratio
        if aspect_ratio == "custom" and aspect_ratio_custom:
            style["aspect_ratio"] = aspect_ratio_custom
        elif aspect_ratio != "custom":
            style["aspect_ratio"] = aspect_ratio

        if render_intent:
            style["render_intent"] = render_intent

        if style or include_empty_fields:
            prompt_dict["style"] = style

        # Output
        output = {}

        # Camera angle
        if camera_angle == "custom" and camera_angle_custom:
            output["camera_angle"] = camera_angle_custom
        elif camera_angle != "custom":
            output["camera_angle"] = camera_angle.replace("_", " ")

        if depth_of_field:
            output["depth_of_field"] = depth_of_field

        if output_lighting:
            output["lighting"] = output_lighting

        if output or include_empty_fields:
            prompt_dict["output"] = output

        # Custom fields (parse as JSON if provided)
        if custom_fields.strip():
            try:
                custom_data = json.loads(custom_fields)
                if isinstance(custom_data, dict):
                    prompt_dict.update(custom_data)
            except json.JSONDecodeError:
                # If not valid JSON, add as a custom note
                prompt_dict["custom_note"] = custom_fields

        # Convert to JSON string
        if indent_json:
            json_output = json.dumps(prompt_dict, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(prompt_dict, ensure_ascii=False)

        return (json_output,)
