import streamlit as st
import pytesseract
import pandas as pd
from PIL import Image
import io

# Konfigurasi lokasi instalasi Tesseract di Windows 
# (Sesuaikan jika Anda menginstalnya di folder lain)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.title("Aplikasi Scan & Ekstrak KTP")
st.write("Ambil foto KTP langsung dari kamera HP atau unggah gambar, lalu ekstrak teksnya!")

# Pilihan metode input
opsi_input = st.radio("Pilih Metode:", ("Gunakan Kamera (Scan Langsung)", "Unggah Gambar dari Perangkat"))

gambar_terpilih = None

if opsi_input == "Gunakan Kamera (Scan Langsung)":
    gambar_terpilih = st.camera_input("Ambil Foto KTP")
else:
    gambar_terpilih = st.file_uploader("Pilih file foto KTP", type=['png', 'jpg', 'jpeg'])

if gambar_terpilih is not None:
    image = Image.open(gambar_terpilih)
    st.image(image, caption="Foto KTP Berhasil Diambil", use_container_width=True)
    
    if st.button("Mulai Ekstrak Data KTP"):
        with st.spinner("Sedang membaca teks pada KTP..."):
            try:
                # Proses OCR menggunakan pytesseract (Bahasa Indonesia = 'ind')
                teks_gabungan = pytesseract.image_to_string(image, lang='ind')
                
                st.success("Ekstrak data berhasil!")
                
                st.subheader("Hasil Teks Terbaca:")
                st.text(teks_gabungan)
                
                # Format ke Excel
                df_hasil = pd.DataFrame([{
                    "Teks Terbaca KTP": teks_gabungan
                }])
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_hasil.to_excel(writer, index=False, sheet_name='Data KTP')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="Unduh Hasil ke Excel (.xlsx)",
                    data=excel_data,
                    file_name="Hasil_Scan_KTP.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
                st.info("Pastikan Anda sudah menginstal aplikasi Tesseract OCR di komputer Anda.")