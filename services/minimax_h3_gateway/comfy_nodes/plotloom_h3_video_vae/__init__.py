"""Maintained pinned-Comfy H3 video loader; no global or audio dtype mutation."""
from .loader import PlotloomH3VideoVAELoader

NODE_CLASS_MAPPINGS = {"PlotloomH3VideoVAELoader": PlotloomH3VideoVAELoader}
