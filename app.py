import streamlit as st
import easyocr
import pandas as pd
from PIL import Image
import io

st.title("Aplikasi Batch Scan & Ekstrak KTP")
st.write("Unggah banyak foto KTP sekaligus (hingga ratusan file), lalu ekstrak ke satu file Excel!")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['id', 'en'], gpu=False)

with st.spinner("Memuat sistem AI pembaca KTP..."):
    reader = load_reader()

# Mengaktifkan fitur multi-upload (bisa pilih banyak file sekaligus)
uploaded_files = st.file_uploader(
    "Pilih atau Seret (Drag & Drop) Banyak Foto KTP Sekaligus", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"Total {len(uploaded_files)} foto KTP dipilih.")
    
    if st.button("Mulai Proses Semua KTP"):
        data_hasil = []
        
        # Membuat progress bar di layar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_file = len(uploaded_files)
        
        # Perulangan (looping) untuk memproses setiap foto KTP
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Memproses file {i+1} dari {total_file}: {uploaded_file.name}")
            
            try:
                # Membuka gambar
                image = Image.open(uploaded_file)
                
                # Konversi ke bytes untuk EasyOCR
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='JPEG')
                image_bytes = image_bytes.getvalue()
                
                # Ekstrak teks
                hasil = reader.readtext(image_bytes, detail=0)
                teks_gabungan = " ".join(hasil)
                
                # Simpan hasilnya
                data_hasil.append({
                    "Nama File": uploaded_file.name,
                    "Teks Terbaca KTP": teks_gabungan
                })
            except Exception as e:
                data_hasil.append({
                    "Nama File": uploaded_file.name,
                    "Teks Terbaca KTP": f"Gagal diproses: {e}"
                })
            
            # Update progress bar
            progress_bar.progress((i + 1) / total_file)
        
        status_text.text("Semua KTP berhasil diproses!")
        st.success("Proses ekstraksi massal selesai!")
        
        # Ubah daftar hasil menjadi tabel DataFrame
        df_hasil = pd.DataFrame(data_hasil)
        
        # Tampilkan tabel pratinjau di web
        st.dataframe(df_hasil)
        
        # Konversi ke format Excel (Bytes)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hasil.to_excel(writer, index=False, sheet_name='Rekap Data KTP')
        excel_data = output.getvalue()
        
        # Tombol untuk mengunduh rekap Excel
        st.download_button(
            label="Unduh Rekap Semua Data ke Excel (.xlsx)",
            data=excel_data,
            file_name="Rekap_200_KTP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )