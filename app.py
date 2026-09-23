import streamlit as st
import easyocr
import pandas as pd
from PIL import Image
import io
import re

# --- KOMPONEN UI ---
st.title("Aplikasi Ekstraksi KTP Khusus NIK & NAMA")
st.write("Menggunakan pengurutan koordinat teks (Top-to-Bottom OCR) untuk akurasi tinggi pada KTP ber-watermark.")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['id', 'en'], gpu=False)

with st.spinner("Memuat sistem AI pembaca KTP (Proses ini mungkin memakan waktu beberapa menit saat pertama kali)..."):
    reader = load_reader()

def parse_ktp_nik_nama(text):
    data = {
        "NIK": "", 
        "NAMA": ""
    }
    
    # 1. Bersihkan karakter aneh hasil OCR
    text_clean = text.replace("{", "3").replace("}", "").replace("|", "I").replace("?", "7").replace("€", "E")
    text_clean = re.sub(r'\s+', ' ', text_clean)
    
    # 2. Pencarian Global NIK (Mencari 16 digit angka unik di mana pun letaknya)
    nik_match = re.search(r'\b\d{16}\b', text_clean)
    if nik_match:
        data["NIK"] = nik_match.group(0)

    # 3. Pembersih Watermark / Teks Latar Belakang KTP Lama
    watermark_patterns = [
        r'KARTU\s+TANDA\s+PENDUDUK',
        r'PENDUDUK\s+INDONESIA',
        r'REPUBLIK\s+INDONESIA'
    ]
    for pat in watermark_patterns:
        text_clean = re.sub(pat, ' ', text_clean, flags=re.IGNORECASE)

    # 4. Pencarian NAMA (Mencari teks setelah label Nama/Nara/Nam)
    nama_match = re.search(r'(?i)\b(?:Nama|Nara|Narna|Nam)\b\s*[:\s]*([A-Z\s\.\,\']+?)(?=\s+(?:Tempat|Tgl|Lahir|Jenis|Alamat|Agama|NIK|$))', text_clean)
    if nama_match:
        nama_bersih = re.sub(r'^[\:\.\-\;\_]+', '', nama_match.group(1)).strip().upper()
        data["NAMA"] = nama_bersih
    
    # Fallback pengaman jika format label agak bergeser
    if not data["NAMA"]:
        words = text_clean.split()
        for idx, w in enumerate(words):
            if w in ["NAMA", "NAMA:", "Nara", "Nam"]:
                candidate = " ".join(words[idx+1:idx+4])
                for stop_word in ["TEMPAT", "LAHIR", "JENIS", "ALAMAT", "AGAMA"]:
                    if stop_word in candidate:
                        candidate = candidate.split(stop_word)[0]
                data["NAMA"] = re.sub(r'[^A-Z\s]', '', candidate).strip()
                break

    return data

# --- KOMPONEN UNGGAH & PROSES ---
uploaded_files = st.file_uploader(
    "Pilih atau Seret (Drag & Drop) Banyak Foto KTP Sekaligus", 
    type=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif'], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Mulai Proses Ekstraksi NIK & Nama"):
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
                
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='JPEG')
                
                # MENGGUNAKAN DETAIL=1 UNTUK MENDAPATKAN KOORDINAT POSISI TEKS
                results = reader.readtext(image_bytes.getvalue(), detail=1)
                
                # URUTKAN TEKS DARI ATAS KE BAWAH (Top-to-Bottom berdasarkan koordinat y)
                # results format: [([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], text, prob), ...]
                sorted_results = sorted(results, key=lambda x: x[0][0][1])
                text_lines = [res[1] for res in sorted_results]
                combined_text = " ".join(text_lines)
                
                parsed_data = parse_ktp_nik_nama(combined_text)
                
                row_data = {"No": i + 1}
                row_data.update(parsed_data)
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
