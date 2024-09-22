import math, string, re
import numpy as np
from PIL import Image
import torch

debug = False

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
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "dither_type": (["Floyd-Steinberg", "Atkinson", "Ordered"],),
                "contrast": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "scale": ("INT", {"default": 1, "min": 0, "max": 10, "step": 1}),
                "threshold": ("INT", {"default": 128, "min": 0, "max": 255, "step": 1}),
                "invert": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "apply_dither"

    CATEGORY = "image/postprocessing"
    
    def distributeError(self, img, x, y, error, m):
        h, w = img.shape
        if x + 1 < w:
            img[y, x + 1] = np.clip(img[y, x + 1] + error * m[0], 0, 255)
        if y + 1 < h:
            if x > 0:
                img[y + 1, x - 1] = np.clip(img[y + 1, x - 1] + error * m[1], 0, 255)
            img[y + 1, x] = np.clip(img[y + 1, x] + error * m[2], 0, 255)
            if x + 1 < w:
                img[y + 1, x + 1] = np.clip(img[y + 1, x + 1] + error * m[3], 0, 255)

    def apply_dither(self, image, dither_type, contrast, scale, threshold, invert):
        print(f"Input image shape: {image.shape}")
        
        # Process each image in the batch
        dithered_images = []
        for img in image:
            # Convert the tensor image to numpy array
            img = img.cpu().numpy()
            print(f"Single image shape: {img.shape}")
            
            # Convert to grayscale
            img_gray = np.dot(img[..., :3], [0.2989, 0.5870, 0.1140])
            
            # Scale to 0-255 range and convert to float32 for calculations
            img_gray = (img_gray * 255).astype(np.float32)
            
            print(f"Grayscale image shape: {img_gray.shape}")
            
            # Apply contrast
            img_gray = np.clip((img_gray - 128) * contrast + 128, 0, 255)

            h, w = img_gray.shape
            
            if dither_type in ["Floyd-Steinberg", "Atkinson"]:
                for y in range(h):
                    for x in range(w):
                        old_pixel = img_gray[y, x]
                        new_pixel = 255 if old_pixel > threshold else 0
                        img_gray[y, x] = new_pixel
                        error = (old_pixel - new_pixel) / scale

                        if dither_type == "Floyd-Steinberg":
                            self.distributeError(img_gray, x, y, error, [7/16, 3/16, 5/16, 1/16])
                        elif dither_type == "Atkinson":
                            self.distributeError(img_gray, x, y, error / 8, [1, 1, 1, 1])
                            if x < w - 2:
                                img_gray[y, x + 2] = np.clip(img_gray[y, x + 2] + error / 8, 0, 255)
                            if y < h - 2:
                                img_gray[y + 2, x] = np.clip(img_gray[y + 2, x] + error / 8, 0, 255)
            elif dither_type == "Ordered":
                threshold_map = np.array([
                    [15, 135, 45, 165],
                    [195, 75, 225, 105],
                    [60, 180, 30, 150],
                    [240, 120, 210, 90]
                ]) / 255.0  # Normalize the threshold map

                # Create a threshold map of the same size as the image
                threshold_map_full = np.tile(threshold_map, (h // 4 + 1, w // 4 + 1))[:h, :w]
                
                # Apply scaling to the threshold map
                threshold_map_scaled = threshold_map_full * (scale / 10)

                # Apply ordered dithering
                img_gray = np.where(img_gray / 255.0 > threshold_map_scaled, 255, 0)

            # Clip values to ensure they're in the 0-255 range and convert back to uint8
            img_gray = np.clip(img_gray, 0, 255).astype(np.uint8)
            
            # Invert the image if the invert option is True
            if invert:
                img_gray = 255 - img_gray

            # Convert back to RGB
            img_dithered = np.stack([img_gray, img_gray, img_gray], axis=-1)
            
            # Convert back to tensor and normalize to 0-1 range
            dithered_image = torch.from_numpy(img_dithered).float() / 255.0
            dithered_images.append(dithered_image)

        # Stack all processed images back into a batch
        result = torch.stack(dithered_images)
        print(f"Output image shape: {result.shape}")
        return (result,)


       
# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
WWAA_CLASS_MAPPINGS = {
    "WWAA-LineCount": WWAA_LineCount,
    "WWAA-BuildString": WWAA_BuildString,
    "WWAA_DitherNode": WWAA_DitherNode,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
WWAA_DISPLAY_NAME_MAPPINGS = {
    "WWAA-LineCount": "🪠️ WWAA LineCount",
    "WWAA-BuildString": "🪠️ WWAA JoinString",
    "WWAA_DitherNode": "🪠️ WWAA Dither Image"
}
