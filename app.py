import streamlit as st
import easyocr
import pandas as pd
from PIL import Image, ImageOps
import io
import re
import difflib

st.title("Aplikasi Batch Scan & Format KTP ke Excel")
st.write("Ekstraksi KTP Cerdas: Stabil, Ringan, dan Otomatis.")

@st.cache_resource
def load_reader():
    # Menggunakan CPU dan menonaktifkan model paragraf yang memakan banyak RAM
    return easyocr.Reader(['id'], gpu=False, model_storage_directory='/tmp')

with st.spinner("Memuat sistem AI pembaca KTP..."):
    reader = load_reader()

DAFTAR_KOTA_INDO = [
    "CIREBON", "JAKARTA", "BANDUNG", "SEMARANG", "SURABAYA", "YOGYAKARTA", 
    "MEDAN", "PALEMBANG", "MAKASSAR", "DENPASAR", "MALANG", "BOGOR", "BEKASI", 
    "DEPOK", "TANGERANG", "SURAKARTA", "TASIKMALAYA", "GARUT", "INDRAMAYU", 
    "MAJALENGKA", "KUNINGAN", "BREBES", "TEGAL", "PEKALONGAN", "BANYUMAS"
]

def koreksi_nama_kota(kota_typo):
    if not kota_typo: return ""
    koreksi = difflib.get_close_matches(kota_typo, DAFTAR_KOTA_INDO, n=1, cutoff=0.35)
    return koreksi[0] if koreksi else kota_typo

def parse_ktp_text(text):
    data = {
        "NIK": "", "NAMA": "", "Tempat/Tgl Lahir": "", "Jenis Kelamin": "",
        "Alamat": "", "Agama": "", "Status Perkawinan": "", "Pekerjaan": "",
        "Kewarganegaraan": "", "Berlaku Hingga": ""
    }
    
    text_clean = text.replace("{", "3").replace("}", "").replace("|", "I").replace("?", "7").replace("€", "E")
    text_clean = re.sub(r'\s+', ' ', text_clean)
    
    text_clean = re.sub(r'(?i)\b(NIK)\b', ' _NIK_ ', text_clean)
    text_clean = re.sub(r'(?i)\b(Nara|Narna|Nam|Nama)\b\s*(?:Lengkap)?', ' _NAMA_ ', text_clean)
    text_clean = re.sub(r'(?i)(Terpa.*?Lahir|Tenpat.*?Lahir|Tempat.*?Lahir|Tgl.*?Lahir|Tcl.*?Lahis)', ' _TTL_ ', text_clean)
    text_clean = re.sub(r'(?i)(Jenis.*?Kelamin|Jenis.*?kel|Jens.*?Keanin)', ' _JK_ ', text_clean)
    text_clean = re.sub(r'(?i)(Gd Darah|Gol.*?Darah|Golongan.*?Darah)', ' _GOL_ ', text_clean)
    text_clean = re.sub(r'(?i)(Aamat|Nlamal|Nemal|Alamat)', ' _ALAMAT_ ', text_clean)
    text_clean = re.sub(r'(?i)(RHRW|RTRW|RT.*?RW|BTRW)', ' _RTRW_ ', text_clean)
    text_clean = re.sub(r'(?i)(KeDesa|Kel.*?Desa|Desa.*?Kelurahan|Desa)', ' _KELD_ ', text_clean)
    text_clean = re.sub(r'(?i)(Kecamatan|Kec)', ' _KEC_ ', text_clean)
    text_clean = re.sub(r'(?i)(Agama|Agare)', ' _AGAMA_ ', text_clean)
    text_clean = re.sub(r'(?i)(Status.*?Perkavnan|Status.*?Kawin|Status.*?Perkawinan)', ' _STATUS_ ', text_clean)
    text_clean = re.sub(r'(?i)(Pekerjaan)', ' _PEKERJAAN_ ', text_clean)
    text_clean = re.sub(r'(?i)(Kewvarganegaraan|Kewaranegaraan)', ' _KWN_ ', text_clean)
    text_clean = re.sub(r'(?i)(Berlaku.*?Hingga|Benaku.*?Hingga)', ' _BERLAKU_ ', text_clean)

    text_clean = re.sub(r'\s*:\s*', ' ', text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean)
    
    def extract_between(start_tag, next_tags, text):
        pattern = start_tag + r'\s*(.*?)\s*(?:' + '|'.join(next_tags) + '|$)'
        match = re.search(pattern, text)
        if match:
            res = match.group(1).strip()
            return re.sub(r'^[\:\.\-\;\_]+', '', res).strip().upper()
        return ""

    nik_raw = extract_between('_NIK_', ['_NAMA_', '_TTL_'], text_clean)
    nik_val = re.sub(r'\D', '', nik_raw)
    data["NIK"] = nik_val[:16] if len(nik_val) >= 16 else (re.findall(r'\b[0-9]{16}\b', text_clean)[0] if re.findall(r'\b[0-9]{16}\b', text_clean) else "")
    data["NAMA"] = extract_between('_NAMA_', ['_TTL_', '_JK_', '_ALAMAT_'], text_clean)
    
    ttl_raw = extract_between('_TTL_', ['_JK_', '_GOL_', '_ALAMAT_'], text_clean)
    ttl_raw = re.sub(r'(?i)(TGI|TGL|TCL|TEMPAT|TERPA|LAHIR|LAHIS|TEMPAL)\s*', '', ttl_raw).strip()
    date_match = re.search(r'(\d{2})[-/\s\.]*(\d{2})[-/\s\.]*(\d{4})', ttl_raw)
    if date_match:
        tgl_format_rapi = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        kota_typo = re.sub(r'[^A-Z]', '', ttl_raw[:date_match.start()]).strip()
        kota_asli = koreksi_nama_kota(kota_typo)
        data["Tempat/Tgl Lahir"] = f"{kota_asli}, {tgl_format_rapi}" if kota_asli else tgl_format_rapi
    else:
        data["Tempat/Tgl Lahir"] = ttl_raw

    jk_raw = extract_between('_JK_', ['_GOL_', '_ALAMAT_', '_RTRW_'], text_clean)
    if re.search(r'LAK|EAK|AKI', jk_raw): data["Jenis Kelamin"] = "LAKI-LAKI"
    elif re.search(r'PER|PUAN|EMP', jk_raw): data["Jenis Kelamin"] = "PEREMPUAN"
        
    alamat_jalan = extract_between('_ALAMAT_', ['_RTRW_', '_KELD_', '_KEC_', '_AGAMA_'], text_clean)
    kamus_alamat = {
        r'\b(?:L|J|JLN)\b\s*': 'JL. ',
        r'\b(?:UUNG|UJUNS)\b': 'UJUNG',
        r'\b(?:FARAPAN)\b': 'HARAPAN',
        r'\b(?:GGTANA|GG\s*TANA|66\s*TANAH|CANG)\b': 'GG. TANAH ',
        r'\b(?:EARU|BARU7|BARU\?)\b': 'BARU',
        r'\b(?:NO|N0|NOMOR)\b\s*[\?\7]': 'NO. 2',
        r'\b(?:NO|N0|NOMOR)\b\s*': 'NO. '
    }
    for pola, perbaikan in kamus_alamat.items():
        alamat_jalan = re.sub(pola, perbaikan, alamat_jalan, flags=re.IGNORECASE)
    alamat_jalan = re.sub(r'\s+', ' ', alamat_jalan).strip()
    
    rt_rw_raw = extract_between('_RTRW_', ['_KELD_', '_KEC_', '_AGAMA_'], text_clean)
    rt_rw_match = re.search(r'(\d{1,3})[^\d]*(\d{1,3})', rt_rw_raw)
    rt_rw_final = f"{rt_rw_match.group(1).zfill(3)}/{rt_rw_match.group(2).zfill(3)}" if rt_rw_match else rt_rw_raw
    
    kel_desa_raw = extract_between('_KELD_', ['_KEC_', '_AGAMA_'], text_clean)
    kel_desa_final = re.sub(r'[^A-Z\s\-]', '', kel_desa_raw).strip()
    
    kec_raw = extract_between('_KEC_', ['_AGAMA_', '_STATUS_'], text_clean)
    kec_final = re.sub(r'[^A-Z\s\-]', '', kec_raw).strip()
    
    alamat_lengkap = alamat_jalan
    if rt_rw_final: alamat_lengkap += f" RT/RW {rt_rw_final}"
    if kel_desa_final: alamat_lengkap += f" KEL/DESA {kel_desa_final}"
    if kec_final: alamat_lengkap += f" KECAMATAN {kec_final}"
    data["Alamat"] = alamat_lengkap.strip()
    
    agama_raw = extract_between('_AGAMA_', ['_STATUS_', '_PEKERJAAN_'], text_clean)
    for agm in ["ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDHA", "KONGHUCU"]:
        if agm in agama_raw: data["Agama"] = agm; break
            
    status_raw = extract_between('_STATUS_', ['_PEKERJAAN_', '_KWN_', '_BERLAKU_'], text_clean)
    for stts in ["BELUM KAWIN", "KAWIN", "CERAI MATI", "CERAI HIDUP"]:
        if stts in status_raw: data["Status Perkawinan"] = stts; break
            
    pekerjaan_raw = extract_between('_PEKERJAAN_', ['_KWN_', '_BERLAKU_'], text_clean)
    date_loc_match = re.search(r'(\d{2}[\-\/\.]\d{2}[\-\/\.]\d{4}|KOTA|KABUPATEN|KAB\.|PROV|GUBERNUR)', pekerjaan_raw)
    if date_loc_match: pekerjaan_raw = pekerjaan_raw[:date_loc_match.start()]
    data["Pekerjaan"] = re.sub(r'[^A-Z\s]+$', '', pekerjaan_raw.strip()).strip()

    kwn_raw = extract_between('_KWN_', ['_BERLAKU_'], text_clean)
    if "WNI" in kwn_raw or "WN" in kwn_raw: data["Kewarganegaraan"] = "WNI"
    elif "WNA" in kwn_raw: data["Kewarganegaraan"] = "WNA"
        
    berlaku_raw = extract_between('_BERLAKU_', ['_SEUMUR_', 'ON'], text_clean)
    if "SEUMUR HIDUP" in text_clean.upper() or "SEUMUR" in berlaku_raw: data["Berlaku Hingga"] = "SEUMUR HIDUP"
    else: data["Berlaku Hingga"] = berlaku_raw

    return data

uploaded_files = st.file_uploader(
    "Pilih atau Seret (Drag & Drop) Banyak Foto KTP Sekaligus", 
    type=['png', 'jpg', 'jpeg'], accept_multiple_files=True
)

if uploaded_files:
    if st.button("Mulai Proses & Format ke Tabel KTP"):
        data_hasil = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_file = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Memproses file {i+1} dari {total_file}: {uploaded_file.name}")
            try:
                image = Image.open(uploaded_file)
                image = ImageOps.exif_transpose(image)
                
                sudut_rotasi = [0, 90, 180, 270]
                teks_terbaik = ""
                max_score = -1
                
                for angle in sudut_rotasi:
                    img_rotated = image.rotate(angle, expand=True) if angle != 0 else image
                    image_bytes = io.BytesIO()
                    img_rotated.save(image_bytes, format='JPEG')
                    
                    hasil = reader.readtext(image_bytes.getvalue(), detail=0)
                    teks_gabungan = " ".join(hasil)
                    
                    score = 0
                    if re.search(r'(?i)NIK', teks_gabungan): score += 3
                    if re.search(r'(?i)PROVINSI|KOTA', teks_gabungan): score += 2
                    if re.search(r'(?i)ALAMAT|AGAMA', teks_gabungan): score += 2
                    score += len(hasil)
                    
                    if score > max_score:
                        max_score = score
                        teks_terbaik = teks_gabungan
                
                parsed_data = parse_ktp_text(teks_terbaik)
                row_data = {"No": i + 1}
                row_data.update(parsed_data)
                data_hasil.append(row_data)
                
            except Exception as e:
                data_hasil.append({"No": i + 1, "NIK": f"Error: {e}", "NAMA": uploaded_file.name})
            
            progress_bar.progress((i + 1) / total_file)
        
        status_text.text("Semua KTP berhasil diproses!")
        st.success("Proses ekstraksi massal selesai!")
        
        df_hasil = pd.DataFrame(data_hasil)
        st.dataframe(df_hasil)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hasil.to_excel(writer, index=False, sheet_name='Format KTP')
        
        st.download_button(
            "Unduh Excel Sesuai Format KTP (.xlsx)",
            data=output.getvalue(), file_name="Data_Rekap_Sesuai_Format_KTP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )