
import hashlib
import hmac
import os
import shutil
import tempfile

import osintegration

DEBUG_FONTINFO=False

def extract_name_ending(font_filename):
    extracted_letters = 0
    if font_filename.lower().endswith(".ttf"):
        extracted_letters += len(".ttf")
        font_filename = font_filename[:-len(".ttf")]
    variants = ["Bold", "Italic", "BoldItalic",
        "ItalicBold", "Regular"]
    for variant in variants:
        if font_filename.endswith("-" + variant.lower()) or \
                font_filename.endswith("-" + variant) or \
                font_filename.endswith(" " + variant):
            extracted_letters += len("-" + variant)
            if variant == "ItalicBold":
                return ("BoldItalic", extracted_letters)
            return (variant, extracted_letters)
        if font_filename.endswith(variant) or \
                font_filename.endswith(variant.lower()):
            extracted_letters += len(variant)
            if variant == "ItalicBold":
                return ("BoldItalic", extracted_letters)
            return (variant, extracted_letters)
    return ("Regular", 0)

def get_font_paths_by_name(name):
    # Search in packaged folder:
    name_variants = []
    name_variants.append(name.lower())
    name_variants.append(name.replace(" ", "").lower())
    candidates = []
    for filename in os.listdir(os.path.abspath(
            os.path.join(os.path.dirname(__file__),
            "packaged-fonts"))):
        (variant_name, extracted_letters) = extract_name_ending(
            filename)
        if DEBUG_FONTINFO:
            print("searching " + str(name_variants) +
                " in " + str((variant_name, extracted_letters)) +
                " of packaged " + str(filename))
        if len(variant_name) > 0:
            for name_variant in name_variants:
                base = filename[:-extracted_letters].lower()
                if extracted_letters == 0:
                    base = filename
                if base.lower() == name_variant or \
                        (base.lower() + " " +
                        variant_name.lower()) == name_variant or \
                        (base.lower() + variant_name.lower()) == \
                        name_variant:
                    if variant_name.lower() != "regular":
                        candidates.append((base + variant_name[:1].upper() +
                            variant_name[1:].lower(),
                            os.path.normpath(os.path.join(
                            os.path.abspath(os.path.dirname(__file__)),
                            "packaged-fonts", filename))))
                    else:
                        candidates = [(base,
                            os.path.normpath(os.path.join(
                            os.path.abspath(os.path.dirname(__file__)),
                            "packaged-fonts", filename)))] + candidates
    if len(candidates) > 0:
        return candidates

    # Don't try other places on android:
    if osintegration.is_android():
        return []

    # Search system-wide:
    import fontconfig
    from font.query import get_font_name
    candidates = []
    unspecific_variants = ["italic", "bold", "condensed"]
    def is_not_regular(font_name):
        for unspecific_variant in unspecific_variants:
            if font_name.lower().endswith(unspecific_variant):
                return True
        return False
    for fpath in fontconfig.query():
        if not os.path.exists(fpath):
            continue
        (specific_name, unspecific_name) = get_font_name(fpath)
        if specific_name is None:
            continue
        if unspecific_name.lower() == name.lower() and \
                specific_name.lower() != name.lower() and \
                is_not_regular(specific_name):
            # Not-so-good match:
            candidates.append((specific_name, fpath))
        elif unspecific_name.lower() == name.lower() or \
                specific_name.lower() == name.lower():
            # Good match:
            candidates = [(specific_name, fpath)] +\
                candidates
    return candidates

cache_path = None

def clear_cache():
    global cache_path
    if cache_path != None:
        shutil.rmdir(cache_path)
        cache_path = None

def get_font_as_ttf_files(name):
    global cache_path
    if cache_path == None:
        cache_path = tempfile.mkdtemp(
            prefix="fontinfoutil-conversion-cache-")
    new_paths = []
    for (fname, fpath) in get_font_paths_by_name(name):
        if fpath.lower().endswith(".ttf"):
            new_paths.append((fname, fpath))
            continue
        cache_name = hmac.new(b"unnecessarysalt",
            fpath.encode("utf-8"), hashlib.sha512).hexdigest()
        full_path = os.path.join(cache_path, cache_name + ".ttf")
        if os.path.exists(full_path):
            return full_path
        import wobblui.font.otfttf as fontotfttf
        fontotfttf.otf_to_ttf(fpath, full_path)
        new_paths.append((fname, full_path))
    return new_paths


