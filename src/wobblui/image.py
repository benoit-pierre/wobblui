
import os
import sdl2 as sdl
import sdl2.sdlimage as sdlimage
import tempfile

from wobblui.sdlinit import initialize_sdl
from wobblui.widget import Widget

sdlimage_initialized = False

def stock_image(name):
    p = os.path.join(os.path.abspath(os.path.dirname(__file__)),
        "img", name)
    if name.find(".") < 0:
        if os.path.exists(p + ".png"):
            return (p + ".png")
        elif os.path.exists(p + ".jpg"):
            return (p + ".jpg")
    return p

def image_to_sdl_surface(pil_image):
    global sdlimage_initialized
    initialize_sdl()
    if not sdlimage_initialized:
        flags = sdlimage.IMG_INIT_JPG|sdlimage.IMG_INIT_PNG
        sdlimage.IMG_Init(flags)
    sdl_image = None
    (fd, path) = tempfile.mkstemp(prefix="wobblui-image-")
    try:
        os.close(fd)
        pil_image.save(path, format="PNG")
        sdl_image = sdlimage.IMG_Load(path.encode("utf-8", "replace"))
    finally:
        os.remove(path)
    if sdl_image is None:
        err_msg = sdlimage.IMG_GetError()
        try:
            err_msg = err_msg.decode("utf-8", "replace")
        except AttributeError:
            pass
        raise ValueError("failed to load image with SDL Image: " +
            str(err_msg))
    return sdl_image

def image_to_sdl_texture(renderer, pil_image):
    initialize_sdl()
    sdl_image = image_to_sdl_surface(pil_image)
    try:
        texture = sdl.SDL_CreateTextureFromSurface(renderer, sdl_image)
    finally:
        sdl.SDL_FreeSurface(sdl_image)
    return texture

def image_as_grayscale(pil_image):
    if pil_image.mode.upper() == "RGBA":
        gray_image = pil_image.convert("LA")
        return gray_image
    elif pil_image.mode.upper() == "RGB":
        gray_image = pil_image.convert("L")
        return gray_image
    elif pil_image.mode.upper() == "L" or \
            pil_image.mode.upper() == "LA":
        return pil_image.copy()
    else:
        raise RuntimeError("unsupported mode: " +
            pil_image.mode)

def remove_image_alpha(pil_image):
    if pil_image.mode.upper() == "RGBA":
        no_alpha_img = PIL.Image.new("RGB",
            pil_image.size,
            (255, 255, 255))
        no_alpha_img.paste(pil_image,
            mask=pil_image.split()[3])
        return no_alpha_img
    elif pil_image.mode.upper() == "RGB":
        return pil_image.copy()
    else:
        raise RuntimeError("unsupported mode: " +
            pil_Image.mode)

