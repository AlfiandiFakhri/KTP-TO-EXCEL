import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import json
import time

st.title("Scanner KTP TO EXCEL")
st.write("200 KTP")

# --- AMBIL API KEYS DARI STREAMLIT SECRETS (AMAN DARI GITHUB) ---
if "API_KEYS" in st.secrets:
    LIST_API_KEYS = st.secrets["API_KEYS"]
else:
    st.error("API Keys belum dikonfigurasi di Streamlit Secrets!")
    LIST_API_KEYS = []

# Simpan indeks kunci aktif ke dalam Session State Streamlit
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

def get_model_with_current_key():
    if not LIST_API_KEYS:
        return None
    st.session_state.key_index = st.session_state.key_index % len(LIST_API_KEYS)
    active_key = LIST_API_KEYS[st.session_state.key_index]
    genai.configure(api_key=active_key)
    return genai.GenerativeModel('gemini-3.6-flash')

# --- LOGIKA EKSTRAKSI DENGAN ROTASI KUNCI OTOMATIS ---
def ekstrak_ktp_dengan_ai(image_file):
    prompt = """
    Anda adalah asisten AI ahli. Baca KTP pada gambar ini dan ekstrak datanya ke dalam format JSON.
    Perbaiki salah ketik (typo) secara otomatis.
    Output HANYA boleh berupa format JSON murni yang valid, TANPA blok kode markdown, TANPA teks apapun.
    
    Gunakan persis struktur kunci (key) JSON berikut:
    {
      "Nama": "",
      "NIK": "",
      "Tempat/Tgl Lahir": "",
      "Jenis Kelamin": "",
      "Status Perkawinan": "",
      "Pekerjaan": ""
    }
    """
    
    if not LIST_API_KEYS:
        return {"Error": "API Key tidak ditemukan di Streamlit Secrets."}

    for attempt in range(len(LIST_API_KEYS)):
        try:
            model = get_model_with_current_key()
            response = model.generate_content([prompt, image_file])
            
            clean_text = response.text.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            if clean_text.startswith("```"): clean_text = clean_text[3:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
                
            return json.loads(clean_text.strip())
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota" in error_str:
                st.session_state.key_index = (st.session_state.key_index + 1) % len(LIST_API_KEYS)
                time.sleep(2)
            else:
                return {"Error": error_str}
                
    return {"Error": "Semua API Key telah habis kuotanya hari ini."}

# --- ANTARMUKA APLIKASI (UI) ---
uploaded_files = st.file_uploader(
    "Unggah Foto KTP", 
    type=['png', 'jpg', 'jpeg'], accept_multiple_files=True
)

if uploaded_files:
    if st.button("PROSES"):
        data_hasil = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_file = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            key_info = f"Key ke-{st.session_state.key_index + 1}" if LIST_API_KEYS else "No Key"
            status_text.text(f"memproses KTP ke-{i+1} dari {total_file} ({key_info})...")
            
            image = Image.open(uploaded_file)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            
            parsed_data = ekstrak_ktp_dengan_ai(image)
            
            row_data = {"No": i + 1}
            if "Error" not in parsed_data:
                row_data["Nama"] = parsed_data.get("Nama", "")
                row_data["NIK"] = parsed_data.get("NIK", "")
                row_data["Tempat/Tgl Lahir"] = parsed_data.get("Tempat/Tgl Lahir", "")
                row_data["Jenis Kelamin"] = parsed_data.get("Jenis Kelamin", "")
                row_data["Status Perkawinan"] = parsed_data.get("Status Perkawinan", "")
                row_data["Pekerjaan"] = parsed_data.get("Pekerjaan", "")
            else:
                row_data["Nama"] = parsed_data["Error"]
                row_data["NIK"] = "GAGAL DIBACA"
                
            data_hasil.append(row_data)
            progress_bar.progress((i + 1) / total_file)
            time.sleep(1)
        
        st.success("SELESAI!")
        
        df_hasil = pd.DataFrame(data_hasil)
        st.dataframe(df_hasil)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hasil.to_excel(writer, index=False, sheet_name='Rekap KTP')
        
        st.download_button(
            "Unduh Hasil",
            data=output.getvalue(), file_name="Rekap_KTP_TO_EXCEL.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
