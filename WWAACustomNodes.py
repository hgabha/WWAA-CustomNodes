import math, string, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
import torch.nn.functional as F
import os, folder_paths
import random
from pathlib import Path

debug = False
"""
WWAA Custom Nodes - do a bunch of different things. Made by WeirdWonderfulAI.art for self, shared with the Comfy Community
Image Batch Loader - Load Images from Directory and loop through them in different orders. Can read corresponding caption file as with same name .txt
Line Count - Have a multi-line string it will read and identify how many lines exist. Ignores blank lines
Join String - Combine a string with defined prefix and suffix text. Originally made to build a Lora string for inclusion into Prompts eg. <lora: Name:1> where Prefix is <lora: and Suffix is :1>
Dither Image - various different dithering functions to manipulate an image with variety of parameters you can control
Prompt Writer - feed it prompts related to images and it will write the prompt using the image filename, ready for LoRA training
LLM Prompt To Text File - feed prompts from multiple images one by one and this will write to the same file all your prompts creating a batched file for lora testing
Advanced Text File Reader - Can read txt files like the ones produced by LLM Prompt to Text file and output them as string for Clip Text Encoders
Game Boy Camera Style - a fun node that let's you convert image into game boy camera style. Original images are 128x112 so very small, this has some added upscale options
"""
class WWAA_ImageLoader:
    def __init__(self):
        self.current_index = 0
        self.image_files = []
        self.total_images = 0
        self.current_directory = ""
        self.current_extension = ""
        self.current_sort_method = ""
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": ""}),
                "file_extension": (["PNG", "JPG", "JPEG", "ALL"], {"default": "ALL"}),
                "reset_index": ("BOOLEAN", {"default": False}),
                "sort_method": (["alphabetical", "numerical", "creation_time", "modification_time"], {"default": "numerical"}),
                "reload_directory": ("BOOLEAN", {"default": False}),
                "read_caption": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "starting_index": ("INT", {"default": 0, "min": 0, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("image", "current_index", "total_images", "filename", "caption")
    FUNCTION = "load_image"
    CATEGORY = "🪠️WWAA"

    def natural_sort_key(self, s):
        """
        Sort strings containing numbers in natural order.
        Example: ['img1.png', 'img2.png', 'img10.png'] instead of ['img1.png', 'img10.png', 'img2.png']
        """
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]

    def sort_files(self, files, directory_path, sort_method):
        """Sort files based on the selected method"""
        if sort_method == "alphabetical":
            return sorted(files)
        elif sort_method == "numerical":
            return sorted(files, key=self.natural_sort_key)
        elif sort_method == "creation_time":
            return sorted(files, 
                        key=lambda x: os.path.getctime(os.path.join(directory_path, x)))
        elif sort_method == "modification_time":
            return sorted(files, 
                        key=lambda x: os.path.getmtime(os.path.join(directory_path, x)))
        return sorted(files)

    def should_reload_directory(self, directory_path, file_extension, sort_method, reload_directory):
        """
        Determine if we should reload the directory contents
        """
        # Force reload if reload_directory is True
        if reload_directory:
            return True
            
        # Reload if any settings have changed
        settings_changed = (
            directory_path != self.current_directory or
            file_extension != self.current_extension or
            sort_method != self.current_sort_method
        )
        
        return settings_changed

    def find_caption_file(self, directory_path, image_filename):
        """
        Find corresponding caption file with case-insensitive matching
        """
        # Get base filename without extension
        base_name = os.path.splitext(image_filename)[0]
        
        # List all txt files in directory (case-insensitive)
        txt_files = [f for f in os.listdir(directory_path) 
                    if f.lower().endswith('.txt')]
        
        # Look for matching filename (case-insensitive)
        for txt_file in txt_files:
            txt_base = os.path.splitext(txt_file)[0]
            if txt_base.lower() == base_name.lower():
                return os.path.join(directory_path, txt_file)
        
        return None

    def read_caption_text(self, directory_path, image_filename):
        """
        Read caption from corresponding txt file
        """
        caption_path = self.find_caption_file(directory_path, image_filename)
        if caption_path and os.path.exists(caption_path):
            try:
                with open(caption_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Warning: Could not read caption file {caption_path}: {str(e)}")
                return ""
        return ""

    def load_directory(self, directory_path, file_extension, sort_method):
        """
        Load and sort files from directory
        """
        # Update current settings
        self.current_directory = directory_path
        self.current_extension = file_extension
        self.current_sort_method = sort_method

        # Validate directory path
        if not os.path.exists(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")

        # Get all image files with specified extension
        allowed_extensions = ('.png', '.jpg', '.jpeg') if file_extension == "ALL" else \
                           (f'.{file_extension.lower()}',)
        
        # Get files and sort them according to the selected method
        files = [f for f in os.listdir(directory_path)
                if f.lower().endswith(allowed_extensions)]
        
        self.image_files = self.sort_files(files, directory_path, sort_method)
        self.total_images = len(self.image_files)
        
        if self.total_images == 0:
            raise ValueError(f"No images with extension {file_extension} found in directory")

    def load_image(self, directory_path, file_extension, reset_index, sort_method, reload_directory, read_caption, starting_index=None):
        # Check if we need to reload directory contents
        if self.should_reload_directory(directory_path, file_extension, sort_method, reload_directory):
            self.load_directory(directory_path, file_extension, sort_method)
            # Use starting_index on reload if provided
            self.current_index = starting_index if starting_index is not None else 0
        elif reset_index:
            # Use starting_index on reset if provided
            self.current_index = starting_index if starting_index is not None else 0
        # Set starting_index if provided and we're not reloading or resetting
        elif starting_index is not None and self.current_index == 0:
            self.current_index = starting_index

        # Ensure index is within bounds
        if self.current_index >= self.total_images:
            self.current_index = 0  # Wrap around to start
            
        # Get current filename
        current_filename = self.image_files[self.current_index]
        
        # Load the image at current index
        image_path = os.path.join(directory_path, current_filename)
        image = Image.open(image_path)
        
        # Convert image to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Convert to numpy array and then to torch tensor
        image_array = np.array(image).astype(np.float32) / 255.0
        
        # Convert to torch tensor and move to GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        image_tensor = torch.from_numpy(image_array).to(device)
        
        # Add batch dimension if needed
        if len(image_tensor.shape) == 3:
            image_tensor = image_tensor.unsqueeze(0)
        
        # Ensure tensor is in the correct memory layout
        image_tensor = image_tensor.contiguous()
        
        # Read caption if enabled
        caption = self.read_caption_text(directory_path, current_filename) if read_caption else ""
        
        # Store current index for next iteration
        current_index = self.current_index
        
        # Increment index for next run
        self.current_index += 1
        
        return (image_tensor, current_index, self.total_images, current_filename, caption)

    @classmethod
    def IS_CHANGED(cls, directory_path, file_extension, reset_index, sort_method, reload_directory, read_caption, starting_index=None):
        """
        Helper method to determine if the node needs to be re-executed
        """
        return float("nan")  # Always process to allow for proper image sequencing

class WWAA_LineCount:
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
    CATEGORY = "🪠️WWAA"
    
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
    CATEGORY = "🪠️WWAA"
    
    def executeBuildString(self, pre_text, input_text, post_text):
        #Concatenate and build string
        joinString = pre_text + input_text + post_text
        print(joinString if debug else "")
        return (joinString,)
        

class WWAA_DitherNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "dither_type": (["Floyd-Steinberg", "Atkinson", "Ordered", "Bayer", "Random", 
                                 "Jarvis-Judice-Ninke", "Stucki", "Burkes", "Sierra", "Two-Row Sierra", 
                                 "Sierra Lite", "Halftone"],),
                "contrast": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "scale": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "threshold": ("INT", {"default": 128, "min": 0, "max": 255, "step": 1}),
                "invert": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_dither"
    CATEGORY = "🪠️WWAA"

    def distributeError(self, img, x, y, error, kernel):
        h, w = img.shape
        for dx, dy, factor in kernel:
            if 0 <= x + dx < w and 0 <= y + dy < h:
                img[y + dy, x + dx] = np.clip(img[y + dy, x + dx] + error * factor, 0, 255)

    def apply_dither(self, image, dither_type, contrast, scale, threshold, invert):
        print(f"Input image shape: {image.shape}")
        
        dithered_images = []
        for img in image:
            img = img.cpu().numpy()
            print(f"Single image shape: {img.shape}")
            
            # Convert to grayscale
            img_gray = np.dot(img[..., :3], [0.2989, 0.5870, 0.1140])
            img_gray = (img_gray * 255).astype(np.float32)
            print(f"Grayscale image shape: {img_gray.shape}")
            
            # Apply contrast
            img_gray = np.clip((img_gray - 128) * contrast + 128, 0, 255)

            h, w = img_gray.shape
            
            # Reduce the size of the image based on the scale
            small_h, small_w = h // scale, w // scale
            img_small = Image.fromarray(img_gray.astype(np.uint8)).resize((small_w, small_h), Image.LANCZOS)
            img_gray = np.array(img_small).astype(np.float32)

            kernels = {
                "Floyd-Steinberg": [(1, 0, 7/16), (0, 1, 5/16), (-1, 1, 3/16), (1, 1, 1/16)],
                "Atkinson": [(1, 0, 1/8), (2, 0, 1/8), (-1, 1, 1/8), (0, 1, 1/8), (1, 1, 1/8), (0, 2, 1/8)],
                "Jarvis-Judice-Ninke": [
                    (1, 0, 7/48), (2, 0, 5/48),
                    (-2, 1, 3/48), (-1, 1, 5/48), (0, 1, 7/48), (1, 1, 5/48), (2, 1, 3/48),
                    (-2, 2, 1/48), (-1, 2, 3/48), (0, 2, 5/48), (1, 2, 3/48), (2, 2, 1/48)
                ],
                "Stucki": [
                    (1, 0, 8/42), (2, 0, 4/42),
                    (-2, 1, 2/42), (-1, 1, 4/42), (0, 1, 8/42), (1, 1, 4/42), (2, 1, 2/42),
                    (-2, 2, 1/42), (-1, 2, 2/42), (0, 2, 4/42), (1, 2, 2/42), (2, 2, 1/42)
                ],
                "Burkes": [
                    (1, 0, 8/32), (2, 0, 4/32),
                    (-2, 1, 2/32), (-1, 1, 4/32), (0, 1, 8/32), (1, 1, 4/32), (2, 1, 2/32)
                ],
                "Sierra": [
                    (1, 0, 5/32), (2, 0, 3/32),
                    (-2, 1, 2/32), (-1, 1, 4/32), (0, 1, 5/32), (1, 1, 4/32), (2, 1, 2/32),
                    (-1, 2, 2/32), (0, 2, 3/32), (1, 2, 2/32)
                ],
                "Two-Row Sierra": [
                    (1, 0, 4/16), (2, 0, 3/16),
                    (-2, 1, 1/16), (-1, 1, 2/16), (0, 1, 3/16), (1, 1, 2/16), (2, 1, 1/16)
                ],
                "Sierra Lite": [(1, 0, 2/4), (-1, 1, 1/4), (0, 1, 1/4)]
            }

            if dither_type in kernels:
                kernel = kernels[dither_type]
                for y in range(small_h):
                    for x in range(small_w):
                        old_pixel = img_gray[y, x]
                        new_pixel = 255 if old_pixel > threshold else 0
                        img_gray[y, x] = new_pixel
                        error = old_pixel - new_pixel
                        self.distributeError(img_gray, x, y, error, kernel)
            elif dither_type == "Ordered":
                threshold_map = np.array([
                    [15, 135, 45, 165],
                    [195, 75, 225, 105],
                    [60, 180, 30, 150],
                    [240, 120, 210, 90]
                ]) / 255.0
                threshold_map_full = np.tile(threshold_map, (small_h // 4 + 1, small_w // 4 + 1))[:small_h, :small_w]
                img_gray = np.where(img_gray / 255.0 > threshold_map_full, 255, 0)
            elif dither_type == "Bayer":
                bayer_matrix = np.array([
                    [0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5]
                ]) / 16.0
                bayer_full = np.tile(bayer_matrix, (small_h // 4 + 1, small_w // 4 + 1))[:small_h, :small_w]
                img_gray = np.where(img_gray / 255.0 > bayer_full, 255, 0)
            elif dither_type == "Random":
                random_threshold = np.random.rand(small_h, small_w)
                img_gray = np.where(img_gray / 255.0 > random_threshold, 255, 0)
            elif dither_type == "Halftone":
                x = np.tile(np.linspace(0, 1, small_w), (small_h, 1))
                y = np.tile(np.linspace(0, 1, small_h), (small_w, 1)).T
                dist = np.sqrt((x - 0.5)**2 + (y - 0.5)**2)
                halftone = np.where(dist < np.sqrt(img_gray / 255.0) / np.sqrt(2), 255, 0)
                img_gray = halftone

            # Clip values and convert back to uint8
            img_gray = np.clip(img_gray, 0, 255).astype(np.uint8)

            if invert:
                img_gray = 255 - img_gray

            # Scale the image back up to the original size
            img_dithered = np.array(Image.fromarray(img_gray).resize((w, h), Image.NEAREST))

            # Convert back to RGB
            img_dithered = np.stack([img_dithered, img_dithered, img_dithered], axis=-1)
            
            dithered_image = torch.from_numpy(img_dithered).float() / 255.0
            dithered_images.append(dithered_image)

        result = torch.stack(dithered_images)
        print(f"Output image shape: {result.shape}")
        return (result,)       

class WWAA_PromptWriter:
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
    CATEGORY = "🪠️WWAA"

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
    CATEGORY = "🪠️WWAA"

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
    def __init__(self):
        self.current_index = 0
        self.lines = []
        self.total_lines = 0
        self.current_file = ""
        self.random_indices = set()
        self.last_traversal_mode = "forward"  # Track the last used traversal mode
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
                "traversal_mode": (["forward", "reverse", "random"], {"default": "forward"}),
                "skip_lines": ("INT", {"default": 0, "min": 0, "max": 10}),
                "reset_counter": ("BOOLEAN", {"default": False}),
                "reload_file": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "starting_index": ("INT", {"default": 0, "min": 0, "step": 1}),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "INT", "INT")
    RETURN_NAMES = ("current_line", "current_line_number", "total_lines", "remaining_lines")
    FUNCTION = "process_file"
    CATEGORY = "🪠️WWAA"

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
                    reset_counter=False, reload_file=False, starting_index=None):
        # Convert to Path object for consistent handling
        file_path = str(Path(file_path))
        
        # Check if we need to reload the file
        if self.should_reload_file(file_path, reload_file):
            self.load_file(file_path)
            self.current_index = starting_index if starting_index is not None else 0
            self.last_traversal_mode = traversal_mode  # Reset the last traversal mode
        elif reset_counter:
            self.current_index = starting_index if starting_index is not None else 0
            self.last_traversal_mode = traversal_mode  # Reset the last traversal mode
            if traversal_mode == "random":
                self.random_indices = set(range(self.total_lines))
        elif starting_index is not None and self.current_index == 0:
            self.current_index = starting_index

        # Handle traversal mode changes
        self.adjust_index_for_mode_change(traversal_mode)

        # Get current line
        if not self.lines:
            return ("", 0, 0, 0)
            
        line_index = self.get_next_index(traversal_mode, skip_lines)
        current_line = self.lines[line_index]
        current_line_number = line_index + 1  # 1-based line numbering
        remaining_lines = self.get_remaining_lines(traversal_mode)
        
        return (current_line, current_line_number, self.total_lines, remaining_lines)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Always process to allow for proper line sequencing"""
        return float("nan")
class WWAA_GBCamera:
        
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mode": (["greyscale", "gameboy_green"],),
                "resolution": (["1x_gameboy", "2x_gameboy", "4x_gameboy"],),
                "upscale_factor": ("INT", {"default": 5, "min": 1, "max": 10})
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "🪠️WWAA"

    def __init__(self):
        # Base Game Boy Camera resolution
        self.gb_base_width = 128
        self.gb_base_height = 112

        # Game Boy palettes
        self.gb_greyscale = torch.tensor([
            [0, 0, 0],       # Black
            [86, 86, 86],    # Dark grey
            [172, 172, 172], # Light grey
            [255, 255, 255]  # White
        ], dtype=torch.float32) / 255.0

        self.gb_green = torch.tensor([
            [15, 56, 15],     # Darkest green
            [48, 98, 48],     # Dark green
            [139, 172, 15],   # Light green
            [155, 188, 15]    # Lightest green
        ], dtype=torch.float32) / 255.0

        # 8x8 Bayer matrix for ordered dithering
        self.bayer_matrix = torch.tensor([
            [ 0, 32,  8, 40,  2, 34, 10, 42],
            [48, 16, 56, 24, 50, 18, 58, 26],
            [12, 44,  4, 36, 14, 46,  6, 38],
            [60, 28, 52, 20, 62, 30, 54, 22],
            [ 3, 35, 11, 43,  1, 33,  9, 41],
            [51, 19, 59, 27, 49, 17, 57, 25],
            [15, 47,  7, 39, 13, 45,  5, 37],
            [63, 31, 55, 23, 61, 29, 53, 21]
        ], dtype=torch.float32) / 64.0 - 0.5

    def find_closest_palette_colors(self, image, palette):
        """Find the closest palette color for each pixel using L2 distance."""
        image_reshaped = image.reshape(-1, 1, 3)
        palette_reshaped = palette.to(image.device)
        
        distances = torch.sqrt(torch.sum((image_reshaped - palette_reshaped) ** 2, dim=2))
        closest_indices = torch.argmin(distances, dim=1)
        
        return palette_reshaped[closest_indices].reshape(image.shape)

    def ordered_dithering(self, image, palette):
        """Apply ordered dithering using Bayer matrix."""
        device = image.device
        batch_size, height, width, channels = image.shape
        
        bayer = self.bayer_matrix.to(device)
        bayer_h = ((height + 7) // 8) * 8
        bayer_w = ((width + 7) // 8) * 8
        bayer_tiled = bayer.repeat(bayer_h // 8, bayer_w // 8)[:height, :width]
        
        bayer_tiled = bayer_tiled.unsqueeze(0).unsqueeze(-1)
        bayer_tiled = bayer_tiled.expand(batch_size, -1, -1, channels)
        
        dither_strength = 1.0 / len(palette)
        dithered = image + bayer_tiled * dither_strength
        dithered = torch.clamp(dithered, 0.0, 1.0)
        
        return self.find_closest_palette_colors(dithered, palette)

    def calculate_target_size(self, original_height, original_width, target_height, target_width):
        """Calculate target size maintaining aspect ratio."""
        orig_aspect = original_width / original_height
        target_aspect = target_width / target_height
        
        if orig_aspect > target_aspect:
            # Image is wider than target
            new_width = target_width
            new_height = int(target_width / orig_aspect)
        else:
            # Image is taller than target
            new_height = target_height
            new_width = int(target_height * orig_aspect)
            
        return new_height, new_width

    def nearest_neighbor_upscale(self, image, scale_factor):
        """Upscale image using nearest neighbor interpolation."""
        b, h, w, c = image.shape
        return image.repeat_interleave(scale_factor, dim=1).repeat_interleave(scale_factor, dim=2)

    def process(self, image, mode="greyscale", resolution="1x_gameboy", upscale_factor=5):
        """Process the input image to apply Game Boy Camera effect."""
        device = image.device
        
        # Convert image to float32 and normalize to [0, 1]
        if image.dtype != torch.float32:
            image = image.float()
        if image.max() > 1.0:
            image = image / 255.0

        # Get resolution multiplier
        res_multiplier = {
            "1x_gameboy": 1,
            "2x_gameboy": 2,
            "4x_gameboy": 4
        }[resolution]
        
        # Calculate target dimensions while maintaining aspect ratio
        target_height, target_width = self.calculate_target_size(
            image.shape[1], 
            image.shape[2],
            self.gb_base_height * res_multiplier,
            self.gb_base_width * res_multiplier
        )

        # Resize image
        image = image.permute(0, 3, 1, 2)  # [B, C, H, W]
        image = F.interpolate(
            image, 
            size=(target_height, target_width), 
            mode='bilinear', 
            align_corners=False
        )
        image = image.permute(0, 2, 3, 1)  # Back to [B, H, W, C]
            
        # Select palette and apply dithering
        palette = self.gb_greyscale if mode == "greyscale" else self.gb_green
        processed = self.ordered_dithering(image, palette)

        # Upscale if needed
        if upscale_factor > 1:
            processed = self.nearest_neighbor_upscale(processed, upscale_factor)
            
        return (processed,)
    
# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
WWAA_CLASS_MAPPINGS = {
    "WWAA-LineCount": WWAA_LineCount,
    "WWAA-BuildString": WWAA_BuildString,
    "WWAA_DitherNode": WWAA_DitherNode,
    "WWAA_ImageLoader": WWAA_ImageLoader,
    "WWAA_PromptWriter": WWAA_PromptWriter,
    "WWAA_ImageToTextFile": WWAA_ImageToTextFile,
    "WWAA_AdvancedTextFileReader": WWAA_AdvancedTextFileReader,
    "WWAA_GBCamera": WWAA_GBCamera,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
WWAA_DISPLAY_NAME_MAPPINGS = {
    "WWAA-LineCount": "🪠️ WWAA LineCount",
    "WWAA-BuildString": "🪠️ WWAA JoinString",
    "WWAA_DitherNode": "🪠️ WWAA Dither Image",
    "WWAA_ImageLoader": "🪠️ WWAA Image Batch Loader",
    "WWAA_PromptWriter": "🪠️ WWAA Prompt Writer",
    "WWAA_ImageToTextFile": "🪠️ WWAA LLM Prompt To Text File",
    "WWAA_AdvancedTextFileReader": "🪠️ WWAA Advanced Text File Reader",
    "WWAA_GBCamera": "🪠️ WWAA Game Boy Camera Style"
}
