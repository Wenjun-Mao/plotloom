"""Bounded pure centered geometry preparation with an auditable recipe."""
from hashlib import sha256
from inspect import getsource
from io import BytesIO
from PIL import Image, __version__ as pillow_version
from .geometry_preparation_contracts import GeometryPolicy, GeometryRecipe, GeometryRuntime
from .keyframe_preparation import center_crop_png
from .managed_media import inspect_import_image


def geometry_runtime():
    return GeometryRuntime(pillow_version=pillow_version, transform_hash=sha256(getsource(center_crop_png).encode()).hexdigest())


def geometry_policy():
    return GeometryPolicy(runtime=geometry_runtime())


def prepare_geometry(content, *, width, height):
    observed = inspect_import_image(content)
    with Image.open(BytesIO(content)) as image:
        orientation = image.getexif().get(274, 1)
    if orientation not in range(1, 9):
        raise ValueError("unsupported EXIF orientation")
    w, h = (observed.height, observed.width) if orientation >= 5 else (observed.width, observed.height)
    if w * height > h * width:
        cw, ch = h * width / height, float(h)
    else:
        cw, ch = float(w), w * height / width
    recipe = GeometryRecipe(exif_orientation=orientation, oriented_width=w, oriented_height=h,
        crop_box=((w-cw)/2, (h-ch)/2, (w+cw)/2, (h+ch)/2), target_width=width, target_height=height)
    output = center_crop_png(content, target_width=width, target_height=height)
    result = inspect_import_image(output)
    if (result.width, result.height) != (width, height):
        raise ValueError("deterministic geometry output differs from frozen target")
    return output, result, recipe
