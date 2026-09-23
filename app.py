import streamlit as st
import easyocr
import pandas as pd
from PIL import Image
import io
import re
import difflib

# --- KOMPONEN UI ---
st.title("Aplikasi Batch Scan & Format KTP ke Excel")
st.write("Ekstraksi KTP Cerdas: Global Pencarian NIK/Nama, Pembersih Watermark, & Multi-Format Gambar.")

@st.cache_resource
def load_reader():
    return easyocr.Reader(['id', 'en'], gpu=False)

with st.spinner("Memuat sistem AI pembaca KTP (Proses ini mungkin memakan waktu beberapa menit saat pertama kali)..."):
    reader = load_reader()

# DATABASE NAMA KOTA INDONESIA
DAFTAR_KOTA_INDO = [
    "CIREBON", "JAKARTA", "BANDUNG", "SEMARANG", "SURABAYA", "YOGYAKARTA", 
    "MEDAN", "PALEMBANG", "MAKASSAR", "DENPASAR", "MALANG", "BOGOR", "BEKASI", 
    "DEPOK", "TANGERANG", "SURAKARTA", "TASIKMALAYA", "GARUT", "INDRAMAYU", 
    "MAJALENGKA", "KUNINGAN", "BREBES", "TEGAL", "PEKALONGAN", "BANYUMAS", 
    "PURWOKERTO", "CILACAP", "MAGELANG", "KEDIRI", "MADIUN", "PASURUAN"
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
    
    # 1. PENCARIAN LANGSUNG NIK (GLOBAL REGEX)
    nik_global_match = re.search(r'\b\d{16}\b', text_clean)
    if nik_global_match:
        data["NIK"] = nik_global_match.group(0)

    # 2. PENCARIAN LANGSUNG NAMA
    nama_match = re.search(r'(?i)\b(?:Nama|Nara|Narna|Nam)\b\s*[:\s]*([A-Z\s\.\,\']+?)(?=\s+(?:Tempat|Tgl|Lahir|Jenis|Alamat|Agama|$))', text_clean)
    if nama_match:
        nama_bersih = re.sub(r'^[\:\.\-\;\_]+', '', nama_match.group(1)).strip().upper()
        data["NAMA"] = nama_bersih
    
    kamus_typo_nama = {r'\bOWI\b': 'DWI', r'\bUTAIYANTI\b': 'UTAMIYANTI'}
    for salah, benar in kamus_typo_nama.items():
        data["NAMA"] = re.sub(salah, benar, data["NAMA"], flags=re.IGNORECASE)

    # Pembersih Watermark Latar Belakang KTP Lama
    watermark_patterns = [r'KARTU\s+TANDA\s+PENDUDUK', r'PENDUDUK\s+INDONESIA', r'REPUBLIK\s+INDONESIA']
    for pat in watermark_patterns:
        text_clean = re.sub(pat, ' ', text_clean, flags=re.IGNORECASE)

    # Standarisasi TAG Pembatas untuk Field Lainnya
    text_clean = re.sub(r'(?i)(Terpa.*?Lahir|Tenpat.*?Lahir|Tempat.*?Lahir|Tompat.*?Lahir|Tornpat.*?Lahir|Tompautol|Tgl.*?Lahir|Tcl.*?Lahis|Tempat|Tompat|Tornpat)', ' _TTL_ ', text_clean)
    text_clean = re.sub(r'(?i)(Jenis.*?Kelamin|Jenis.*?kel|Jens.*?Keanin)', ' _JK_ ', text_clean)
    text_clean = re.sub(r'(?i)(Gd Darah|Gol.*?Darah|Golongan.*?Darah)', ' _GOL_ ', text_clean)
    text_clean = re.sub(r'(?i)(Alamat|Aamat|Nlamal|Nemal|Alamet)', ' _ALAMAT_ ', text_clean)
    text_clean = re.sub(r'(?i)(RHRW|RTRW|RT.*?RW|BTRW|RT\s*I\s*RW)', ' _RTRW_ ', text_clean)
    text_clean = re.sub(r'(?i)(Kelurahan|Desa|Kel.*?Desa|KeDesa|Kel|Des)', ' _KELD_ ', text_clean)
    text_clean = re.sub(r'(?i)(Kecamatan|Kec)', ' _KEC_ ', text_clean)
    text_clean = re.sub(r'(?i)(Agama|Agare|Agarna)', ' _AGAMA_ ', text_clean)
    text_clean = re.sub(r'(?i)(Status.*?Perkawinan|Status.*?Perkavnan|Status.*?Kawin|Status)', ' _STATUS_ ', text_clean)
    text_clean = re.sub(r'(?i)(Pekerjaan|Pekerjaari|Pekerja.*?n|Pokenaan|Pokena.*?n)', ' _PEKERJAAN_ ', text_clean)
    text_clean = re.sub(r'(?i)(Kewvarganegaraan|Kewaranegaraan|Kewarganegaraan|Kewarganegara.*?n|Kewarga.*?n)', ' _KWN_ ', text_clean)
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

    # -- TTL --
    ttl_raw = extract_between('_TTL_', ['_JK_', '_GOL_', '_ALAMAT_'], text_clean)
    ttl_raw = re.sub(r'(?i)(TGI|TGL|TCL|TEMPAT|TOMPAT|TORNPAT|TOMPAUTOL|TERPA|LAHIR|LAHIS|TEMPAL)\s*', '', ttl_raw).strip()
    date_match = re.search(r'(\d{2})[-/\s\.]*(\d{2})[-/\s\.]*(\d{4})', ttl_raw)
    if date_match:
        tgl_format_rapi = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        kota_typo = re.sub(r'[^A-Z]', '', ttl_raw[:date_match.start()]).strip()
        kota_asli = koreksi_nama_kota(kota_typo)
        data["Tempat/Tgl Lahir"] = f"{kota_asli}, {tgl_format_rapi}" if kota_asli else tgl_format_rapi
    else:
        data["Tempat/Tgl Lahir"] = ttl_raw

    # -- JENIS KELAMIN --
    jk_raw = extract_between('_JK_', ['_GOL_', '_ALAMAT_', '_RTRW_'], text_clean)
    if re.search(r'LAK|EAK|AKI', jk_raw): data["Jenis Kelamin"] = "LAKI-LAKI"
    elif re.search(r'PER|PUAN|EMP|PEREPU', jk_raw): data["Jenis Kelamin"] = "PEREMPUAN"
        
    # -- ALAMAT --
    alamat_jalan = extract_between('_ALAMAT_', ['_RTRW_', '_KELD_', '_KEC_', '_AGAMA_'], text_clean)
    kamus_alamat = {
        r'\b(?:L|J|JLN)\b\s*': 'JL. ', r'\b(?:UUNG|UJUNS)\b': 'UJUNG',
        r'\b(?:FARAPAN)\b': 'HARAPAN', r'\b(?:GGTANA|GG\s*TANA|66\s*TANAH|CANG)\b': 'GG. TANAH ',
        r'\b(?:EARU|BARU7|BARU\?)\b': 'BARU', r'\b(?:NO|N0|NOMOR)\b\s*[\?\7]': 'NO. 2', 
        r'\b(?:NO|N0|NOMOR)\b\s*': 'NO. ', r'\bKESAVBI\b': 'KESAMBI'
    }
    for pola, perbaikan in kamus_alamat.items():
        alamat_jalan = re.sub(pola, perbaikan, alamat_jalan, flags=re.IGNORECASE)
    alamat_jalan = re.sub(r'\s+', ' ', alamat_jalan).strip() 
    
    rt_rw_raw = extract_between('_RTRW_', ['_KELD_', '_KEC_', '_AGAMA_'], text_clean)
    rt_rw_match = re.search(r'(\d{1,3})[^\d]*(\d{1,3})', rt_rw_raw)
    rt_rw_final = f"{rt_rw_match.group(1).zfill(3)}/{rt_rw_match.group(2).zfill(3)}" if rt_rw_match else rt_rw_raw
    
    kel_desa_raw = extract_between('_KELD_', ['_KEC_', '_AGAMA_'], text_clean)
    kel_desa_final = re.sub(r'[^A-Z\s\-]', '', kel_desa_raw).strip().replace("KESAVBI", "KESAMBI")
    
    kec_raw = extract_between('_KEC_', ['_AGAMA_', '_STATUS_'], text_clean)
    kec_final = re.sub(r'[^A-Z\s\-]', '', kec_raw).strip().replace("KESAVBI", "KESAMBI")
    
    alamat_lengkap = alamat_jalan
    if rt_rw_final: alamat_lengkap += f" RT/RW {rt_rw_final}"
    if kel_desa_final: alamat_lengkap += f" KEL/DESA {kel_desa_final}"
    if kec_final: alamat_lengkap += f" KECAMATAN {kec_final}"
    data["Alamat"] = alamat_lengkap.strip()
    
    # -- AGAMA --
    agama_raw = extract_between('_AGAMA_', ['_STATUS_', '_PEKERJAAN_', '_KWN_'], text_clean)
    if re.search(r'ISLAM|1SLAM|AMIN', agama_raw): data["Agama"] = "ISLAM"
    elif re.search(r'KRISTEN', agama_raw): data["Agama"] = "KRISTEN"
    elif re.search(r'KATOLIK', agama_raw): data["Agama"] = "KATOLIK"
    elif re.search(r'HINDU', agama_raw): data["Agama"] = "HINDU"
    elif re.search(r'BUDHA|BUDDHA', agama_raw): data["Agama"] = "BUDHA"
    elif re.search(r'KONGHUCU', agama_raw): data["Agama"] = "KONGHUCU"
    else: data["Agama"] = ""
            
    # -- STATUS PERKAWINAN --
    status_raw = extract_between('_STATUS_', ['_PEKERJAAN_', '_KWN_', '_BERLAKU_'], text_clean)
    if re.search(r'BELUM\s*KAW|BELUM', status_raw): data["Status Perkawinan"] = "BELUM KAWIN"
    elif re.search(r'CERAI\s*MATI', status_raw): data["Status Perkawinan"] = "CERAI MATI"
    elif re.search(r'CERAI\s*HIDUP', status_raw): data["Status Perkawinan"] = "CERAI HIDUP"
    elif re.search(r'KAW|KAV|KAW1N', status_raw): data["Status Perkawinan"] = "KAWIN"
    else: data["Status Perkawinan"] = ""
            
    # -- PEKERJAAN --
    pekerjaan_raw = extract_between('_PEKERJAAN_', ['_KWN_', '_BERLAKU_'], text_clean)
    date_loc_match = re.search(r'(\d{2}[\-\/\.]\d{2}[\-\/\.]\d{4}|KOTA|KABUPATEN|KAB\.|PROV|GUBERNUR)', pekerjaan_raw)
    if date_loc_match: pekerjaan_raw = pekerjaan_raw[:date_loc_match.start()]
    data["Pekerjaan"] = re.sub(r'[^A-Z\s\(\)]+$', '', pekerjaan_raw.strip()).strip()

    # -- KEWARGANEGARAAN & BERLAKU --
    kwn_raw = extract_between('_KWN_', ['_BERLAKU_'], text_clean)
    if "WNI" in kwn_raw or "WN" in kwn_raw: data["Kewarganegaraan"] = "WNI"
    elif "WNA" in kwn_raw: data["Kewarganegaraan"] = "WNA"
    else: data["Kewarganegaraan"] = ""
        
    berlaku_raw = extract_between('_BERLAKU_', ['_SEUMUR_', 'ON'], text_clean)
    if "SEUMUR HIDUP" in text_clean.upper() or "SEUMUR" in berlaku_raw: data["Berlaku Hingga"] = "SEUMUR HIDUP"
    else: data["Berlaku Hingga"] = berlaku_raw

    return data

# --- KOMPONEN UNGGAH & PROSES ---
uploaded_files = st.file_uploader(
    "Pilih atau Seret (Drag & Drop) Banyak Foto KTP Sekaligus", 
    type=['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif'], 
    accept_multiple_files=True
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
                if image.mode in ("RGBA", "P"): 
                    image = image.convert("RGB")
                
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='JPEG')
                
                hasil = reader.readtext(image_bytes.getvalue(), detail=0)
                parsed_data = parse_ktp_text(" ".join(hasil))
                
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
            df_hasil.to_excel(writer, index=False, sheet_name='Format KTP')
        
        st.download_button(
            "Unduh Excel Sesuai Format KTP (.xlsx)",
            data=output.getvalue(), file_name="Data_Rekap_Sesuai_Format_KTP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
