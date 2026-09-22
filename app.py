import streamlit as st
import easyocr
import pandas as pd
from PIL import Image
import io

st.title("Aplikasi Scan & Ekstrak KTP Online")
st.write("Ambil foto KTP langsung dari kamera HP atau unggah file, ekstrak data otomatis!")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['id', 'en'], gpu=False)

with st.spinner("Memuat sistem AI pembaca KTP..."):
    reader = load_reader()

# Membuat pilihan metode: Menggunakan Kamera Langsung atau Unggah File
pilihan = st.radio("Pilih Cara Ambil Gambar:", ("Gunakan Kamera HP Langsung", "Unggah dari Galeri/File"))

uploaded_file = None

if pilihan == "Gunakan Kamera HP Langsung":
    # Tombol khusus yang langsung membuka kamera HP
    uploaded_file = st.camera_input("Ambil Foto KTP Anda")
else:
    uploaded_file = st.file_uploader("Pilih file foto KTP", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Foto KTP Berhasil Dimuat", use_container_width=True)
    
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