import streamlit as st
import pandas as pd
from PIL import Image
import io
import json
import time 
from google import genai

# --- KONFIGURASI API GEMINI ---
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key Gemini belum disetel di Streamlit Secrets! Tambahkan GEMINI_API_KEY terlebih dahulu.")

# --- KOMPONEN UI ---
st.title("Aplikasi Ekstraksi KTP Pintar (Powered by Gemini AI)")
st.write("Ekstraksi NIK & Nama berakurasi tinggi menggunakan kecerdasan buatan multimodal.")

MODEL_NAME = "gemini-3.6-flash"

def ekstrak_ktp_dengan_gemini(image, batas_percobaan=3):
    """Mengirim gambar KTP dengan fitur Auto-Retry (Pantang Menyerah)"""
    prompt = """
    Analisis gambar KTP ini dan ekstrak data berikut secara akurat:
    1. NIK (16 digit angka)
    2. NAMA (Nama lengkap pemilik KTP)

    Berikan hasilnya HANYA dalam format JSON murni seperti ini, tanpa teks tambahan:
    {
      "NIK": "nomor_nik_disini",
      "NAMA": "nama_lengkap_disini"
    }
    """
    
    # Sistem akan mencoba mengulang otomatis maksimal 3 kali jika ditolak Google
    for percobaan in range(batas_percobaan):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[image, prompt]
            )
            
            # Bersihkan format output
            teks_respons = response.text.strip()
            teks_respons = teks_respons.replace("```json", "").replace("```", "").strip()
            
            data_json = json.loads(teks_respons)
            return data_json
            
        except Exception as e:
            pesan_error = str(e)
            
            # Jika error 429 (kuota padat), tunggu 15 detik lalu COBA LAGI KTP YANG SAMA
            if "429" in pesan_error or "RESOURCE_EXHAUSTED" in pesan_error:
                if percobaan < batas_percobaan - 1:
                    time.sleep(15) # Jeda istirahat 15 detik sebelum diulang
                    continue # Kembali memproses KTP yang sama
            
            # Jika sudah diulang 3x dan tetap gagal, baru dicatat Error di Excel
            return {"NIK": f"Error: {pesan_error}", "NAMA": "GAGAL"}

# --- KOMPONEN UNGGAH & PROSES ---
uploaded_files = st.file_uploader(
    "Pilih atau Seret (Drag & Drop) Banyak Foto KTP Sekaligus", 
    type=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif'], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Mulai Proses Ekstraksi dengan AI"):
        data_hasil = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_file = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Memproses KTP {i+1} dari {total_file}: {uploaded_file.name}")
            try:
                image = Image.open(uploaded_file)
                if image.mode in ("RGBA", "P"): 
                    image = image.convert("RGB")
                
                # Panggil fungsi AI Gemini
                hasil_ekstraksi = ekstrak_ktp_dengan_gemini(image)
                
                row_data = {"No": i + 1}
                row_data.update(hasil_ekstraksi)
                data_hasil.append(row_data)
                
                # Jeda normal 10 detik antar KTP
                if i < total_file - 1:
                    status_text.text(f"KTP {i+1} selesai. Menjeda 10 detik agar aman dari limit...")
                    time.sleep(10)
                    
            except Exception as e:
                data_hasil.append({"No": i + 1, "NIK": f"Error Sistem: {e}", "NAMA": uploaded_file.name})
            
            progress_bar.progress((i + 1) / total_file)
        
        st.success("Proses ekstraksi massal selesai!")
        status_text.text("Semua KTP berhasil diproses.")
        
        df_hasil = pd.DataFrame(data_hasil)
        st.dataframe(df_hasil)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hasil.to_excel(writer, index=False, sheet_name='NIK_Nama_KTP')
        
        st.download_button(
            "Unduh Excel NIK & Nama (.xlsx)",
            data=output.getvalue(), file_name="Data_Rekap_NIK_Nama_KTP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
