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
from datetime import datetime

debug = False

class WWAA_NestedLoopCounter:
    DESCRIPTION = "Implements a nested loop counter for complex iteration patterns. Maintains state across executions with customizable maximum values and increment steps. Returns both integer and float values for 'i' and 'j' loop variables, along with debug logging for tracking execution state."

    def __init__(self):
        # Initialize state in instance variables
        self.current_i = 0
        self.current_j = 0
        self.execution_count = 0

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "max_value": ("INT", {"default": 10, "min": 1, "max": 10000}),
                "increment": ("INT", {"default": 1, "min": 1, "max": 1000}),
                "reset": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("i", "j", "i_float", "j_float", "debug_log")
    FUNCTION = "count"
    CATEGORY = "🪠️ WWAA/utilities"

    def count(self, max_value, increment, reset):
        # Increment execution count
        self.execution_count += 1

        debug_msg = f"Execution #{self.execution_count}\n"
        debug_msg += f"Starting state: i={self.current_i}, j={self.current_j}\n"

        # Handle reset
        if reset:
            debug_msg += "Reset triggered\n"
            self.current_i = 0
            self.current_j = 0
            return (0, 0, 0.0, 0.0, debug_msg)

        # Store current values for return
        i = self.current_i
        j = self.current_j

        # Calculate next state
        self.current_j += increment

        if self.current_j >= max_value:
            self.current_j = 0
            self.current_i += increment
            debug_msg += f"j reached max_value, incrementing i to {self.current_i}\n"

        if self.current_i >= max_value:
            self.current_i = 0
            self.current_j = 0
            debug_msg += "i reached max_value, resetting both counters\n"

        debug_msg += f"Returning: i={i}, j={j}\n"
        debug_msg += f"Next state will be: i={self.current_i}, j={self.current_j}"

        return (i, j, float(i), float(j), debug_msg)

    @classmethod
    def IS_CHANGED(cls, max_value, increment, reset):
        """
        Tell ComfyUI to always process this node to allow for proper counter sequencing
        """
        return float("nan")

class WWAA_Switch_Int:
    """
    A ComfyUI node that takes two integer inputs and outputs them directly or swapped
    based on a boolean switch parameter.
    """

    DESCRIPTION = "Takes two integer inputs and outputs them either as-is or swapped based on a boolean switch parameter. When switch is False, outputs (int_a, int_b). When switch is True, outputs (int_b, int_a). Useful for conditional value routing and dynamic parameter switching."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "int_a": ("INT",),
                "int_b": ("INT",),
                "switch": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("output_1", "output_2")
    FUNCTION = "switch_ints"
    CATEGORY = "🪠️ WWAA/utilities"

    def switch_ints(self, int_a, int_b, switch):
        """
        Switch the two integer values based on the boolean switch parameter.

        Args:
            int_a (int): First integer input
            int_b (int): Second integer input
            switch (bool): When True, swap the outputs. When False, output as-is.

        Returns:
            tuple: (output_1, output_2) - either (int_a, int_b) or (int_b, int_a)
        """
        if switch:
            # Switch/swap the values
            return (int_b, int_a)
        else:
            # Return values as-is
            return (int_a, int_b)

class WWAA_MetadataSaver:
    """
    A ComfyUI node that saves prompt and seed metadata to a text file.
    Takes a prompt string and seed integer, saves them to a specified file with auto-incrementing numbering,
    and outputs the full file path and filename prefix.
    """

    DESCRIPTION = "Saves prompt and seed metadata to text files with automatic file numbering. Takes a prompt string and seed integer, creates numbered files starting from 01 with no upper limit, and outputs the full file path and filename prefix. Files are saved to ComfyUI's output directory by default. Supports date formatting in filename prefix using %date:format% syntax (e.g., %date:yyyy-MM-dd% or %date:yyyyMMdd%). Supports subfolder creation by including path separators in the prefix (e.g., '%date:yyyy-MM-dd%/Ernest_ETv8_' creates a dated subfolder)."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "filename_prefix": ("STRING", {"default": "metadata_%date:yyyy-MM-dd%"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename_prefix",)
    FUNCTION = "save_metadata"
    OUTPUT_NODE = True
    CATEGORY = "🪠️ WWAA/utilities"

    def format_date_string(self, text):
        """
        Replace date placeholders in text with actual dates.
        Supports ComfyUI-style formatting: %date:yyyy-MM-dd%
        """
        import re

        # Find all date patterns like %date:yyyy-MM-dd%
        pattern = r'%date:([^%]+)%'

        def replace_date(match):
            format_str = match.group(1)
            now = datetime.now()

            # Convert ComfyUI format to Python strftime format
            # yyyy -> %Y, MM -> %m, dd -> %d, HH -> %H, mm -> %M, ss -> %S
            py_format = format_str
            py_format = py_format.replace('yyyy', '%Y')
            py_format = py_format.replace('yy', '%y')
            py_format = py_format.replace('MM', '%m')
            py_format = py_format.replace('dd', '%d')
            py_format = py_format.replace('HH', '%H')
            py_format = py_format.replace('mm', '%M')
            py_format = py_format.replace('ss', '%S')

            return now.strftime(py_format)

        return re.sub(pattern, replace_date, text)

    def find_next_filename(self, output_folder, prefix):
        """Find the next available filename with incrementing number"""
        counter = 1
        while True:
            filename = f"{prefix}_{counter:02d}.txt"
            full_path = os.path.join(output_folder, filename)
            if not os.path.exists(full_path):
                return full_path, filename
            counter += 1

    def save_metadata(self, prompt, seed, filename_prefix):
        # Use ComfyUI's default output directory
        output_folder = folder_paths.get_output_directory()

        # Process date formatting in filename prefix
        formatted_prefix = self.format_date_string(filename_prefix)

        # Keep track of the full formatted prefix for output
        output_prefix = formatted_prefix

        # Check if prefix contains path separators (subfolders)
        if '/' in formatted_prefix or '\\' in formatted_prefix:
            # Normalize path separators to OS-specific
            formatted_prefix = formatted_prefix.replace('/', os.sep).replace('\\', os.sep)

            # Split into directory and filename parts
            prefix_parts = formatted_prefix.rsplit(os.sep, 1)
            if len(prefix_parts) == 2:
                subfolder, file_prefix = prefix_parts
                # Create full path including subfolder
                output_folder = os.path.join(output_folder, subfolder)
                formatted_prefix = file_prefix
            else:
                # No subfolder, just filename
                formatted_prefix = prefix_parts[0]

        # Ensure output directory exists (including any subfolders)
        os.makedirs(output_folder, exist_ok=True)

        # Find next available filename
        full_path, filename = self.find_next_filename(output_folder, formatted_prefix)

        # Prepare content
        content = f"Prompt: {prompt}\nSeed: {seed}\n"

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Metadata saved to: {full_path}")
        except Exception as e:
            print(f"Error saving metadata: {e}")
            raise

        return (output_prefix,)
class WWAA_DisplayAny:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input": (("*",{})),
                "mode": (["raw value", "tensor shape"],),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(s, input_types):
        return True

    RETURN_TYPES = ("STRING",)
    FUNCTION = "execute"
    OUTPUT_NODE = True

    CATEGORY = "🪠️ WWAA/utilities"

    def execute(self, input, mode):
        if mode == "tensor shape":
            text = []
            def tensorShape(tensor):
                if isinstance(tensor, dict):
                    for k in tensor:
                        tensorShape(tensor[k])
                elif isinstance(tensor, list):
                    for i in range(len(tensor)):
                        tensorShape(tensor[i])
                elif hasattr(tensor, 'shape'):
                    text.append(list(tensor.shape))

            tensorShape(input)
            input = text

        text = str(input)

        return {"ui": {"text": [text]}, "result": (text,)}

class WWAA_TextFileBrowser:
    """
    A ComfyUI node that browses a directory for .csv and .txt files and provides
    a dropdown selector to choose a file. Outputs the full file path as a string.
    """

    DESCRIPTION = "Browses a directory path for .csv and .txt files and populates a dropdown menu with found filenames. Outputs the full file path of the selected file as a string. Only searches the top-level directory (non-recursive). Dropdown updates dynamically when the directory path is changed."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "", "multiline": False}),
            },
            "hidden": {
                "selected_file": "STRING",
            }
        }

    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("file_path", "filename",)
    FUNCTION = "get_file_path"
    CATEGORY = "🪠️ WWAA/utilities"

    @classmethod
    def get_files_from_directory(cls, directory_path):
        """
        Scan directory for .csv and .txt files (non-recursive).
        Returns list of filenames with extensions.
        """
        print(f"[WWAA_TextFileBrowser] Scanning directory: '{directory_path}'")
        
        if not directory_path:
            print("[WWAA_TextFileBrowser] Directory path is empty")
            return []
            
        if not os.path.exists(directory_path):
            print(f"[WWAA_TextFileBrowser] Directory does not exist: {directory_path}")
            return []
        
        if not os.path.isdir(directory_path):
            print(f"[WWAA_TextFileBrowser] Path is not a directory: {directory_path}")
            return []
        
        try:
            files = []
            for item in os.listdir(directory_path):
                full_path = os.path.join(directory_path, item)
                if os.path.isfile(full_path):
                    _, ext = os.path.splitext(item)
                    if ext.lower() in ['.csv', '.txt']:
                        files.append(item)
            
            print(f"[WWAA_TextFileBrowser] Found {len(files)} files")
            return sorted(files)
        except Exception as e:
            print(f"[WWAA_TextFileBrowser] Error reading directory: {e}")
            return []

    def get_file_path(self, directory_path, selected_file):
        """
        Returns the full path and filename of the selected file
        """
        if not directory_path or selected_file in ["No files found", "Error reading directory"]:
            return ("", "")
        
        full_path = os.path.join(directory_path, selected_file)
        
        if os.path.exists(full_path):
            return (full_path, selected_file)
        else:
            return ("", "")