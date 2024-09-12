
from .WWAACustomNodes import WWAA_CLASS_MAPPINGS, WWAA_DISPLAY_NAME_MAPPINGS

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

NODE_CLASS_MAPPINGS.update(WWAA_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(WWAA_DISPLAY_NAME_MAPPINGS)

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']