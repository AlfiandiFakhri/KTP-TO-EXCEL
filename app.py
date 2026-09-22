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
    
    # Bersihkan teks umum dari salah baca OCR
    text_clean = text.replace("{", "3").replace("}", "").replace("|", "I")
    text_clean = re.sub(r'\s+', ' ', text_clean)
    
    # 1. NIK (Cari angka 16 digit)
    nik_match = re.search(r'(?:NIK|M|K)\s*[:\.]?\s*([0-9\s]{16,20})', text_clean, re.IGNORECASE)
    if nik_match:
        nik_val = re.sub(r'\D', '', nik_match.group(1))
        if len(nik_val) >= 16:
            data["NIK"] = nik_val[:16]
    if not data["NIK"]:
        # Cari angka 16 digit acak di seluruh teks
        all_nums = re.findall(r'\b[0-9]{16}\b', text_clean)
        if all_nums:
            data["NIK"] = all_nums[0]

    # 2. NAMA
    nama_match = re.search(r'Nama\s*(?:Lengkap)?\s*[:\.]?\s*([A-Z\s\.]+?)(?=\s+(?:Tempat|Alamat|Jenis|Gol|Agama|Status|Pekerjaan|Kewarganegaraan|Berlaku)|$)', text_clean, re.IGNORECASE)
    if nama_match:
        data["NAMA"] = nama_match.group(1).strip()

    # 3. Tempat/Tgl Lahir
    ttl_match = re.search(r'(?:Tempat|Tgl|Terpa)?\s*Lahir\s*[:\.]?\s*([A-Z\s\,\-\/0-9]+?)(?=\s+(?:Jenis|Gol|Alamat|Agama|Status)|$)', text_clean, re.IGNORECASE)
    if ttl_match:
        data["Tempat/Tgl Lahir"] = ttl_match.group(1).strip()

    # 4. Jenis Kelamin
    if re.search(r'LAKI|LAK[-_]LAK', text_clean, re.IGNORECASE):
        data["Jenis Kelamin"] = "LAKI-LAKI"
    elif re.search(r'PEREMPUAN|PERENPUAN', text_clean, re.IGNORECASE):
        data["Jenis Kelamin"] = "PEREMPUAN"

    # 5. Alamat
    alamat_match = re.search(r'Alamat\s*[:\.]?\s*([A-Z0-9\s\,\-\/]+?)(?=\s+(?:RT|RW|Desa|Kecamatan|Agama|Status|Pekerjaan)|$)', text_clean, re.IGNORECASE)
    if alamat_match:
        data["Alamat"] = alamat_match.group(1).strip()

    # 6. Agama
    for agama in ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDHA", "KONGHUCU"]:
        if agama in text_clean.upper():
            data["Agama"] = agama
            break

    # 7. Status Perkawinan
    for status in ["KAWIN", "BELUM KAWIN", "CERAI"]:
        if status in text_clean.upper():
            data["Status Perkawinan"] = status
            break

    # 8. Pekerjaan
    pek_match = re.search(r'Pekerjaan\s*[:\.]?\s*([A-Z\s]+?)(?=\s+(?:Kewarganegaraan|Berlaku|Gol)|$)', text_clean, re.IGNORECASE)
    if pek_match:
        data["Pekerjaan"] = pek_match.group(1).strip()

    # 9. Kewarganegaraan
    if "WNI" in text_clean.upper():
        data["Kewarganegaraan"] = "WNI"
    elif "WNA" in text_clean.upper():
        data["Kewarganegaraan"] = "WNA"

    # 10. Berlaku Hingga
    if "SEUMUR HIDUP" in text_clean.upper():
        data["Berlaku Hingga"] = "SEUMUR HIDUP"
    else:
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
                
                hasil = reader.readtext(image_bytes, detail=0)
                teks_gabungan = " ".join(hasil)
                
                parsed_data = parse_ktp_text(teks_gabungan)
                
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
        
        status_text.text("Semua KTP berhasil diproses!")
        st.success("Selesai!")
        
        df_hasil = pd.DataFrame(data_hasil)
        st.dataframe(df_hasil)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hasil.to_excel(writer, index=False, sheet_name='Format KTP')
        excel_data = output.getvalue()
        
        st.download_button(
            label="Unduh Excel Sesuai Format KTP (.xlsx)",
            data=excel_data,
            file_name="Data_Rekap_Sesuai_Format_KTP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )