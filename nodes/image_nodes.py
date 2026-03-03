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
import ctypes

debug = False

class WWAA_ImageLoader:
    DESCRIPTION = "Loads images from a directory and loops through them in different orders with multiple sorting options (alphabetical, numerical, creation time, modification time, Windows Explorer style). Can read corresponding caption files with matching names as .txt files. Supports various image formats including PNG, JPG, JPEG, and WEBP."

    def __init__(self):
        self.current_index = 0
        self.image_files = []
        self.total_images = 0
        self.current_directory = ""
        self.current_extension = ""
        self.current_sort_method = ""
        
        # Initialize Windows sorting if available
        self.windows_sort_available = False
        try:
            if os.name == 'nt':  # Windows
                self.shlwapi = ctypes.windll.shlwapi
                self.windows_sort_available = True
        except:
            pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": ""}),
                "file_extension": (["PNG", "JPG", "JPEG","WEBP", "ALL"], {"default": "ALL"}),
                "reset_index": ("BOOLEAN", {"default": False}),
                "sort_method": (["alphabetical", "numerical", "windows_sort", "creation_time", "modification_time"], {"default": "numerical"}),
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
    CATEGORY = "🪠️ WWAA/image"

    def natural_sort_key(self, s):
        """
        Sort strings containing numbers in natural order.
        Example: ['img1.png', 'img2.png', 'img10.png'] instead of ['img1.png', 'img10.png', 'img2.png']
        """
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split('([0-9]+)', s)]
    
    def windows_sort_key(self, s1, s2):
        """
        Windows Explorer style sorting using StrCmpLogicalW.
        Returns negative if s1 < s2, zero if s1 == s2, positive if s1 > s2
        """
        if not self.windows_sort_available:
            # Fallback to natural sort if Windows API not available
            key1 = self.natural_sort_key(s1)
            key2 = self.natural_sort_key(s2)
            if key1 < key2:
                return -1
            elif key1 > key2:
                return 1
            else:
                return 0
        
        try:
            # Use Windows StrCmpLogicalW for proper Windows Explorer sorting
            result = self.shlwapi.StrCmpLogicalW(s1, s2)
            return result
        except:
            # Fallback to natural sort on error
            key1 = self.natural_sort_key(s1)
            key2 = self.natural_sort_key(s2)
            if key1 < key2:
                return -1
            elif key1 > key2:
                return 1
            else:
                return 0

    def sort_files(self, files, directory_path, sort_method):
        """Sort files based on the selected method"""
        if sort_method == "alphabetical":
            return sorted(files)
        elif sort_method == "numerical":
            return sorted(files, key=self.natural_sort_key)
        elif sort_method == "windows_sort":
            # Use Windows Explorer sorting
            from functools import cmp_to_key
            return sorted(files, key=cmp_to_key(self.windows_sort_key))
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
        allowed_extensions = ('.png', '.jpg', '.jpeg','.webp') if file_extension == "ALL" else \
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

class WWAA_DitherNode:
    DESCRIPTION = "Applies various dithering functions to manipulate images with a wide variety of controllable parameters. Supports multiple dithering algorithms including Floyd-Steinberg, Atkinson, Ordered, Bayer, Random, Jarvis-Judice-Ninke, Stucki, Burkes, Sierra variations, and Halftone. Includes GPU acceleration support for faster processing."

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
                "use_gpu": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_dither"
    CATEGORY = "🪠️ WWAA/image"

    def error_diffuse(self, img, kernel_definition, threshold):
        """Vectorized error diffusion implementation"""
        device = img.device
        height, width = img.shape
        output = torch.zeros_like(img)

        # Create error buffer
        error_buffer = img.clone()

        # Create kernel tensors
        offsets_x = []
        offsets_y = []
        weights = []

        for dx, dy, weight in kernel_definition:
            offsets_x.append(dx)
            offsets_y.append(dy)
            weights.append(weight)

        weights = torch.tensor(weights, device=device).view(-1, 1, 1)

        # Process image in parallel for each row
        for y in range(height):
            # Threshold the current row
            current = error_buffer[y:y+1, :]
            quantized = torch.where(current > threshold,
                                  torch.tensor(255.0, device=device),
                                  torch.tensor(0.0, device=device))
            output[y:y+1, :] = quantized

            # Calculate error
            error = current - quantized

            # Distribute error to neighboring pixels
            for idx, (dx, dy) in enumerate(zip(offsets_x, offsets_y)):
                if dy + y >= 0 and dy + y < height:
                    if dx < 0:  # Left shift
                        target = F.pad(error[:, :-abs(dx)], (abs(dx), 0))
                    elif dx > 0:  # Right shift
                        target = F.pad(error[:, dx:], (0, dx))
                    else:
                        target = error

                    if 0 <= y + dy < height:
                        error_buffer[y+dy:y+dy+1, :] += target * weights[idx]

        return output

    def apply_dither(self, image, dither_type, contrast, scale, threshold, invert, use_gpu):
        print(f"Input image shape: {image.shape}")

        # Determine device based on use_gpu setting
        target_device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')

        # If we're using CPU, make sure we move the input to CPU
        if not use_gpu:
            image = image.cpu()

        dithered_images = []
        for img in image:
            # Move current image to target device
            img = img.to(target_device)

            # Convert to grayscale using device-specific operations
            rgb_weights = torch.tensor([0.2989, 0.5870, 0.1140], device=target_device)
            img_gray = torch.sum(img * rgb_weights.view(1, 1, 3), dim=2) * 255

            # Apply contrast
            img_gray = torch.clamp((img_gray - 128) * contrast + 128, 0, 255)

            h, w = img_gray.shape

            # Reduce size based on scale
            small_h, small_w = h // scale, w // scale
            img_small = F.interpolate(
                img_gray.unsqueeze(0).unsqueeze(0),
                size=(small_h, small_w),
                mode='bicubic',
                align_corners=False
            ).squeeze(0).squeeze(0)

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
                img_small = self.error_diffuse(img_small, kernels[dither_type], threshold)
            elif dither_type == "Ordered":
                threshold_map = torch.tensor([
                    [15, 135, 45, 165],
                    [195, 75, 225, 105],
                    [60, 180, 30, 150],
                    [240, 120, 210, 90]
                ], device=target_device) / 255.0
                threshold_map_full = threshold_map.repeat(
                    (small_h + 3) // 4, (small_w + 3) // 4
                )[:small_h, :small_w]
                img_small = torch.where(img_small / 255.0 > threshold_map_full, 255.0, 0.0)
            elif dither_type == "Bayer":
                bayer_matrix = torch.tensor([
                    [0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5]
                ], device=target_device) / 16.0
                bayer_full = bayer_matrix.repeat(
                    (small_h + 3) // 4, (small_w + 3) // 4
                )[:small_h, :small_w]
                img_small = torch.where(img_small / 255.0 > bayer_full, 255.0, 0.0)
            elif dither_type == "Random":
                random_threshold = torch.rand(small_h, small_w, device=target_device)
                img_small = torch.where(img_small / 255.0 > random_threshold, 255.0, 0.0)
            elif dither_type == "Halftone":
                x = torch.linspace(0, 1, small_w, device=target_device).repeat(small_h, 1)
                y = torch.linspace(0, 1, small_h, device=target_device).view(-1, 1).repeat(1, small_w)
                dist = torch.sqrt((x - 0.5)**2 + (y - 0.5)**2)
                halftone = torch.where(
                    dist < torch.sqrt(img_small / 255.0) / torch.sqrt(torch.tensor(2.0, device=target_device)),
                    255.0, 0.0
                )
                img_small = halftone

            # Clip values
            img_small = torch.clamp(img_small, 0, 255)

            if invert:
                img_small = 255 - img_small

            # Scale back up to original size
            img_dithered = F.interpolate(
                img_small.unsqueeze(0).unsqueeze(0),
                size=(h, w),
                mode='nearest'
            ).squeeze(0).squeeze(0)

            # Convert back to RGB
            img_dithered = img_dithered.repeat(3, 1, 1).permute(1, 2, 0)

            dithered_image = img_dithered / 255.0
            dithered_images.append(dithered_image)

        result = torch.stack(dithered_images)

        # Ensure result is on the correct device
        if not use_gpu:
            result = result.cpu()

        print(f"Output image shape: {result.shape}")
        return (result,)

class WWAA_GBCamera:
    DESCRIPTION = "Converts images into Game Boy Camera style with authentic retro aesthetics. Original Game Boy Camera images are 128x112 pixels, and this node includes multiple resolution options and upscaling. Supports both greyscale and classic Game Boy green color palettes with Bayer matrix dithering for authentic retro look."

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
    CATEGORY = "🪠️ WWAA/image"

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

class WWAA_GridLayoutNode:
    """
    A ComfyUI node that arranges multiple images in a grid layout.
    Takes row and column counts, multiple images, and creates a composite grid image.
    """

    DESCRIPTION = "Places images sequentially in grid cells using all available images up to grid capacity. Empty cells display the specified background color. Maximum output scale is 100%."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "rows": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                "columns": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                "background_color": ("STRING", {
                    "default": "#000000",
                    "multiline": False
                }),
                "output_scale": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 100,
                    "step": 10,
                    "display": "number"
                })
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grid_image",)
    FUNCTION = "create_grid"
    CATEGORY = "🪠️ WWAA/image"

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            hex_color = "000000"  # Default to black if invalid
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            return (0, 0, 0)  # Default to black if conversion fails

    def tensor_to_pil(self, tensor_image):
        """Convert ComfyUI tensor to PIL Image"""
        # ComfyUI images are typically in format [batch, height, width, channels]
        if len(tensor_image.shape) == 4:
            tensor_image = tensor_image[0]  # Take first batch

        # Convert from tensor to numpy
        numpy_image = tensor_image.cpu().numpy()

        # Ensure values are in 0-255 range
        if numpy_image.max() <= 1.0:
            numpy_image = (numpy_image * 255).astype(np.uint8)
        else:
            numpy_image = numpy_image.astype(np.uint8)

        # Convert to PIL Image
        if numpy_image.shape[2] == 3:  # RGB
            return Image.fromarray(numpy_image, 'RGB')
        elif numpy_image.shape[2] == 4:  # RGBA
            return Image.fromarray(numpy_image, 'RGBA')
        else:  # Grayscale
            return Image.fromarray(numpy_image[:,:,0], 'L').convert('RGB')

    def pil_to_tensor(self, pil_image):
        """Convert PIL Image to ComfyUI tensor format"""
        # Convert to RGB if not already
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Convert to numpy array
        numpy_image = np.array(pil_image).astype(np.float32) / 255.0

        # Convert to tensor and add batch dimension
        tensor_image = torch.from_numpy(numpy_image)[None,]

        return tensor_image

    def create_grid(self, images, rows, columns, background_color, output_scale):
        """Create a grid layout from the provided images"""

        # Handle both single image and batch of images
        if len(images.shape) == 4 and images.shape[0] > 1:
            # Multiple images in batch
            image_list = [images[i] for i in range(images.shape[0])]
        else:
            # Single image or single image in batch
            if len(images.shape) == 4:
                image_list = [images[0]]
            else:
                image_list = [images]

        if not image_list:
            raise ValueError("At least one image must be provided")

        # Convert first image to get dimensions
        first_pil = self.tensor_to_pil(image_list[0])
        cell_width, cell_height = first_pil.size

        # Calculate canvas dimensions
        canvas_width = cell_width * columns
        canvas_height = cell_height * rows

        # Parse background color
        bg_color = self.hex_to_rgb(background_color)

        # Create canvas
        canvas = Image.new('RGB', (canvas_width, canvas_height), bg_color)

        # Calculate total cells needed
        total_cells = rows * columns

        # Place images on grid - only fill cells up to the number of available images
        # Remaining cells will stay as background color
        for i in range(len(image_list)):
            if i >= total_cells:
                break  # Don't exceed grid capacity

            # Calculate grid position
            row = i // columns
            col = i % columns

            # Calculate pixel position
            x = col * cell_width
            y = row * cell_height

            # Convert tensor to PIL and resize to match cell dimensions
            pil_img = self.tensor_to_pil(image_list[i])
            if pil_img.size != (cell_width, cell_height):
                pil_img = pil_img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)

            # Paste image onto canvas
            canvas.paste(pil_img, (x, y))

        # Apply output scaling if not 100%
        if output_scale != 100:
            scale_factor = output_scale / 100.0
            new_width = int(canvas_width * scale_factor)
            new_height = int(canvas_height * scale_factor)
            canvas = canvas.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert back to ComfyUI tensor format
        output_tensor = self.pil_to_tensor(canvas)

        return (output_tensor,)

class WWAA_AdvancedGridLayoutNode:
    """
    An advanced ComfyUI node that intelligently selects frames from an image sequence
    to create a grid layout. Always includes first and last images from the sequence.
    """

    DESCRIPTION = "Intelligently selects representative frames from image sequences, always including the first and last images while evenly distributing middle frames. Designed for video and animation sequences where you want key frames displayed. Maximum output scale is 200% for double resolution output."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "rows": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                "columns": ("INT", {
                    "default": 2,
                    "min": 2,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                "background_color": ("STRING", {
                    "default": "#000000",
                    "multiline": False
                }),
                "output_scale": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 200,
                    "step": 1,
                    "display": "number"
                })
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grid_image",)
    FUNCTION = "create_advanced_grid"
    CATEGORY = "🪠️ WWAA/image"

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            hex_color = "000000"  # Default to black if invalid
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            return (0, 0, 0)  # Default to black if conversion fails

    def tensor_to_pil(self, tensor_image):
        """Convert ComfyUI tensor to PIL Image"""
        # ComfyUI images are typically in format [batch, height, width, channels]
        if len(tensor_image.shape) == 4:
            tensor_image = tensor_image[0]  # Take first batch

        # Convert from tensor to numpy
        numpy_image = tensor_image.cpu().numpy()

        # Ensure values are in 0-255 range
        if numpy_image.max() <= 1.0:
            numpy_image = (numpy_image * 255).astype(np.uint8)
        else:
            numpy_image = numpy_image.astype(np.uint8)

        # Convert to PIL Image
        if numpy_image.shape[2] == 3:  # RGB
            return Image.fromarray(numpy_image, 'RGB')
        elif numpy_image.shape[2] == 4:  # RGBA
            return Image.fromarray(numpy_image, 'RGBA')
        else:  # Grayscale
            return Image.fromarray(numpy_image[:,:,0], 'L').convert('RGB')

    def pil_to_tensor(self, pil_image):
        """Convert PIL Image to ComfyUI tensor format"""
        # Convert to RGB if not already
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Convert to numpy array
        numpy_image = np.array(pil_image).astype(np.float32) / 255.0

        # Convert to tensor and add batch dimension
        tensor_image = torch.from_numpy(numpy_image)[None,]

        return tensor_image

    def select_frame_indices(self, total_images, grid_size):
        """
        Intelligently select frame indices ensuring first and last frames are included.
        Returns list of indices to use for the grid.
        """
        if total_images <= grid_size:
            # If we have fewer or equal images than grid cells, use all images
            return list(range(total_images))

        if grid_size == 1:
            # Edge case: only one cell, use first image
            return [0]

        if grid_size == 2:
            # Only two cells: first and last
            return [0, total_images - 1]

        # For grid_size > 2: first image, evenly distributed middle images, last image
        selected_indices = [0]  # Always start with first image

        # Calculate indices for middle images
        # We need (grid_size - 2) middle images between first and last
        middle_slots = grid_size - 2

        if middle_slots > 0:
            # Create evenly spaced indices between index 1 and (total_images - 2)
            # This ensures we don't duplicate first or last image
            start_idx = 1
            end_idx = total_images - 2

            if start_idx <= end_idx:
                # Calculate step size for even distribution
                if middle_slots == 1:
                    # Only one middle slot, pick the middle image
                    middle_idx = (start_idx + end_idx) // 2
                    selected_indices.append(middle_idx)
                else:
                    # Multiple middle slots, distribute evenly
                    step = (end_idx - start_idx) / (middle_slots - 1)
                    for i in range(middle_slots):
                        idx = int(start_idx + i * step)
                        selected_indices.append(idx)

        # Always end with last image
        selected_indices.append(total_images - 1)

        # Remove duplicates while preserving order
        seen = set()
        unique_indices = []
        for idx in selected_indices:
            if idx not in seen:
                seen.add(idx)
                unique_indices.append(idx)

        return unique_indices[:grid_size]  # Ensure we don't exceed grid size

    def create_advanced_grid(self, images, rows, columns, background_color, output_scale):
        """Create an advanced grid layout with intelligent frame selection"""

        # Handle both single image and batch of images
        if len(images.shape) == 4 and images.shape[0] > 1:
            # Multiple images in batch
            image_list = [images[i] for i in range(images.shape[0])]
        else:
            # Single image or single image in batch
            if len(images.shape) == 4:
                image_list = [images[0]]
            else:
                image_list = [images]

        if not image_list:
            raise ValueError("At least one image must be provided")

        # Calculate grid size
        total_cells = rows * columns
        total_images = len(image_list)

        # Select which frames to use
        selected_indices = self.select_frame_indices(total_images, total_cells)
        selected_images = [image_list[i] for i in selected_indices]

        # Convert first image to get dimensions
        first_pil = self.tensor_to_pil(selected_images[0])
        cell_width, cell_height = first_pil.size

        # Calculate canvas dimensions
        canvas_width = cell_width * columns
        canvas_height = cell_height * rows

        # Parse background color
        bg_color = self.hex_to_rgb(background_color)

        # Create canvas
        canvas = Image.new('RGB', (canvas_width, canvas_height), bg_color)

        # Place selected images on grid
        for i, image_tensor in enumerate(selected_images):
            if i >= total_cells:
                break  # Don't exceed grid capacity

            # Calculate grid position
            row = i // columns
            col = i % columns

            # Calculate pixel position
            x = col * cell_width
            y = row * cell_height

            # Convert tensor to PIL and resize to match cell dimensions
            pil_img = self.tensor_to_pil(image_tensor)
            if pil_img.size != (cell_width, cell_height):
                pil_img = pil_img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)

            # Paste image onto canvas
            canvas.paste(pil_img, (x, y))

        # Apply output scaling if not 100%
        if output_scale != 100:
            scale_factor = output_scale / 100.0
            new_width = int(canvas_width * scale_factor)
            new_height = int(canvas_height * scale_factor)
            canvas = canvas.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert back to ComfyUI tensor format
        output_tensor = self.pil_to_tensor(canvas)

        return (output_tensor,)

class WWAA_IndexGridLayoutNode:
    """
    A ComfyUI node that creates a grid based on specified frame indices.
    Automatically calculates optimal grid dimensions and fills missing frames with background color.
    """

    DESCRIPTION = "Creates a grid layout based on specified frame indices from an image sequence. You provide comma-separated indices (e.g., '0,3,6,9,12,15') and the node automatically calculates optimal grid dimensions. Missing frames are filled with the specified background color. Returns the grid image along with computed rows and columns."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "indices": ("STRING", {
                    "default": "0,3,6,9,12,15",
                    "multiline": False,
                    "placeholder": "Enter comma-separated indices (e.g. 0,3,6,9)"
                }),
                "background_color": ("STRING", {
                    "default": "#000000",
                    "multiline": False
                }),
                "output_scale": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 200,
                    "step": 1,
                    "display": "number"
                })
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT")
    RETURN_NAMES = ("grid_image", "computed_rows", "computed_columns")
    FUNCTION = "create_index_grid"
    CATEGORY = "🪠️ WWAA/image"

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            hex_color = "000000"  # Default to black if invalid
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            return (0, 0, 0)  # Default to black if conversion fails

    def tensor_to_pil(self, tensor_image):
        """Convert ComfyUI tensor to PIL Image"""
        # ComfyUI images are typically in format [batch, height, width, channels]
        if len(tensor_image.shape) == 4:
            tensor_image = tensor_image[0]  # Take first batch

        # Convert from tensor to numpy
        numpy_image = tensor_image.cpu().numpy()

        # Ensure values are in 0-255 range
        if numpy_image.max() <= 1.0:
            numpy_image = (numpy_image * 255).astype(np.uint8)
        else:
            numpy_image = numpy_image.astype(np.uint8)

        # Convert to PIL Image
        if numpy_image.shape[2] == 3:  # RGB
            return Image.fromarray(numpy_image, 'RGB')
        elif numpy_image.shape[2] == 4:  # RGBA
            return Image.fromarray(numpy_image, 'RGBA')
        else:  # Grayscale
            return Image.fromarray(numpy_image[:,:,0], 'L').convert('RGB')

    def pil_to_tensor(self, pil_image):
        """Convert PIL Image to ComfyUI tensor format"""
        # Convert to RGB if not already
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Convert to numpy array
        numpy_image = np.array(pil_image).astype(np.float32) / 255.0

        # Convert to tensor and add batch dimension
        tensor_image = torch.from_numpy(numpy_image)[None,]

        return tensor_image

    def parse_indices(self, indices_string):
        """Parse comma-separated indices string into list of integers"""
        try:
            # Remove whitespace and split by comma
            indices_str = indices_string.strip()
            if not indices_str:
                return []

            # Split and convert to integers
            indices = []
            for idx_str in indices_str.split(','):
                idx_str = idx_str.strip()
                if idx_str:  # Skip empty strings
                    indices.append(int(idx_str))

            return sorted(list(set(indices)))  # Remove duplicates and sort
        except ValueError as e:
            raise ValueError(f"Invalid indices format. Please use comma-separated numbers (e.g. '0,3,6,9'): {e}")

    def calculate_optimal_grid_size(self, num_indices):
        """Calculate optimal grid dimensions for given number of indices"""
        if num_indices == 0:
            return 2, 2  # Minimum grid size

        if num_indices == 1:
            return 1, 1

        # Find the best rectangular grid that can fit all indices
        # Try to make it as square as possible
        sqrt_num = math.sqrt(num_indices)

        # Start with square-ish dimensions
        rows = int(math.ceil(sqrt_num))
        columns = int(math.ceil(num_indices / rows))

        # Adjust to ensure we have enough cells
        while rows * columns < num_indices:
            if rows <= columns:
                rows += 1
            else:
                columns += 1

        # Try to optimize for more square-like aspect ratio
        # Check if we can reduce one dimension
        if (rows - 1) * columns >= num_indices:
            rows -= 1
        elif rows * (columns - 1) >= num_indices:
            columns -= 1

        return rows, columns

    def create_index_grid(self, images, indices, background_color, output_scale):
        """Create a grid layout based on specified indices"""

        # Parse indices
        try:
            parsed_indices = self.parse_indices(indices)
        except ValueError as e:
            raise ValueError(str(e))

        if not parsed_indices:
            raise ValueError("At least one index must be provided")

        # Handle both single image and batch of images
        if len(images.shape) == 4 and images.shape[0] > 1:
            # Multiple images in batch
            image_list = [images[i] for i in range(images.shape[0])]
        else:
            # Single image or single image in batch
            if len(images.shape) == 4:
                image_list = [images[0]]
            else:
                image_list = [images]

        total_available_images = len(image_list)

        # Calculate optimal grid size based on number of indices
        rows, columns = self.calculate_optimal_grid_size(len(parsed_indices))
        total_cells = rows * columns

        # Get reference image for dimensions (use first available image)
        reference_image = image_list[0] if image_list else None
        if reference_image is None:
            raise ValueError("No images provided")

        first_pil = self.tensor_to_pil(reference_image)
        cell_width, cell_height = first_pil.size

        # Calculate canvas dimensions
        canvas_width = cell_width * columns
        canvas_height = cell_height * rows

        # Parse background color
        bg_color = self.hex_to_rgb(background_color)

        # Create canvas
        canvas = Image.new('RGB', (canvas_width, canvas_height), bg_color)

        # Place images based on indices
        for grid_pos, img_index in enumerate(parsed_indices):
            if grid_pos >= total_cells:
                break  # Don't exceed grid capacity

            # Calculate grid position
            row = grid_pos // columns
            col = grid_pos % columns

            # Calculate pixel position
            x = col * cell_width
            y = row * cell_height

            # Check if we have the requested image
            if img_index < total_available_images:
                # Use the specified image
                pil_img = self.tensor_to_pil(image_list[img_index])
                if pil_img.size != (cell_width, cell_height):
                    pil_img = pil_img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)

                # Paste image onto canvas
                canvas.paste(pil_img, (x, y))
            # If image doesn't exist, leave the cell blank (background color)

        # Apply output scaling if not 100%
        if output_scale != 100:
            scale_factor = output_scale / 100.0
            new_width = int(canvas_width * scale_factor)
            new_height = int(canvas_height * scale_factor)
            canvas = canvas.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Convert back to ComfyUI tensor format
        output_tensor = self.pil_to_tensor(canvas)

        return (output_tensor, rows, columns)

