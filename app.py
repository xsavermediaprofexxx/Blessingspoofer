
import streamlit as st
import os, random, string, zipfile
import numpy as np
from io import BytesIO
from PIL import Image, ImageEnhance
import piexif

# Neon CSS theme
st.markdown("""
<style>
body {background:#070710;}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(145deg,#090a12,#06060a);
    color:#b8dcff;
    font-family: 'Arial';
}
.neon-title {
    color:#9d4cff;
    text-shadow:0 0 12px #9d4cff,0 0 22px #5a33ff;
    font-size:48px;
    text-align:center;
    font-weight:bold;
}
.panel {
    border:1px solid #6f25ff;
    padding:20px;
    border-radius:15px;
    box-shadow:0 0 15px #5a33ff;
    background:rgba(20,20,35,0.4);
}
button[kind="primary"] {
    border:1px solid #873cff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='neon-title'>Blessing Spoofer</div>", unsafe_allow_html=True)
st.write("## ")

def random_string(n=12):
    import string, random
    return ''.join(random.choices(string.ascii_letters+string.digits,k=n))

def modify_metadata(img_path, meta_random=False):
    try: exif_dict = piexif.load(img_path)
    except: exif_dict = {"0th": {}, "Exif": {}, "1st": {}, "thumbnail": None}
    exif_dict["0th"][piexif.ImageIFD.Software] = random_string()
    exif_dict["0th"][piexif.ImageIFD.Artist] = random_string()
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = random_string()
    if meta_random:
        for tag in [piexif.ImageIFD.Make, piexif.ImageIFD.Model, piexif.ImageIFD.Copyright]:
            exif_dict["0th"][tag] = random_string()
    return piexif.dump(exif_dict)

def slight_crop(img, p):
    w,h = img.size; dx=int(w*p); dy=int(h*p)
    return img.crop((dx,dy,w-dx,h-dy))

def micro_rotate(img):
    return img.rotate(random.uniform(-1.2,1.2),expand=True,resample=Image.Resampling.BICUBIC)

def micro_warp(img):
    w,h=img.size; s=random.uniform(0.003,0.007)
    return img.transform((w,h),Image.AFFINE,(1,s,0,s,1,0),resample=Image.Resampling.BICUBIC)

def micro_adjust(img,b,c):
    img = ImageEnhance.Brightness(img).enhance(b/100)
    img = ImageEnhance.Contrast(img).enhance(c/100)
    arr=np.array(img).astype(np.int16)
    arr+=random.randint(-2,2)
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8))

def apply_noise(img):
    arr=np.array(img).astype(np.int16)
    noise=np.random.randint(-2,3,arr.shape)
    return Image.fromarray(np.clip(arr+noise,0,255).astype(np.uint8))

def color_shift(img):
    r,g,b=img.split()
    shift=lambda i: min(255,max(0,i+random.randint(-3,3)))
    return Image.merge("RGB",(r.point(shift),g.point(shift),b.point(shift)))

def add_border(img,size):
    if size<=0: return img
    new=Image.new("RGB",(img.width+size*2,img.height+size*2),"black")
    new.paste(img,(size,size))
    return new

def process_image(img, bright, cont, crop, noise, color, border, meta):
    temp=random_string()+".jpg"; img.save(temp,"JPEG")
    exif=modify_metadata(temp,meta)
    os.remove(temp)
    x=img.convert("RGB")
    x=slight_crop(x,crop)
    x=micro_rotate(x)
    x=micro_warp(x)
    x=micro_adjust(x,bright,cont)
    if color: x=color_shift(x)
    if noise: x=apply_noise(x)
    x=add_border(x,border)
    name=random_string()+".jpg"
    x.save(name,"JPEG",exif=exif,quality=94)
    return name,x

st.markdown("<div class='panel'>", unsafe_allow_html=True)
files = st.file_uploader("Upload images:", accept_multiple_files=True, type=["jpg","jpeg","png","webp"])
variants = st.slider("Variants per image",1,20,5)
bright = st.slider("Brightness %",50,200,102)
cont = st.slider("Contrast %",50,200,102)
crop = st.slider("Crop %",0,20,2)/100
border = st.slider("Border Size",0,20,2)
noise = st.checkbox("Add Noise",True)
color = st.checkbox("Color Shift",True)
meta = st.checkbox("Randomize Metadata",True)
st.markdown("</div>", unsafe_allow_html=True)

if st.button("Start Spoofing"):
    if not files: st.error("Please upload files.")
    else:
        with st.spinner("Spoofing in progress..."):
            out=[]
            buf=BytesIO()
            total=len(files)*variants; done=0
            bar=st.progress(0)
            for f in files:
                img=Image.open(f)
                for _ in range(variants):
                    name,_ = process_image(img,bright,cont,crop,noise,color,border,meta)
                    out.append(name); done+=1; bar.progress(done/total)
            z=zipfile.ZipFile(buf,"w")
            for f in out: z.write(f); os.remove(f)
            z.close(); buf.seek(0)
        st.success("Done!")
        st.download_button("Download Results ZIP",buf,"spoofed_images.zip","application/zip")
