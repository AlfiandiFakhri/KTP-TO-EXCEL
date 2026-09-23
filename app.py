import streamlit as st
import pandas as pd
from PIL import Image
import io
import json
import google.generativeai as genai

# --- KONFIGURASI API GEMINI ---
# Mengambil API Key secara aman dari Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key Gemini belum disetel di Streamlit Secrets! Tambahkan GEMINI_API_KEY terlebih dahulu.")

# --- KOMPONEN UI ---
st.title("Aplikasi Ekstraksi KTP Pintar (Powered by Gemini AI)")
st.write("Ekstraksi NIK & Nama berakurasi tinggi menggunakan kecerdasan buatan multimodal.")

# Pilih model Gemini yang cepat dan mendukung gambar
MODEL_NAME = "gemini-1.5-flash"

def ekstrak_ktp_dengan_gemini(image):
    """Mengirim gambar KTP langsung ke Gemini API untuk diekstrak"""
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
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([image, prompt])
        
        # Bersihkan format output jika ada pembungkus markdown code block
        teks_respons = response.text.strip()
        teks_respons = teks_respons.replace("```json", "").replace("```", "").strip()
        
        data_json = json.loads(teks_respons)
        return data_json
    except Exception as e:
        return {"NIK": f"Error: {str(e)}", "NAMA": "GAGAL"}

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
            status_text.text(f"Memproses file {i+1} dari {total_file}: {uploaded_file.name}")
            try:
                image = Image.open(uploaded_file)
                if image.mode in ("RGBA", "P"): 
                    image = image.convert("RGB")
                
                # Panggil fungsi AI Gemini
                hasil_ekstraksi = ekstrak_ktp_dengan_gemini(image)
                
                row_data = {"No": i + 1}
                row_data.update(hasil_ekstraksi)
                data_hasil.append(row_data)
            except Exception as e:
                data_hasil.append({"No": i + 1, "NIK": f"Error: {e}", "NAMA": uploaded_file.name})
            
            progress_bar.progress((i + 1) / total_file)
        
        st.success("Proses ekstraksi massal selesai!")
        
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
