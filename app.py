import streamlit as st
import os
import random
import string
import numpy as np
from PIL import Image, ImageEnhance
import piexif
import zipfile
from io import BytesIO

def random_string(n=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def modify_metadata(img_path, meta_random=False):
    try:
        exif_dict = piexif.load(img_path)
    except:
        exif_dict = {"0th": {}, "Exif": {}, "1st": {}, "thumbnail": None}
    exif_dict["0th"][piexif.ImageIFD.Software] = random_string()
    exif_dict["0th"][piexif.ImageIFD.Artist] = random_string()
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = random_string()
    if meta_random:
        exif_dict["0th"][piexif.ImageIFD.Make] = random_string()
        exif_dict["0th"][piexif.ImageIFD.Model] = random_string()
        exif_dict["0th"][piexif.ImageIFD.Copyright] = random_string()
    return piexif.dump(exif_dict)

def slight_crop(img, crop_percent):
    w, h = img.size
    dx = int(w * crop_percent)
    dy = int(h * crop_percent)
    return img.crop((dx, dy, w - dx, h - dy))

def micro_rotate(img):
    angle = random.uniform(-1.2, 1.2)
    return img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

def micro_warp(img):
    w, h = img.size
    shift = random.uniform(0.003, 0.007)
    coeffs = (1, shift, 0, shift, 1, 0)
    return img.transform((w, h), Image.AFFINE, coeffs, resample=Image.Resampling.BICUBIC)

def micro_adjust(img, brightness_percent, contrast_percent):
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness_percent / 100)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast_percent / 100)
    arr = np.array(img).astype(np.int16)
    arr += random.randint(-2, 2)
    arr = np.clip(arr, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))

def apply_noise(img):
    arr = np.array(img).astype(np.int16)
    noise = np.random.randint(-2, 3, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def color_shift(img):
    r, g, b = img.split()
    r = r.point(lambda i: min(255, max(0, i + random.randint(-3, 3))))
    g = g.point(lambda i: min(255, max(0, i + random.randint(-3, 3))))
    b = b.point(lambda i: min(255, max(0, i + random.randint(-3, 3))))
    return Image.merge("RGB", (r, g, b))

def add_border(img, border_size):
    if border_size > 0:
        new_img = Image.new("RGB", (img.width + border_size * 2, img.height + border_size * 2), "black")
        new_img.paste(img, (border_size, border_size))
        return new_img
    return img

def process_image(input_img, brightness, contrast, crop_percent, add_noise, add_color, border, meta_random):
    temp_name = random_string(12) + ".jpg"
    input_img.save(temp_name, "JPEG")
    exif_bytes = modify_metadata(temp_name, meta_random)
    img = input_img.convert("RGB")
    img = slight_crop(img, crop_percent)
    img = micro_rotate(img)
    img = micro_warp(img)
    img = micro_adjust(img, brightness, contrast)
    if add_color:
        img = color_shift(img)
    if add_noise:
        img = apply_noise(img)
    img = add_border(img, border)
    output_name = random_string(16) + ".jpg"
    img.save(output_name, "JPEG", exif=exif_bytes, quality=94)
    os.remove(temp_name)
    return output_name, img

st.title("📸 Image Spoofer (Web Version)")
st.write("Transform and spoof your images with randomness, noise, EXIF spoofing, and more.")

uploaded_files = st.file_uploader("Upload Images", accept_multiple_files=True, type=["jpg","jpeg","png","webp"])

variants = st.number_input("Variants per image", 1, 20, 5)
brightness = st.slider("Brightness %", 50, 200, 102)
contrast = st.slider("Contrast %", 50, 200, 102)
crop_percent = st.slider("Crop %", 0, 20, 2) / 100
border = st.slider("Border Size", 0, 20, 2)

add_noise = st.checkbox("Add Noise", True)
add_color = st.checkbox("Color Shift", True)
meta_random = st.checkbox("Randomize Metadata", True)

if st.button("Start Spoofing"):
    if not uploaded_files:
        st.error("No files uploaded.")
    else:
        output_files = []
        progress = st.progress(0)
        total = len(uploaded_files) * variants
        done = 0

        for file in uploaded_files:
            img = Image.open(file)
            for _ in range(variants):
                filename, _ = process_image(img, brightness, contrast, crop_percent, add_noise, add_color, border, meta_random)
                output_files.append(filename)
                done += 1
                progress.progress(done/total)

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for f in output_files:
                z.write(f)
                os.remove(f)
        buf.seek(0)

        st.success("Done!")
        st.download_button("Download ZIP", data=buf, file_name="spoofed_images.zip", mime="application/zip")