class WWAA_BeforeAfterSliderNode:
    """
    A ComfyUI node that creates a before/after slider animation between two images.
    Outputs a batch of images showing progressive reveal from image1 to image2.
    """

    DESCRIPTION = "Creates a before/after slider animation between two images, outputting a batch showing progressive reveal from the first image to the second. Supports four slider directions (left to right, right to left, top to bottom, bottom to top), customizable slider line width and color, multiple easing functions (linear, ease in, ease out, ease in out), and optional loop-back for seamless animations."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image1": ("IMAGE",),  # Before image
                "image2": ("IMAGE",),  # After image
                "num_frames": ("INT", {
                    "default": 10,
                    "min": 2,
                    "max": 100,
                    "step": 1,
                    "display": "number"
                }),
                "slider_direction": (["left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"], {
                    "default": "left_to_right"
                }),
                "slider_width": ("INT", {
                    "default": 3,
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "display": "number",
                    "tooltip": "Width of the slider line in pixels (0 for no line)"
                }),
                "slider_color": ("STRING", {
                    "default": "#FFFFFF",
                    "tooltip": "Hex color for slider line (e.g., #FFFFFF for white)"
                }),
                "ease_function": (["linear", "ease_in", "ease_out", "ease_in_out"], {
                    "default": "linear"
                }),
                "loop_back": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "If True, creates a loop by sliding back to the before image using the same number of frames"
                })
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "create_slider_animation"
    CATEGORY = "🪠️ WWAA/image"

    def ease_linear(self, t):
        return t

    def ease_in(self, t):
        return t * t

    def ease_out(self, t):
        return 1 - (1 - t) * (1 - t)

    def ease_in_out(self, t):
        return 3 * t * t - 2 * t * t * t

    def get_easing_function(self, ease_type):
        """Get the easing function based on type"""
        easing_functions = {
            "linear": self.ease_linear,
            "ease_in": self.ease_in,
            "ease_out": self.ease_out,
            "ease_in_out": self.ease_in_out
        }
        return easing_functions.get(ease_type, self.ease_linear)

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (255, 255, 255)  # Default to white if invalid

    def resize_images_to_match(self, img1_tensor, img2_tensor):
        """Resize both images to match dimensions (use larger dimensions)"""
        # Convert tensors to PIL for easier manipulation
        img1_pil = self.tensor_to_pil(img1_tensor[0])
        img2_pil = self.tensor_to_pil(img2_tensor[0])

        # Get dimensions
        w1, h1 = img1_pil.size
        w2, h2 = img2_pil.size

        # Use the larger dimensions
        target_width = max(w1, w2)
        target_height = max(h1, h2)

        # Resize both images
        img1_resized = img1_pil.resize((target_width, target_height), Image.Resampling.LANCZOS)
        img2_resized = img2_pil.resize((target_width, target_height), Image.Resampling.LANCZOS)

        return img1_resized, img2_resized

    def tensor_to_pil(self, tensor):
        """Convert tensor to PIL Image"""
        # Handle tensor format: [H, W, C] with values in [0, 1]
        numpy_image = tensor.cpu().numpy()
        if numpy_image.max() <= 1.0:
            numpy_image = (numpy_image * 255).astype(np.uint8)
        return Image.fromarray(numpy_image)

    def pil_to_tensor(self, pil_img):
        """Convert PIL Image to tensor format expected by ComfyUI"""
        numpy_image = np.array(pil_img).astype(np.float32) / 255.0
        return torch.from_numpy(numpy_image)

    def create_slider_frame(self, img1_pil, img2_pil, progress, direction, slider_width, slider_color):
        """Create a single frame of the slider animation"""
        width, height = img1_pil.size

        # Create result image starting with image1
        result = img1_pil.copy()

        # Calculate split position based on direction and progress
        if direction == "left_to_right":
            split_x = int(width * progress)
            # Paste image2 on the right side of the split
            if split_x < width:
                crop_box = (split_x, 0, width, height)
                img2_crop = img2_pil.crop(crop_box)
                result.paste(img2_crop, (split_x, 0))

            # Draw slider line
            if slider_width > 0 and split_x > 0 and split_x < width:
                draw = ImageDraw.Draw(result)
                line_start = max(0, split_x - slider_width // 2)
                line_end = min(width, split_x + slider_width // 2)
                rgb_color = self.hex_to_rgb(slider_color)
                draw.rectangle([line_start, 0, line_end, height], fill=rgb_color)

        elif direction == "right_to_left":
            split_x = int(width * (1 - progress))
            # Paste image2 on the left side of the split
            if split_x > 0:
                crop_box = (0, 0, split_x, height)
                img2_crop = img2_pil.crop(crop_box)
                result.paste(img2_crop, (0, 0))

            # Draw slider line
            if slider_width > 0 and split_x > 0 and split_x < width:
                draw = ImageDraw.Draw(result)
                line_start = max(0, split_x - slider_width // 2)
                line_end = min(width, split_x + slider_width // 2)
                rgb_color = self.hex_to_rgb(slider_color)
                draw.rectangle([line_start, 0, line_end, height], fill=rgb_color)

        elif direction == "top_to_bottom":
            split_y = int(height * progress)
            # Paste image2 on the bottom side of the split
            if split_y < height:
                crop_box = (0, split_y, width, height)
                img2_crop = img2_pil.crop(crop_box)
                result.paste(img2_crop, (0, split_y))

            # Draw slider line
            if slider_width > 0 and split_y > 0 and split_y < height:
                draw = ImageDraw.Draw(result)
                line_start = max(0, split_y - slider_width // 2)
                line_end = min(height, split_y + slider_width // 2)
                rgb_color = self.hex_to_rgb(slider_color)
                draw.rectangle([0, line_start, width, line_end], fill=rgb_color)

        elif direction == "bottom_to_top":
            split_y = int(height * (1 - progress))
            # Paste image2 on the top side of the split
            if split_y > 0:
                crop_box = (0, 0, width, split_y)
                img2_crop = img2_pil.crop(crop_box)
                result.paste(img2_crop, (0, 0))

            # Draw slider line
            if slider_width > 0 and split_y > 0 and split_y < height:
                draw = ImageDraw.Draw(result)
                line_start = max(0, split_y - slider_width // 2)
                line_end = min(height, split_y + slider_width // 2)
                rgb_color = self.hex_to_rgb(slider_color)
                draw.rectangle([0, line_start, width, line_end], fill=rgb_color)

        return result

    def create_slider_animation(self, image1, image2, num_frames, slider_direction,
                              slider_width, slider_color, ease_function, loop_back):
        """Main function to create the slider animation"""

        # Resize images to match
        img1_pil, img2_pil = self.resize_images_to_match(image1, image2)

        # Get easing function
        easing_func = self.get_easing_function(ease_function)

        # Generate frames
        frames = []

        # Calculate total frames - double if looping back
        total_frames = num_frames * 2 if loop_back else num_frames

        for i in range(total_frames):
            if loop_back and i < num_frames:
                # First half: slide from before to after
                linear_progress = i / (num_frames - 1) if num_frames > 1 else 0
                eased_progress = easing_func(linear_progress)
            elif loop_back and i >= num_frames:
                # Second half: slide from after back to before
                reverse_i = total_frames - 1 - i  # Reverse the index
                linear_progress = reverse_i / (num_frames - 1) if num_frames > 1 else 0
                eased_progress = easing_func(linear_progress)
            else:
                # Normal single direction animation
                linear_progress = i / (num_frames - 1) if num_frames > 1 else 0
                eased_progress = easing_func(linear_progress)

            # Create frame
            frame = self.create_slider_frame(
                img1_pil, img2_pil, eased_progress,
                slider_direction, slider_width, slider_color
            )

            # Convert back to tensor
            frame_tensor = self.pil_to_tensor(frame)
            frames.append(frame_tensor)

        # Stack frames into batch
        batch_tensor = torch.stack(frames, dim=0)

        return (batch_tensor,)

class WWAA_ImageSwitcher:
    """
    A ComfyUI node that takes two single images and outputs them with optional switching.
    When switch is False: Output A = Input A, Output B = Input B
    When switch is True: Output A = Input B, Output B = Input A
    """

    DESCRIPTION = "Routes two input images to two output ports with optional switching. When switch is False, image A goes to output X and image B goes to output Y (pass-through). When switch is True, the outputs are swapped so image A goes to output Y and image B goes to output X. Useful for conditional image routing in workflows. Only accepts single images, not batches."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
                "switch": ("BOOLEAN", {"default": False})
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("output_x", "output_y")
    FUNCTION = "switch_images"
    CATEGORY = "🪠️ WWAA/image"

    def switch_images(self, image_a, image_b, switch):
        """Switch or pass through images based on boolean switch"""

        # Validate that inputs are single images (batch size of 1)
        if image_a.shape[0] != 1:
            raise ValueError(f"image_a must be a single image (batch size 1), got batch size {image_a.shape[0]}")
        if image_b.shape[0] != 1:
            raise ValueError(f"image_b must be a single image (batch size 1), got batch size {image_b.shape[0]}")

        if switch:
            # Swap: A -> Y, B -> X
            output_x = image_b
            output_y = image_a
        else:
            # Pass through: A -> X, B -> Y
            output_x = image_a
            output_y = image_b

        return (output_x, output_y)

class WWAA_SlicedArt:
    """
    A ComfyUI node that creates a mirrored 2x2 grid from a single image.
    Can either resize input to 0.5x on original canvas, or keep original size on 2x canvas.
    Then creates a second output by slicing the canvas into vertical strips and rearranging them.
    Finally creates a third output by slicing Pass1Output into horizontal strips and rearranging.
    All operations are performed on GPU using PyTorch tensors.
    """

    DESCRIPTION = "Creates a kaleidoscope-like effect by arranging a single image in a 2x2 grid with different orientations. DoubleSize=False: resizes input to 0.5x on original canvas. DoubleSize=True: keeps original size on 2x canvas. First output (flippedOutput) is the mirrored 2x2 grid. Second output (Pass1Output) slices the grid into equal vertical strips and rearranges them in order: 1,N,2,N-1,3,N-2... Third output (FinalOutput) takes Pass1Output, slices into horizontal strips, and rearranges in the same pattern. All operations performed on GPU."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "num_slices": ("INT", {
                    "default": 20,
                    "min": 20,
                    "max": 80,
                    "step": 2,
                    "display": "number"
                }),
                "DoubleSize": ("BOOLEAN", {
                    "default": False
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("flippedOutput", "Pass1Output", "FinalOutput")
    FUNCTION = "create_sliced_art"
    CATEGORY = "🪠️ WWAA/image"

    def create_sliced_art(self, image, num_slices=20, DoubleSize=False):
        """Create a 2x2 mirrored grid from a single image using GPU tensors"""

        # Validate input is a single image
        if image.shape[0] != 1:
            raise ValueError(f"Input must be a single image (batch size 1), got batch size {image.shape[0]}")

        # Get device from input tensor
        device = image.device
        
        # Remove batch dimension for easier manipulation
        # Shape: [batch=1, height, width, channels] -> [height, width, channels]
        img = image[0]
        
        original_height, original_width, channels = img.shape

        if DoubleSize:
            # Keep image at original size, create canvas 2x the size
            img_to_place = img
            canvas_height = original_height * 2
            canvas_width = original_width * 2
            cell_height = original_height
            cell_width = original_width
        else:
            # Resize image to 0.5x (half size), canvas stays original size
            # Need to permute to [channels, height, width] for interpolate
            img_resized = img.permute(2, 0, 1).unsqueeze(0)  # [1, C, H, W]
            img_resized = F.interpolate(
                img_resized,
                size=(original_height // 2, original_width // 2),
                mode='bilinear',
                align_corners=False
            )
            img_to_place = img_resized.squeeze(0).permute(1, 2, 0)  # Back to [H/2, W/2, C]
            canvas_height = original_height
            canvas_width = original_width
            cell_height = original_height // 2
            cell_width = original_width // 2

        # Create canvas with calculated dimensions
        canvas = torch.zeros((canvas_height, canvas_width, channels), dtype=image.dtype, device=device)

        # Top-left: Original image
        canvas[0:cell_height, 0:cell_width, :] = img_to_place

        # Top-right: Horizontally flipped
        # Flip along width dimension (dim=1)
        flipped_horizontal = torch.flip(img_to_place, dims=[1])
        canvas[0:cell_height, cell_width:cell_width*2, :] = flipped_horizontal

        # Bottom-left: Vertically flipped
        # Flip along height dimension (dim=0)
        flipped_vertical = torch.flip(img_to_place, dims=[0])
        canvas[cell_height:cell_height*2, 0:cell_width, :] = flipped_vertical

        # Bottom-right: Both horizontally and vertically flipped
        # Flip along both dimensions
        flipped_both = torch.flip(img_to_place, dims=[0, 1])
        canvas[cell_height:cell_height*2, cell_width:cell_width*2, :] = flipped_both

        # Add batch dimension back for first output
        flipped_output = canvas.unsqueeze(0)

        # Now create Pass1Output by slicing and rearranging
        canvas_height, canvas_width, _ = canvas.shape
        
        # Adjust canvas width to be divisible by num_slices if needed
        adjusted_width = (canvas_width // num_slices) * num_slices
        
        if adjusted_width != canvas_width:
            # Resize canvas to make width divisible by num_slices
            # Need to permute to [channels, height, width] for interpolate
            canvas_resized = canvas.permute(2, 0, 1).unsqueeze(0)  # [1, C, H, W]
            canvas_resized = F.interpolate(
                canvas_resized,
                size=(canvas_height, adjusted_width),
                mode='bilinear',
                align_corners=False
            )
            canvas = canvas_resized.squeeze(0).permute(1, 2, 0)  # Back to [H, W, C]
            canvas_width = adjusted_width
        
        # Calculate slice width
        slice_width = canvas_width // num_slices
        
        # Create list to hold slices
        slices = []
        for i in range(num_slices):
            start_x = i * slice_width
            end_x = start_x + slice_width
            slice_tensor = canvas[:, start_x:end_x, :]
            slices.append(slice_tensor)
        
        # Rearrange slices in pattern: 1,N,2,N-1,3,N-2...
        # (using 0-indexing: 0,N-1,1,N-2,2,N-3...)
        rearranged_slices = []
        left_idx = 0
        right_idx = num_slices - 1
        
        while left_idx <= right_idx:
            if left_idx == right_idx:
                # Middle slice (only happens if odd number of slices)
                rearranged_slices.append(slices[left_idx])
            else:
                # Add from left, then from right
                rearranged_slices.append(slices[left_idx])
                rearranged_slices.append(slices[right_idx])
            left_idx += 1
            right_idx -= 1
        
        # Concatenate all rearranged slices horizontally
        pass1_canvas = torch.cat(rearranged_slices, dim=1)
        
        # Add batch dimension for second output
        pass1_output = pass1_canvas.unsqueeze(0)

        # Now create FinalOutput by slicing horizontally (without rotation)
        # Use pass1_canvas directly, no rotation needed
        # Shape: [H, W, C]
        final_canvas_input = pass1_canvas
        
        final_height, final_width, _ = final_canvas_input.shape
        
        # Adjust canvas height to be divisible by num_slices if needed
        adjusted_final_height = (final_height // num_slices) * num_slices
        
        if adjusted_final_height != final_height:
            # Resize to make height divisible by num_slices
            final_resized = final_canvas_input.permute(2, 0, 1).unsqueeze(0)  # [1, C, H, W]
            final_resized = F.interpolate(
                final_resized,
                size=(adjusted_final_height, final_width),
                mode='bilinear',
                align_corners=False
            )
            final_canvas_input = final_resized.squeeze(0).permute(1, 2, 0)  # Back to [H, W, C]
            final_height = adjusted_final_height
        
        # Calculate slice height for horizontal slicing
        final_slice_height = final_height // num_slices
        
        # Create list to hold horizontal slices
        horizontal_slices = []
        for i in range(num_slices):
            start_y = i * final_slice_height
            end_y = start_y + final_slice_height
            slice_tensor = final_canvas_input[start_y:end_y, :, :]  # Slice horizontally
            horizontal_slices.append(slice_tensor)
        
        # Rearrange horizontal slices in the same pattern
        final_rearranged_slices = []
        left_idx = 0
        right_idx = num_slices - 1
        
        while left_idx <= right_idx:
            if left_idx == right_idx:
                # Middle slice
                final_rearranged_slices.append(horizontal_slices[left_idx])
            else:
                # Add from top, then from bottom
                final_rearranged_slices.append(horizontal_slices[left_idx])
                final_rearranged_slices.append(horizontal_slices[right_idx])
            left_idx += 1
            right_idx -= 1
        
        # Concatenate all final rearranged slices vertically (dim=0 for height)
        final_canvas = torch.cat(final_rearranged_slices, dim=0)
        
        # Add batch dimension for third output
        final_output = final_canvas.unsqueeze(0)

        return (flipped_output, pass1_output, final_output)

class WWAA_JPEGPreview:
    """
    A ComfyUI node that displays images converted to JPEG format with file size information.
    Shows the image preview and displays dimensions and file size below the image.
    """

    DESCRIPTION = "Displays images as JPEG format with file size information. Converts input image to JPEG and shows dimensions (width x height) and file size in KB. Quality parameter controls JPEG compression level (1-100, higher is better quality but larger file size)."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "quality": ("INT", {
                    "default": 70,
                    "min": 1,
                    "max": 100,
                    "step": 5,
                    "display": "number"
                }),
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "preview_jpeg"
    CATEGORY = "🪠️ WWAA/image"

    def preview_jpeg(self, image, quality):
        """Convert image to JPEG and return preview data with size information"""
        import io
        
        # Get the first image from batch
        if len(image.shape) == 4:
            img_tensor = image[0]
        else:
            img_tensor = image
        
        # Convert tensor to PIL Image
        numpy_image = img_tensor.cpu().numpy()
        if numpy_image.max() <= 1.0:
            numpy_image = (numpy_image * 255).astype(np.uint8)
        else:
            numpy_image = numpy_image.astype(np.uint8)
        
        pil_image = Image.fromarray(numpy_image, 'RGB')
        
        # Get dimensions
        width, height = pil_image.size
        
        # Convert to JPEG in memory to get file size
        jpeg_buffer = io.BytesIO()
        pil_image.save(jpeg_buffer, format='JPEG', quality=quality)
        jpeg_size_bytes = jpeg_buffer.tell()
        jpeg_size_kb = jpeg_size_bytes / 1024.0
        
        # Save to temp file for ComfyUI to display
        from pathlib import Path
        import hashlib
        import time
        
        # Create a unique filename based on image content and timestamp
        jpeg_buffer.seek(0)
        image_hash = hashlib.md5(jpeg_buffer.read()).hexdigest()
        timestamp = int(time.time() * 1000)
        
        # Use ComfyUI's temp directory
        temp_dir = folder_paths.get_temp_directory()
        filename = f"jpeg_preview_{image_hash}_{timestamp}.jpg"
        filepath = os.path.join(temp_dir, filename)
        
        # Save JPEG to temp file
        jpeg_buffer.seek(0)
        with open(filepath, 'wb') as f:
            f.write(jpeg_buffer.read())
        
        # Prepare results for UI
        results = {
            "ui": {
                "images": [{
                    "filename": filename,
                    "subfolder": "",
                    "type": "temp",
                    "format": "JPEG"
                }],
                "image_info": [{
                    "width": width,
                    "height": height,
                    "size_kb": f"{jpeg_size_kb:.2f}",
                    "quality": quality
                }]
            }
        }
        
        return results

class WWAA_SaveJPEG:
    """
    A ComfyUI node that saves images as JPEG files with auto-incrementing numbering.
    Supports subfolder creation and custom filename prefixes.
    """

    DESCRIPTION = "Saves images as JPEG files to ComfyUI's output folder with auto-incrementing numbering. Supports subfolder handling (e.g., 'subfolder/filename' creates subfolder if needed). Also supports date formatting with %date:format% syntax (e.g., '%date:yyyy-MM-dd%/myfile' creates folder '2025-12-13/myfile_00001.jpg'). Files are saved as prefix_00001.jpg, prefix_00002.jpg, etc., with numbering based on existing files in the target directory. Quality parameter controls JPEG compression (1-100)."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {
                    "default": "ComfyUI",
                    "multiline": False
                }),
                "quality": ("INT", {
                    "default": 95,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "display": "number"
                }),
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "save_images"
    CATEGORY = "🪠️ WWAA/image"

    def parse_date_format(self, text):
        """
        Parse and replace %date:format% patterns with actual dates.
        Supports formats like %date:yyyy-MM-dd%, %date:yyyyMMdd%, etc.
        """
        from datetime import datetime
        import re
        
        # Find all %date:format% patterns
        pattern = r'%date:([^%]+)%'
        matches = re.finditer(pattern, text)
        
        result = text
        for match in matches:
            full_match = match.group(0)  # e.g., "%date:yyyy-MM-dd%"
            date_format = match.group(1)  # e.g., "yyyy-MM-dd"
            
            # Convert ComfyUI date format to Python strftime format
            # Common mappings:
            # yyyy -> %Y (4-digit year)
            # yy -> %y (2-digit year)
            # MM -> %m (2-digit month)
            # dd -> %d (2-digit day)
            # HH -> %H (24-hour)
            # hh -> %I (12-hour)
            # mm -> %M (minutes)
            # ss -> %S (seconds)
            
            python_format = date_format
            python_format = python_format.replace('yyyy', '%Y')
            python_format = python_format.replace('yy', '%y')
            python_format = python_format.replace('MM', '%m')
            python_format = python_format.replace('dd', '%d')
            python_format = python_format.replace('HH', '%H')
            python_format = python_format.replace('hh', '%I')
            python_format = python_format.replace('mm', '%M')
            python_format = python_format.replace('ss', '%S')
            
            # Get current date/time and format it
            current_date = datetime.now()
            formatted_date = current_date.strftime(python_format)
            
            # Replace in result
            result = result.replace(full_match, formatted_date)
        
        return result

    def get_next_counter(self, directory, prefix):
        """
        Find the highest counter number for files matching the prefix pattern.
        Returns the next available counter number.
        """
        existing_files = []
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.startswith(prefix) and filename.endswith('.jpg'):
                    # Extract number from filename like "prefix_123.jpg"
                    try:
                        # Remove prefix and .jpg extension
                        number_part = filename[len(prefix):-4]
                        # Remove leading underscore if present
                        if number_part.startswith('_'):
                            number_part = number_part[1:]
                        # Try to parse as integer
                        counter = int(number_part)
                        existing_files.append(counter)
                    except ValueError:
                        # Skip files that don't match the expected pattern
                        continue
        
        # Return next counter (highest + 1, or 1 if no files found)
        return max(existing_files) + 1 if existing_files else 1

    def save_images(self, images, filename_prefix, quality):
        """Save images as JPEG files with auto-incrementing numbering"""
        
        # Parse date formats in filename_prefix
        filename_prefix = self.parse_date_format(filename_prefix)
        
        # Get ComfyUI's output directory
        output_dir = folder_paths.get_output_directory()
        
        # Handle subfolder in filename_prefix
        # e.g., "wan/ComfyUI" -> subfolder="wan", prefix="ComfyUI"
        if '/' in filename_prefix or '\\' in filename_prefix:
            # Normalize path separators
            filename_prefix = filename_prefix.replace('\\', '/')
            parts = filename_prefix.split('/')
            subfolder = '/'.join(parts[:-1])
            prefix = parts[-1]
            
            # Create full directory path
            full_dir = os.path.join(output_dir, subfolder)
            
            # Create subfolder if it doesn't exist
            os.makedirs(full_dir, exist_ok=True)
        else:
            # No subfolder, save directly to output directory
            full_dir = output_dir
            prefix = filename_prefix
            subfolder = ""
        
        # Get the starting counter based on existing files
        counter = self.get_next_counter(full_dir, prefix)
        
        # List to store saved file information
        saved_files = []
        
        # Process each image in the batch
        for img_tensor in images:
            # Convert tensor to PIL Image
            numpy_image = img_tensor.cpu().numpy()
            if numpy_image.max() <= 1.0:
                numpy_image = (numpy_image * 255).astype(np.uint8)
            else:
                numpy_image = numpy_image.astype(np.uint8)
            
            pil_image = Image.fromarray(numpy_image, 'RGB')
            
            # Generate filename with counter
            filename = f"{prefix}_{counter:05d}.jpg"
            filepath = os.path.join(full_dir, filename)
            
            # Save as JPEG
            pil_image.save(filepath, format='JPEG', quality=quality)
            
            # Get file size
            file_size_bytes = os.path.getsize(filepath)
            file_size_kb = file_size_bytes / 1024.0
            
            # Store file info
            saved_files.append({
                "filename": filename,
                "subfolder": subfolder,
                "path": filepath,
                "size_kb": f"{file_size_kb:.2f}",
                "counter": counter
            })
            
            # Increment counter for next image
            counter += 1
        
        # Prepare results for UI
        results = {
            "ui": {
                "images": [
                    {
                        "filename": info["filename"],
                        "subfolder": info["subfolder"],
                        "type": "output"
                    }
                    for info in saved_files
                ]
            }
        }
        
        # Print summary to console
        print(f"Saved {len(saved_files)} JPEG image(s) to {full_dir}")
        for info in saved_files:
            print(f"  - {info['filename']} ({info['size_kb']} KB)")
        
        return results

class WWAA_ImageDimensionCalculator:
    """
    A ComfyUI node that calculates upscaled image dimensions based on a scale factor.
    Ensures output dimensions are multiples of 64 for compatibility with AI models.
    """

    DESCRIPTION = "Calculates upscaled image dimensions from a single input image based on a decimal scale factor. Automatically rounds the resulting width and height to the nearest multiple of the specified factor (16, 32, or 64) while preserving the original aspect ratio. Does not actually upscale the image, only outputs the calculated integer dimensions."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "scale_factor": ("FLOAT", {
                    "default": 1.5,
                    "min": 0.1,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                }),
                "multiple_of": ([16, 32, 64], {
                    "default": 64
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "calculate_dimensions"
    CATEGORY = "🪠️ WWAA/image"

    def round_to_multiple(self, value, multiple):
        """Round a value to the nearest multiple of the specified factor"""
        return int(round(value / multiple) * multiple)

    def calculate_dimensions(self, image, scale_factor, multiple_of):
        """Calculate upscaled dimensions ensuring multiples of specified factor while preserving aspect ratio"""
        
        # Validate input is a single image
        if image.shape[0] != 1:
            raise ValueError(f"Input must be a single image (batch size 1), got batch size {image.shape[0]}")
        
        # Get current dimensions
        # Image shape is [batch, height, width, channels]
        current_height = image.shape[1]
        current_width = image.shape[2]
        
        # Calculate original aspect ratio
        aspect_ratio = current_width / current_height
        
        # Calculate scaled dimensions
        scaled_width = current_width * scale_factor
        scaled_height = current_height * scale_factor
        
        # Round width to nearest multiple first
        final_width = self.round_to_multiple(scaled_width, multiple_of)
        
        # Calculate height based on aspect ratio, then round to multiple
        calculated_height = final_width / aspect_ratio
        final_height = self.round_to_multiple(calculated_height, multiple_of)
        
        # Verify and adjust if aspect ratio drifted too much
        # Recalculate to ensure we stay close to original aspect ratio
        new_aspect_ratio = final_width / final_height
        aspect_ratio_error = abs(new_aspect_ratio - aspect_ratio) / aspect_ratio
        
        # If error is significant, try adjusting width instead
        if aspect_ratio_error > 0.05:  # More than 5% error
            final_height = self.round_to_multiple(scaled_height, multiple_of)
            calculated_width = final_height * aspect_ratio
            final_width = self.round_to_multiple(calculated_width, multiple_of)
        
        # Ensure minimum dimensions (at least the multiple value)
        final_width = max(multiple_of, final_width)
        final_height = max(multiple_of, final_height)
        
        # Calculate final aspect ratio for reporting
        final_aspect_ratio = final_width / final_height
        
        print(f"Original: {current_width}x{current_height} (aspect ratio: {aspect_ratio:.4f})")
        print(f"Scale factor: {scale_factor}x")
        print(f"Multiple of: {multiple_of}")
        print(f"Calculated: {scaled_width:.2f}x{scaled_height:.2f}")
        print(f"Final (rounded to {multiple_of}): {final_width}x{final_height} (aspect ratio: {final_aspect_ratio:.4f})")
        print(f"Aspect ratio preserved: {abs(final_aspect_ratio - aspect_ratio) < 0.001}")
        
        return (final_width, final_height)

class WWAA_ImageDimensionSize:
    """
    A ComfyUI node that detects and outputs either the longest or shortest edge of an image.
    Compares width and height to determine which is longer/shorter.
    """

    DESCRIPTION = "Analyzes image dimensions and outputs either the longest or shortest edge value, plus an upscaled value multiplied by the given multiplier. Compares the width and height of the input image and returns the selected edge as an integer. Useful for conditional scaling or determining image orientation."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "edge": (["long", "short"], {
                    "default": "long"
                }),
                "multiplier": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10,
                    "step": 1,
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("edge_value", "upscaled_value",)
    FUNCTION = "detect_edge"
    CATEGORY = "🪠️ WWAA/image"

    def detect_edge(self, image, edge, multiplier):
        """Detect and return either the longest or shortest edge of the image, plus an upscaled value"""
        
        # Image shape is [batch, height, width, channels]
        height = image.shape[1]
        width = image.shape[2]
        
        if edge == "long":
            edge_value = max(width, height)
            edge_type = "longest"
        else:  # edge == "short"
            edge_value = min(width, height)
            edge_type = "shortest"
        
        upscaled_value = edge_value * multiplier

        print(f"Image dimensions: {width}x{height}")
        print(f"Detected {edge_type} edge: {edge_value}")
        print(f"Upscaled value ({multiplier}x): {upscaled_value}")
        
        return (edge_value, upscaled_value,)
