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

class WWAA_VideoResolution:
    """
    A ComfyUI node that provides standard video resolutions from 480p to 4K.
    Outputs width and height as integers, with support for various aspect ratios and orientations.
    All values are based on selected model multiplier for compatibility.
    """

    DESCRIPTION = "Provides standard video resolutions from 480p to 4K with support for multiple aspect ratios (16:9, 21:9, 2:1, 4:3, 3:2, 4:5, 1:1) and orientations. Outputs width and height as integers. Resolution multipliers are model-specific for compatibility with different video generation models."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": ([
                    "LTX2/Wan2.x",
                    "Q25xx",
                    "Flux.2",
                    "Z-Image-Turbo",
                ], {"default": "Z-Image-Turbo"}),
                "resolution": ([
                    "480p",
                    "720p",
                    "1080p",
                    "1440p",
                    "4K",
                ], {"default": "1080p"}),
                "aspect_ratio": ([
                    "16:9 (Widescreen)",
                    "21:9 (Ultrawide)",
                    "2:1 (Univisium)",
                    "4:3 (Standard)",
                    "3:2 (Classic)",
                    "4:5 (Portrait)",
                    "1:1 (Square)",
                ], {"default": "16:9 (Widescreen)"}),
                "orientation": (["Horizontal", "Vertical"], {"default": "Horizontal"}),
                "use_custom": ("BOOLEAN", {"default": False}),
                "custom_width": ("INT", {
                    "default": 1024,
                    "min": 256,
                    "max": 8192,
                    "step": 64
                }),
                "custom_height": ("INT", {
                    "default": 1024,
                    "min": 256,
                    "max": 8192,
                    "step": 64
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "get_resolution"
    CATEGORY = "🪠️ WWAA/Video"

    def get_resolution(self, model_type, resolution, aspect_ratio, orientation, use_custom, custom_width, custom_height):
        """
        Get the width and height for the selected resolution and aspect ratio, or use custom values.

        Args:
            model_type (str): Selected model type (determines multiplier)
            resolution (str): Selected resolution preset (480p-4K)
            aspect_ratio (str): Selected aspect ratio
            orientation (str): "Horizontal" or "Vertical"
            use_custom (bool): If True, use custom width and height
            custom_width (int): Custom width (only used when use_custom is True)
            custom_height (int): Custom height (only used when use_custom is True)

        Returns:
            tuple: (width, height) as integers, multiples based on model type
        """
        # If use_custom is enabled, return custom dimensions directly
        if use_custom:
            return (custom_width, custom_height)

        # Model-specific multipliers
        model_multipliers = {
            "LTX2/Wan2.x": 32,
            "Q25xx": 112,
            "Flux.2": 16,
            "Z-Image-Turbo": 64,
        }

        multiplier = model_multipliers[model_type]

        # Base heights for each resolution tier (will be adjusted to model multiplier)
        base_heights = {
            "480p": 512,
            "720p": 704,
            "1080p": 1088,
            "1440p": 1408,
            "4K": 2176,
        }

        # Aspect ratio multipliers
        # Format: (width_multiplier, height_multiplier)
        aspect_ratios = {
            "16:9 (Widescreen)": (16, 9),
            "21:9 (Ultrawide)": (21, 9),
            "2:1 (Univisium)": (2, 1),
            "4:3 (Standard)": (4, 3),
            "3:2 (Classic)": (3, 2),
            "4:5 (Portrait)": (4, 5),
            "1:1 (Square)": (1, 1),
        }

        base_height = base_heights[resolution]
        width_ratio, height_ratio = aspect_ratios[aspect_ratio]

        # Calculate width based on aspect ratio
        # We want: width/height = width_ratio/height_ratio
        # So: width = height * (width_ratio/height_ratio)
        target_width = base_height * width_ratio / height_ratio

        # Round to nearest multiple of model multiplier
        width = round(target_width / multiplier) * multiplier
        height = round(base_height / multiplier) * multiplier

        # For some aspect ratios, adjust for better proportions
        if aspect_ratio == "1:1 (Square)":
            # For square, use the base height for both dimensions
            width = height
        elif aspect_ratio == "4:5 (Portrait)":
            # For portrait 4:5, calculate from height to maintain better proportions
            width = round((height * 4 / 5) / multiplier) * multiplier

        # Swap if vertical orientation
        if orientation == "Vertical":
            width, height = height, width

        return (width, height)
