import streamlit as st
import easyocr
import pandas as pd
from PIL import Image
import io
import re

st.title("Aplikasi Batch Scan & Format KTP ke Excel")
st.write("Unggah banyak foto KTP sekaligus, ekstrak, dan unduh dalam format tabel KTP yang rapi!")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['id', 'en'], gpu=False)

with st.spinner("Memuat sistem AI pembaca KTP..."):
    reader = load_reader()

def parse_ktp_text(text):
    data = {
        "NIK": "", "NAMA": "", "Tempat/Tgl Lahir": "", "Jenis Kelamin": "",
        "Alamat": "", "Agama": "", "Status Perkawinan": "", "Pekerjaan": "",
        "Kewarganegaraan": "", "Berlaku Hingga": ""
    }
    
    # 0. Normalisasi Teks KTP/KIA untuk OCR yang kotor (Pembersih Teks)
    text_clean = text.replace("{", "3").replace("}", "").replace("|", "I").replace("?", "7").replace("€", "E")
    
    # Memperbaiki salah eja (typo) umum dari OCR KTP
    text_clean = re.sub(r'(?i)(Nara|Narna|Nam)\b', 'Nama', text_clean)
    text_clean = re.sub(r'(?i)(Lergka)', 'Lengkap', text_clean)
    text_clean = re.sub(r'(?i)(Terpa|Tempal|Tenpat|TenpatTgi)', 'Tempat', text_clean)
    text_clean = re.sub(r'(?i)(Tcl)', 'Tgl', text_clean)
    text_clean = re.sub(r'(?i)(Lahis)', 'Lahir', text_clean)
    text_clean = re.sub(r'(?i)(Aamat|Nlamal|Nemal)', 'Alamat', text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean)
    
    # 1. NIK
    nik_match = re.search(r'(?:NIK|M|K)\s*[:\.]?\s*([0-9\s]{16,20})', text_clean, re.IGNORECASE)
    if nik_match:
        nik_val = re.sub(r'\D', '', nik_match.group(1))
        if len(nik_val) >= 16: data["NIK"] = nik_val[:16]
    if not data["NIK"]:
        all_nums = re.findall(r'\b[0-9]{16}\b', text_clean)
        if all_nums: data["NIK"] = all_nums[0]
        
    # 2. NAMA
    nama_match = re.search(r'Nama\s*(?:Lengkap)?\s*[\:\.\)\-]*\s*([a-zA-Z\s\.\']+?)\s+(?:Tempat|Tgl|Lahir|Alamat|Jenis|Gol)', text_clean, re.IGNORECASE)
    if nama_match: data["NAMA"] = nama_match.group(1).strip().upper()
        
    # 3. TTL
    ttl_match = re.search(r'(?:Tempat|Tgl|Lahir)\s*[\:\.\-\)]*\s*([a-zA-Z0-9\s\,\-\/]+?)\s+(?:Jenis|Jens|Gol|Alamat|Agama)', text_clean, re.IGNORECASE)
    if ttl_match:
        val = re.sub(r'^(?:Lahir|TglLahir)\s*', '', ttl_match.group(1).strip(), flags=re.IGNORECASE)
        data["Tempat/Tgl Lahir"] = val.upper()
        
    # 4. Jenis Kelamin
    if re.search(r'LAKI|LAK[-_]LAK', text_clean, re.IGNORECASE): data["Jenis Kelamin"] = "LAKI-LAKI"
    elif re.search(r'PEREMPUAN|PERENPUAN', text_clean, re.IGNORECASE): data["Jenis Kelamin"] = "PEREMPUAN"
    
    # 5. Alamat
    alamat_match = re.search(r'(?:Alamat)\s*[\:\.\-\)]*\s*([a-zA-Z0-9\s\,\-\/\.\?\€]+?)\s+(?:RT|RW|RTRW|RHRW|BTRW|Kel|Desa|Kecamatan|Agama)', text_clean, re.IGNORECASE)
    if alamat_match: data["Alamat"] = alamat_match.group(1).strip().upper()
        
    # 6. Agama
    for agama in ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDHA", "KONGHUCU"]:
        if agama in text_clean.upper():
            data["Agama"] = agama
            break
            
    # 7. Status Perkawinan
    for status in ["BELUM KAWIN", "KAWIN", "CERAI MATI", "CERAI HIDUP"]:
        if status in text_clean.upper():
            data["Status Perkawinan"] = status
            break
            
    # 8. Pekerjaan
    pek_match = re.search(r'Pekerjaan\s*[:\.]?\s*([A-Z\s]+?)(?=\s+(?:Kewarganegaraan|Berlaku|Gol)|$)', text_clean, re.IGNORECASE)
    if pek_match: data["Pekerjaan"] = pek_match.group(1).strip().upper()
        
    # 9. Kewarganegaraan
    if "WNI" in text_clean.upper(): data["Kewarganegaraan"] = "WNI"
    elif "WNA" in text_clean.upper(): data["Kewarganegaraan"] = "WNA"
        
    # 10. Berlaku Hingga
    if "SEUMUR HIDUP" in text_clean.upper(): data["Berlaku Hingga"] = "SEUMUR HIDUP"
    else:
        berlaku_match = re.search(r'Berlaku\s*Hingga\s*[:\.]?\s*([A-Z0-9\-]+)', text_clean, re.IGNORECASE)
        if berlaku_match: data["Berlaku Hingga"] = berlaku_match.group(1).strip().upper()
        
    return data

# Komponen Upload Banyak File
uploaded_files = st.file_uploader(
    "Pilih atau Seret (Drag & Drop) Banyak Foto KTP Sekaligus", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"Total {len(uploaded_files)} foto KTP dipilih.")
    
    if st.button("Mulai Proses & Format ke Tabel KTP"):
        data_hasil = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_file = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Memproses file {i+1} dari {total_file}: {uploaded_file.name}")
            
            try:
                image = Image.open(uploaded_file)
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='JPEG')
                image_bytes = image_bytes.getvalue()
                
                # Ekstrak teks OCR
                hasil = reader.readtext(image_bytes, detail=0)
                teks_gabungan = " ".join(hasil)
                
                # Parsing teks ke format kolom KTP
                parsed_data = parse_ktp_text(teks_gabungan)
                
                # Masukkan nomor urut
                row_data = {"No": i + 1}
                row_data.update(parsed_data)
                data_hasil.append(row_data)
                
            except Exception as e:
                data_hasil.append({
                    "No": i + 1, "NIK": f"Error: {e}", "NAMA": uploaded_file.name,
                    "Tempat/Tgl Lahir": "", "Jenis Kelamin": "", "Alamat": "",
                    "Agama": "", "Status Perkawinan": "", "Pekerjaan": "",
                    "Kewarganegaraan": "", "Berlaku Hingga": ""
                })
            
            progress_bar.progress((i + 1) / total_file)
        
        status_text.text("Semua KTP berhasil diproses dan diformat!")
        st.success("Proses selesai!")
        
        # Buat DataFrame sesuai kolom format KTP
        df_hasil = pd.DataFrame(data_hasil)
        
        # Tampilkan pratinjau tabel di web
        st.dataframe(df_hasil)
        
        # Ekspor ke file Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hasil.to_excel(writer, index=False, sheet_name='Format KTP')
        excel_data = output.getvalue()
        
        # Tombol Download
        st.download_button(
            label="Unduh Excel Sesuai Format KTP (.xlsx)",
            data=excel_data,
            file_name="Data_Rekap_Sesuai_Format_KTP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )