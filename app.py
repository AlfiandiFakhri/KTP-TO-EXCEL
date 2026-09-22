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

# Fungsi untuk memetakan teks OCR ke kolom format KTP
def parse_ktp_text(text):
    data = {
        "NIK": "",
        "NAMA": "",
        "Tempat/Tgl Lahir": "",
        "Jenis Kelamin": "",
        "Alamat": "",
        "Agama": "",
        "Status Perkawinan": "",
        "Pekerjaan": "",
        "Kewarganegaraan": "",
        "Berlaku Hingga": ""
    }
    
    # Bersihkan spasi berlebih
    text_clean = re.sub(r'\s+', ' ', text)
    
    # 1. Ekstrak NIK (16 digit angka)
    nik_match = re.search(r'NIK\s*[:\.]?\s*([0-9]{16})', text_clean, re.IGNORECASE)
    if not nik_match:
        nik_match = re.search(r'\b([0-9]{16})\b', text_clean)
    if nik_match:
        data["NIK"] = nik_match.group(1)
        
    # 2. Ekstrak Nama
    nama_match = re.search(r'Nama\s*(?:Lengkap)?\s*[:\.]?\s*([A-Z\s\.]+?)(?=\s+(?:Tempat|Alamat|Jenis|Gol|Agama|Status|Pekerjaan|Kewarganegaraan|Berlaku)|$)', text_clean, re.IGNORECASE)
    if nama_match:
        data["NAMA"] = nama_match.group(1).strip()
        
    # 3. Ekstrak Tempat/Tgl Lahir
    ttl_match = re.search(r'(?:Tempat|Tgl)?\s*Lahir\s*[:\.]?\s*([A-Z\s\,\-\/0-9]+?)(?=\s+(?:Jenis|Gol|Alamat|Agama|Status)|$)', text_clean, re.IGNORECASE)
    if ttl_match:
        data["Tempat/Tgl Lahir"] = ttl_match.group(1).strip()
        
    # 4. Ekstrak Jenis Kelamin
    jk_match = re.search(r'Jenis\s*Kelamin\s*[:\.]?\s*([A-Z\-]+)', text_clean, re.IGNORECASE)
    if jk_match:
        val_jk = jk_match.group(1).strip()
        if "LAKI" in val_jk:
            data["Jenis Kelamin"] = "LAKI-LAKI"
        elif "PEREMPUAN" in val_jk:
            data["Jenis Kelamin"] = "PEREMPUAN"
        else:
            data["Jenis Kelamin"] = val_jk
            
    # 5. Ekstrak Alamat
    alamat_match = re.search(r'Alamat\s*[:\.]?\s*([A-Z0-9\s\,\-\/]+?)(?=\s+(?:RT|RW|Desa|Kecamatan|Agama|Status|Pekerjaan)|$)', text_clean, re.IGNORECASE)
    if alamat_match:
        data["Alamat"] = alamat_match.group(1).strip()
        
    # 6. Ekstrak Agama
    agama_match = re.search(r'Agama\s*[:\.]?\s*([A-Z]+)', text_clean, re.IGNORECASE)
    if agama_match:
        data["Agama"] = agama_match.group(1).strip()
        
    # 7. Ekstrak Status Perkawinan
    status_match = re.search(r'Status\s*Perkawinan\s*[:\.]?\s*([A-Z]+)', text_clean, re.IGNORECASE)
    if status_match:
        data["Status Perkawinan"] = status_match.group(1).strip()
        
    # 8. Ekstrak Pekerjaan
    pek_match = re.search(r'Pekerjaan\s*[:\.]?\s*([A-Z\s]+?)(?=\s+(?:Kewarganegaraan|Berlaku|Gol)|$)', text_clean, re.IGNORECASE)
    if pek_match:
        data["Pekerjaan"] = pek_match.group(1).strip()
        
    # 9. Ekstrak Kewarganegaraan
    Kewarganegaraan_match = re.search(r'Kewarganegaraan\s*[:\.]?\s*([A-Z]+)', text_clean, re.IGNORECASE)
    if Kewarganegaraan_match:
        data["Kewarganegaraan"] = Kewarganegaraan_match.group(1).strip()
        
    # 10. Ekstrak Berlaku Hingga
    berlaku_match = re.search(r'Berlaku\s*Hingga\s*[:\.]?\s*([A-Z0-9\-]+)', text_clean, re.IGNORECASE)
    if berlaku_match:
        data["Berlaku Hingga"] = berlaku_match.group(1).strip()
        
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
                    "No": i + 1,
                    "NIK": f"Error: {e}",
                    "NAMA": uploaded_file.name,
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