# Import all image nodes
from .image_nodes import (
    WWAA_ImageLoader,
    WWAA_DitherNode,
    WWAA_GBCamera,
    WWAA_GridLayoutNode,
    WWAA_AdvancedGridLayoutNode,
    WWAA_IndexGridLayoutNode,
    WWAA_BeforeAfterSliderNode,
)

# Import all text nodes
from .text_nodes import (
    WWAA_LineCount,
    WWAA_BuildString,
    WWAA_PromptWriter,
    WWAA_ImageToTextFile,
    WWAA_AdvancedTextFileReader,
    WWAA_SearchReplaceText,
)

# Import all utility nodes
from .utility_nodes import (
    WWAA_NestedLoopCounter,
    WWAA_Switch_Int,
    WWAA_MetadataSaver,
)

# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
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
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
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
    "WWAA_MetadataSaver": "🪠️ WWAA Metadata Saver"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
