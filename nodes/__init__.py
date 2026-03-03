# Import all image nodes
from .image_nodes import (
    WWAA_ImageLoader,
    WWAA_DitherNode,
    WWAA_GBCamera,
    WWAA_GridLayoutNode,
    WWAA_AdvancedGridLayoutNode,
    WWAA_IndexGridLayoutNode,
    WWAA_BeforeAfterSliderNode,
    WWAA_ImageSwitcher,
    WWAA_SlicedArt,
    WWAA_JPEGPreview,
    WWAA_SaveJPEG,
    WWAA_ImageDimensionCalculator,
    WWAA_ImageDimensionSize,
)

# Import all text nodes
from .text_nodes import (
    WWAA_NumberRangeAsString,
    WWAA_LineCount,
    WWAA_BuildString,
    WWAA_PromptWriter,
    WWAA_ImageToTextFile,
    WWAA_AdvancedTextFileReader,
    WWAA_SearchReplaceText,
    WWAA_JSONPromptBuilder,
    WWAA_AdvancedTextReader,
    WWAA_CameraAngleBuilder,
    WWAA_SearchReplaceMulti,
)

# Import all utility nodes
from .utility_nodes import (
    WWAA_NestedLoopCounter,
    WWAA_Switch_Int,
    WWAA_MetadataSaver,
    WWAA_DisplayAny,
    WWAA_TextFileBrowser,
)

# Import all video nodes
from .video_nodes import (
    WWAA_VideoResolution,
)

# Import all math nodes
from .math_nodes import (
    WWAA_BasicMathNode,
)

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "WWAA_NumberRangeAsString": WWAA_NumberRangeAsString,
    "WWAA_LineCount": WWAA_LineCount,
    "WWAA_BuildString": WWAA_BuildString,
    "WWAA_DitherNode": WWAA_DitherNode,
    "WWAA_ImageLoader": WWAA_ImageLoader,
    "WWAA_PromptWriter": WWAA_PromptWriter,
    "WWAA_ImageToTextFile": WWAA_ImageToTextFile,
    "WWAA_AdvancedTextFileReader": WWAA_AdvancedTextFileReader,
    "WWAA_GBCamera": WWAA_GBCamera,
    "WWAA_NestedLoopCounter": WWAA_NestedLoopCounter,
    "WWAA_SearchReplaceText": WWAA_SearchReplaceText,
    "WWAA_Switch_Int": WWAA_Switch_Int,
    "WWAA_GridLayoutNode": WWAA_GridLayoutNode,
    "WWAA_AdvancedGridLayoutNode": WWAA_AdvancedGridLayoutNode,
    "WWAA_IndexGridLayoutNode": WWAA_IndexGridLayoutNode,
    "WWAA_BeforeAfterSlider": WWAA_BeforeAfterSliderNode,
    "WWAA_MetadataSaver": WWAA_MetadataSaver,
    "WWAA_ImageSwitcher": WWAA_ImageSwitcher,
    "WWAA_JSONPromptBuilder": WWAA_JSONPromptBuilder,
    "WWAA_VideoResolution": WWAA_VideoResolution,
    "WWAA_AdvancedTextReader": WWAA_AdvancedTextReader,
    "WWAA_DisplayAny": WWAA_DisplayAny,
    "WWAA_BasicMathNode": WWAA_BasicMathNode,
    "WWAA_CameraAngleBuilder": WWAA_CameraAngleBuilder,
    "WWAA_SearchReplaceMulti": WWAA_SearchReplaceMulti,
    "WWAA_SlicedArt": WWAA_SlicedArt,
    "WWAA_JPEGPreview": WWAA_JPEGPreview,
    "WWAA_SaveJPEG": WWAA_SaveJPEG,
    "WWAA_ImageDimensionCalculator": WWAA_ImageDimensionCalculator,
    "WWAA_ImageDimensionSize": WWAA_ImageDimensionSize,
    "WWAA_TextFileBrowser": WWAA_TextFileBrowser,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "WWAA_NumberRangeAsString": "🪠️ WWAA Number Range as String",
    "WWAA_LineCount": "🪠️ WWAA LineCount",
    "WWAA_BuildString": "🪠️ WWAA JoinString",
    "WWAA_DitherNode": "🪠️ WWAA Dither Image",
    "WWAA_ImageLoader": "🪠️ WWAA Image Batch Loader",
    "WWAA_PromptWriter": "🪠️ WWAA Prompt Writer",
    "WWAA_ImageToTextFile": "🪠️ WWAA LLM Prompt To Text File",
    "WWAA_AdvancedTextFileReader": "🪠️ WWAA Advanced Text File Reader",
    "WWAA_GBCamera": "🪠️ WWAA Game Boy Camera Style",
    "WWAA_NestedLoopCounter": "🪠️ WWAA Nested Loop Counter",
    "WWAA_SearchReplaceText": "🪠️ WWAA Search and Replace Text",
    "WWAA_Switch_Int": "🪠️ WWAA Switch Int",
    "WWAA_GridLayoutNode": "🪠️ WWAA Image Grid",
    "WWAA_AdvancedGridLayoutNode": "🪠️ WWAA Advanced Image Grid",
    "WWAA_IndexGridLayoutNode": "🪠️ WWAA Image Grid from Index",
    "WWAA_BeforeAfterSlider": "🪠️ WWAA Before After Animator",
    "WWAA_MetadataSaver": "🪠️ WWAA Metadata Saver",
    "WWAA_ImageSwitcher": "🪠️ WWAA Image Switcher",
    "WWAA_JSONPromptBuilder": "🪠️ WWAA JSON Prompt Builder",
    "WWAA_VideoResolution": "🪠️ WWAA Video Resolution",
    "WWAA_AdvancedTextReader": "🪠️ WWAA Advanced Text Reader",
    "WWAA_DisplayAny": "🪠️ WWAA Display Any",
    "WWAA_BasicMathNode": "🪠️ WWAA Basic Math",
    "WWAA_CameraAngleBuilder": "🪠️ WWAA Camera Angle Builder",
    "WWAA_SearchReplaceMulti": "🪠️ WWAA Search and Replace Multi",
    "WWAA_SlicedArt": "🪠️ WWAA Sliced Art",
    "WWAA_JPEGPreview": "🪠️ WWAA JPEG Preview",
    "WWAA_SaveJPEG": "🪠️ WWAA Save JPEG",
    "WWAA_ImageDimensionCalculator": "🪠️ WWAA Image Dimension Calculator",
    "WWAA_ImageDimensionSize": "🪠️ WWAA Image Dimension Size",
    "WWAA_TextFileBrowser": "🪠️ WWAA Text File Browser",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
