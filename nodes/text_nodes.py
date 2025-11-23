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
import csv
from io import StringIO

debug = False

class WWAA_NumberRangeAsString:
    DESCRIPTION = "Generates a comma-separated string of numbers from a start value to a stop value (inclusive). Takes two input numbers and creates a sequence string like '0, 1, 2, ..., 48'. Useful for generating frame numbers, index lists, or sequential prompts."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "start_at": ("INT", {
                    "default": 0,
                    "min": -1000,
                    "max": 1000,
                    "step": 1
                }),
                "stop_at": ("INT", {
                    "default": 48,
                    "min": -1000,
                    "max": 1000,
                    "step": 1
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("number_range",)

    FUNCTION = "execute_number_range"
    CATEGORY = "🪠️ WWAA/String"

    def execute_number_range(self, start_at, stop_at):
        # Generate range of numbers from start to stop (inclusive)
        if start_at <= stop_at:
            numbers = range(start_at, stop_at + 1)
        else:
            # Handle reverse range
            numbers = range(start_at, stop_at - 1, -1)
        
        # Convert to comma-separated string
        result = ", ".join(str(num) for num in numbers)
        
        print(result if debug else "")
        
        return (result,)

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
    CATEGORY = "🪠️ WWAA/String"

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
    CATEGORY = "🪠️ WWAA/String"

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
    CATEGORY = "🪠️ WWAA/String"

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
    CATEGORY = "🪠️ WWAA/String"

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
    CATEGORY = "🪠️ WWAA/String"

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
    CATEGORY = "🪠️ WWAA/String"

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
    CATEGORY = "🪠️ WWAA/String"

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

class WWAA_AdvancedTextReader:
    DESCRIPTION = "Reads multiline text input and outputs lines as strings for Clip Text Encoders. Supports multiple traversal modes (forward, reverse, random) with line skipping and hold functionality. Can output individual lines with tracking of current position and remaining lines."

    def __init__(self):
        self.current_index = 0
        self.lines = []
        self.total_lines = 0
        self.current_text_hash = None  # Track if input text has changed
        self.random_indices = set()
        self.last_traversal_mode = "forward"
        self.last_non_held_index = None
        self.held_index = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"default": "", "multiline": True}),
                "traversal_mode": (["forward", "reverse", "random"], {"default": "forward"}),
                "skip_lines": ("INT", {"default": 0, "min": 0, "max": 10}),
                "reset_counter": ("BOOLEAN", {"default": False}),
                "hold_current_text": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "starting_index": ("INT", {"default": 0, "min": 0, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT", "INT")
    RETURN_NAMES = ("current_line_text", "current_line_number", "total_lines", "remaining_lines")
    FUNCTION = "process_text"
    CATEGORY = "🪠️ WWAA/String"

    def should_reload_text(self, text_input):
        """Determine if we should reload the text contents"""
        text_hash = hash(text_input)
        if text_hash != self.current_text_hash:
            return True
        return False

    def load_text(self, text_input):
        """Load and prepare text contents"""
        if not text_input or text_input.strip() == "":
            raise ValueError("Text input is empty")

        # Split by newlines and strip whitespace from each line
        self.lines = [line.strip() for line in text_input.split('\n')]
        
        # Filter out empty lines if desired (optional - you can remove this if you want to keep empty lines)
        # self.lines = [line for line in self.lines if line]
        
        self.current_text_hash = hash(text_input)
        self.total_lines = len(self.lines)

        if self.total_lines == 0:
            raise ValueError("No lines found in text input")

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

            # Pick next random index
            next_index = random.choice(list(self.random_indices))
            self.random_indices.remove(next_index)

            # Skip additional random indices
            for _ in range(skip_lines):
                if self.random_indices:
                    skip_idx = random.choice(list(self.random_indices))
                    self.random_indices.remove(skip_idx)

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

    def process_text(self, text_input, traversal_mode="forward", skip_lines=0,
                    reset_counter=False, hold_current_text=False,
                    starting_index=None):
        
        # Handle text reloading when input changes
        if self.should_reload_text(text_input):
            self.load_text(text_input)
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

class WWAA_CameraAngleBuilder:
    """
    A node designed for Qwen Edit Multiple Angle Lora that builds camera angle and movement descriptions from dropdown selections.
    Combines rotation, forward movement, and vertical angle options into a single string.
    Get LoRA from: https://huggingface.co/dx8152/Qwen-Edit-2509-Multiple-angles
    """

    DESCRIPTION = "Made for Qwen Edit Multiple Angle Lora, this node builds camera angle and movement descriptions from dropdown menus. Combines rotation (left/right 45°/90°), forward movement (move forward/close-up), and vertical angles (top-down/worm's eye) into a single output string. Includes wide angle and custom angle options for precise control."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "rotate": ([
                    "Rotate right 90",
                    "Rotate right 45",
                    "None",
                    "Rotate left 45",
                    "Rotate left 90"
                ], {"default": "None"}),
                "forward": ([
                    "Move forward",
                    "Close-up",
                    "None"
                ], {"default": "None"}),
                "vertical": ([
                    "Top down view",
                    "Worm's eye view",
                    "None"
                ], {"default": "None"}),
                "wide_angle": ("BOOLEAN", {"default": False}),
                "custom_angle": ("BOOLEAN", {"default": False}),
                "angle_value": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 360,
                    "step": 5
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("camera_description",)
    FUNCTION = "build_camera_string"
    CATEGORY = "🪠️ WWAA/String"

    def build_camera_string(self, rotate, forward, vertical, wide_angle, custom_angle, angle_value):
        """
        Build a combined string from the selected camera angles and movements.
        """
        output_parts = []

        # Map rotation selections to output strings
        rotation_map = {
            "Rotate right 45": "将镜头向右旋转45度 Rotate the camera 45 degrees to the right.",
            "Rotate right 90": "将镜头向右旋转90度 Rotate the camera 90 degrees to the right.",
            "Rotate left 45": "将镜头向左旋转45度 Rotate the camera 45 degrees to the left.",
            "Rotate left 90": "将镜头向左旋转90度 Rotate the camera 90 degrees to the left.",
        }

        # Map forward movement selections to output strings
        forward_map = {
            "Move forward": "将镜头向前移动 Move the camera forward.",
            "Close-up": "将镜头转为特写镜头 Turn the camera to a close-up.",
        }

        # Map vertical angle selections to output strings
        vertical_map = {
            "Top down view": "将镜头转为俯视 Turn the camera to a top-down view.",
            "Worm's eye view": "将相机切换到仰视视角 Turn the camera to a worm's-eye view.",
        }

        # Add rotation if not "None"
        if rotate != "None":
            if custom_angle:
                # Replace the angle value in the rotation string with custom angle_value
                if "right" in rotate.lower():
                    output_parts.append(f"将镜头向右旋转{angle_value}度 Rotate the camera {angle_value} degrees to the right.")
                elif "left" in rotate.lower():
                    output_parts.append(f"将镜头向左旋转{angle_value}度 Rotate the camera {angle_value} degrees to the left.")
            else:
                output_parts.append(rotation_map.get(rotate, rotate))

        # Add forward movement if not "None"
        if forward != "None":
            output_parts.append(forward_map.get(forward, forward))

        # Add vertical angle if not "None"
        if vertical != "None":
            output_parts.append(vertical_map.get(vertical, vertical))

        # Add wide angle if enabled
        if wide_angle:
            output_parts.append("将镜头转为广角镜头 Turn the camera to a wide-angle lens.")

        # Join all parts with comma and space, or return empty string if nothing selected
        if output_parts:
            result = ", ".join(output_parts)
        else:
            result = ""

        return (result,)

class WWAA_SearchReplaceMulti:
    """
    A node that performs multiple search and replace operations on text input.
    Supports both line-based format (one pair per line) and comma-separated format.
    """

    DESCRIPTION = "Performs multiple find/replace operations on text in a single pass. Each line defines a search/replace pair using 'search;replace' format. Supports quoted strings for values containing special characters. Processes replacements sequentially in the order specified."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"multiline": True}),
                "search_replace_pairs": ("STRING", {
                    "multiline": True,
                    "default": "search1;replace1\nsearch2;replace2\n\"text, with comma\";\"replacement\""
                }),
                "use_comma_format": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("modified_text", "processing_log")
    FUNCTION = "search_and_replace_multi"
    CATEGORY = "🪠️ WWAA/String"

    def parse_line_format(self, pairs_text):
        """
        Parse line-based format:
        search1;replace1
        search2;replace2
        "quoted search";"quoted replace"
        """
        pairs = []
        lines = pairs_text.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Use CSV reader to properly handle quoted strings
            try:
                # CSV reader expects comma-separated, but we use semicolon
                # So we'll use it to parse each side separately
                parts = line.split(';', 1)
                if len(parts) != 2:
                    print(f"Warning: Line {line_num} doesn't contain semicolon separator: {line}")
                    continue
                
                search_part, replace_part = parts
                
                # Parse each part to handle quotes
                search = self.parse_quoted_string(search_part.strip())
                replace = self.parse_quoted_string(replace_part.strip())
                
                pairs.append((search, replace))
                
            except Exception as e:
                print(f"Error parsing line {line_num}: {line} - {e}")
                continue
        
        return pairs

    def parse_comma_format(self, pairs_text):
        """
        Parse comma-separated format:
        search1;replace1, search2;replace2, "quoted;search";"quoted;replace"
        """
        pairs = []
        
        # Use CSV reader to properly handle quoted strings with commas
        try:
            reader = csv.reader(StringIO(pairs_text.strip()), delimiter=',', quotechar='"')
            for row in reader:
                for item in row:
                    item = item.strip()
                    if not item:
                        continue
                    
                    parts = item.split(';', 1)
                    if len(parts) != 2:
                        print(f"Warning: Item doesn't contain semicolon separator: {item}")
                        continue
                    
                    search_part, replace_part = parts
                    search = self.parse_quoted_string(search_part.strip())
                    replace = self.parse_quoted_string(replace_part.strip())
                    
                    pairs.append((search, replace))
                    
        except Exception as e:
            print(f"Error parsing comma format: {e}")
        
        return pairs

    def parse_quoted_string(self, s):
        """Remove surrounding quotes if present"""
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            return s[1:-1]
        return s

    def search_and_replace_multi(self, text_input, search_replace_pairs, use_comma_format=False):
        """
        Perform multiple search and replace operations
        """
        log = []
        log.append("=== Search and Replace Multi - Processing Log ===\n")
        
        # Parse the pairs based on format
        if use_comma_format:
            log.append("Format: Comma-separated\n")
            pairs = self.parse_comma_format(search_replace_pairs)
        else:
            log.append("Format: Line-based\n")
            pairs = self.parse_line_format(search_replace_pairs)
        
        log.append(f"Total pairs parsed: {len(pairs)}\n\n")
        
        if not pairs:
            log.append("No valid search/replace pairs found.\n")
            return (text_input, "".join(log))
        
        # Start with original text
        modified_text = text_input
        
        # Apply each search/replace operation sequentially
        for idx, (search, replace) in enumerate(pairs, 1):
            if not search:  # Skip if search string is empty
                log.append(f"Pair {idx}: Skipped (empty search string)\n")
                continue
            
            # Count occurrences before replacement
            count = modified_text.count(search)
            
            # Perform replacement
            modified_text = modified_text.replace(search, replace)
            
            # Log the operation
            log.append(f"Pair {idx}:\n")
            log.append(f"  Search:  '{search}'\n")
            log.append(f"  Replace: '{replace}'\n")
            log.append(f"  Matches: {count}\n\n")
        
        log.append("=== Processing Complete ===\n")
        
        # Print log if debug is enabled
        if debug:
            print("".join(log))
        
        return (modified_text, "".join(log))
