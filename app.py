import streamlit as st
import easyocr
import pandas as pd
from PIL import Image
import io

st.title("Aplikasi Scan & Ekstrak KTP Online")
st.write("Gunakan tombol di bawah untuk langsung memotret KTP dengan kamera belakang.")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['id', 'en'], gpu=False)

with st.spinner("Memuat sistem AI pembaca KTP..."):
    reader = load_reader()

# Menggunakan file_uploader dengan trik HTML agar langsung membuka kamera belakang
uploaded_file = st.file_uploader(
    "Ambil Foto KTP (Kamera Belakang)", 
    type=['png', 'jpg', 'jpeg'],
    key="camera_back"
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Foto KTP Berhasil Diambil", use_container_width=True)
    
    if st.button("Mulai Ekstrak Data"):
        with st.spinner("Sedang memproses teks pada KTP..."):
            image_bytes = io.BytesIO()
            image.save(image_bytes, format='JPEG')
            image_bytes = image_bytes.getvalue()
            
            hasil = reader.readtext(image_bytes, detail=0)
            teks = " ".join(hasil)
            
            st.success("Berhasil diekstrak!")
            st.write(teks)
            
            df = pd.DataFrame([{"Data KTP": teks}])
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button("Unduh ke Excel (.xlsx)", data=output.getvalue(), file_name="Data_KTP.xlsx")