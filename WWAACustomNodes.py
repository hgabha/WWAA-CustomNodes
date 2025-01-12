import math, string, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
import os, folder_paths

debug = False
"""
WWAA Custom Nodes - do a bunch of different things. Made by WeirdWonderfulAI.art for self, shared with the Comfy Community
Image Batch Loader - Load Images from Directory and loop through them in different orders. Can read corresponding caption file as with same name .txt
Line Count - Have a multi-line string it will read and identify how many lines exist. Ignores blank lines
Join String - Combine a string with defined prefix and suffix text. Originally made to build a Lora string for inclusion into Prompts eg. <lora: Name:1> where Prefix is <lora: and Suffix is :1>
Dither Image - various different dithering functions to manipulate an image with variety of parameters you can control
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

    def load_image(self, directory_path, file_extension, reset_index, sort_method, reload_directory, read_caption):
        # Check if we need to reload directory contents
        if self.should_reload_directory(directory_path, file_extension, sort_method, reload_directory):
            self.load_directory(directory_path, file_extension, sort_method)
            self.current_index = 0  # Reset index on reload
        elif reset_index:
            self.current_index = 0

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
    def IS_CHANGED(cls, directory_path, file_extension, reset_index, sort_method, reload_directory, read_caption):
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

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
WWAA_CLASS_MAPPINGS = {
    "WWAA-LineCount": WWAA_LineCount,
    "WWAA-BuildString": WWAA_BuildString,
    "WWAA_DitherNode": WWAA_DitherNode,
    "WWAA_ImageLoader": WWAA_ImageLoader,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
WWAA_DISPLAY_NAME_MAPPINGS = {
    "WWAA-LineCount": "🪠️ WWAA LineCount",
    "WWAA-BuildString": "🪠️ WWAA JoinString",
    "WWAA_DitherNode": "🪠️ WWAA Dither Image",
    "WWAA_ImageLoader": "🪠️ WWAA Image Batch Loader"
}
