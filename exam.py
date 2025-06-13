import streamlit as st
import pandas as pd
import io
import os

st.set_page_config(page_title="Sınav Yerleştirme Analiz", layout="wide")  # <-- EN BAŞTA OLMALI

# --- LOGO EKLEME (En üstte ortada, URL ile) ---
st.markdown(
    """
    <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 10px;">
        <img src="https://e-campus.isikun.edu.tr/Content/img/iu_logo-mavi.png" width="660" style="display:block; margin:auto;"/>
    </div>
    """,
    unsafe_allow_html=True
)
# --- LOGO EKLEME SONU ---

st.markdown(
    """
    <style>
    .main {background-color: #f8f9fa;}
    .stButton>button {background-color: #4F8BF9; color: white;}
    .stDownloadButton>button {background-color: #43aa8b; color: white;}
    .stDataFrame {background-color: #fff;}
    .stTextInput>div>div>input {background-color: #f1f3f6;}
    .ekle-btn {background-color: #43aa8b !important; color: white !important;}
    .sil-btn {background-color: #e63946 !important; color: white !important;}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background: #f8f9fa; padding: 5px 0 5px 0; border-top: 1px solid #e0e0e0; z-index: 999;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎓 Sınav Yerleştirme Analiz Uygulaması")
st.write("Excel dosyanızı yükleyin, analiz için birden fazla parametre ekleyin ve toplu analiz yapın.")

uploaded_file = st.file_uploader("📄 Yerleştirme Veri Dosyası (Excel)", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()
    st.success(f"Yüklenen veri: {df.shape[0]} satır, {df.shape[1]} sütun")
    with st.expander("Yüklenen Veriyi Göster", expanded=False):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔎 Analiz Parametreleri")

    puan_turu_options = []
    if "Puan Türü" in df.columns:
        puan_turu_options = sorted(df["Puan Türü"].dropna().astype(str).str.strip().str.upper().unique())
    puan_turu = st.selectbox(
        "Puan Türü Seçiniz",
        options=puan_turu_options if puan_turu_options else ["Seçiniz"],
        index=0 if puan_turu_options else 0,
        key="puan_turu"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        ogr_siralama = st.text_input("Öğrenci Sıralaması", value="", placeholder="örn: 15000", key="ogr_siralama")
    with col2:
        sinir = st.text_input("Taban Sıralama Sınırı", value="", placeholder="örn: 20000", key="sinir")
    with col3:
        riskli_t = st.text_input("Riskli T (opsiyonel)", value="0", placeholder="örn: 1000", key="riskli_t")

    # --- PARAMETRELERİ EKLEME VE GÖSTERME ---
    if "eklenenler" not in st.session_state:
        st.session_state.eklenenler = []

    def temizle_sayi(s):
        if isinstance(s, str):
            s = s.replace('.', '').replace(',', '')
        try:
            return int(s)
        except:
            return 0

    def etiketle(ogr_siralama, taban, z_riskli):
        try:
            ogr_siralama = int(ogr_siralama)
            taban = int(taban)
        except:
            return "Bilinmiyor"
        # Etiket mantığı:
        # - taban < z_riskli: "Uygun"
        # - z_riskli <= taban < ogr_siralama: "Riskli"
        # - taban < z_riskli: "Uygun"
        # - taban >= ogr_siralama: "Uygun"
        # - taban >= z_riskli and taban < ogr_siralama: "Riskli"
        if taban >= ogr_siralama:
            return "Uygun"
        elif z_riskli is not None and taban >= z_riskli:
            return "Riskli"
        else:
            return "Uygunsuz"

    st.markdown(
        """
        <style>
        .param-table th, .param-table td {padding: 6px 12px;}
        </style>
        """,
        unsafe_allow_html=True
    )

    col_ekle, col_bos = st.columns([1, 5])
    with col_ekle:
        if st.button("➕ Parametreyi Ekle", key="ekle_btn"):
            if puan_turu and puan_turu != "Seçiniz" and ogr_siralama and sinir:
                st.session_state.eklenenler.append({
                    "puan_turu": puan_turu,
                    "ogr_siralama": ogr_siralama,
                    "sinir": sinir,
                    "riskli_t": riskli_t
                })
            else:
                st.warning("Lütfen puan türü, öğrenci sıralaması ve taban sıralama sınırı giriniz.")

    if st.session_state.eklenenler:
        st.markdown("#### Eklenen Parametreler")
        param_df = pd.DataFrame(st.session_state.eklenenler)
        # Sil butonları için tabloyu elle çiz
        for i, row in param_df.iterrows():
            cols = st.columns([2, 2, 2, 2, 1])
            cols[0].write(f"**Puan Türü:** {row['puan_turu']}")
            cols[1].write(f"**Öğrenci Sıralaması:** {row['ogr_siralama']}")
            cols[2].write(f"**Taban Sıralama:** {row['sinir']}")
            cols[3].write(f"**Riskli T:** {row['riskli_t']}")
            if cols[4].button("❌ Sil", key=f"sil_{i}"):
                st.session_state.eklenenler.pop(i)
                st.rerun()  # Düzeltildi: st.experimental_rerun() yerine st.rerun()
        st.markdown("---")

    st.markdown("### 📊 Analiz Sonucu")

    with st.container():
        if st.button("Tümünü Analiz Et", use_container_width=True, key="analiz_et"):
            result = []
            for p in st.session_state.eklenenler:
                ogr_siralama_int = temizle_sayi(p["ogr_siralama"])
                sinir_int = temizle_sayi(p["sinir"])
                riskli_t_int = temizle_sayi(p["riskli_t"])
                z = ogr_siralama_int - sinir_int
                z_riskli = z - riskli_t_int if riskli_t_int else None

                df_filtered = df.copy()
                if p["puan_turu"] and 'Puan Türü' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['Puan Türü'].astype(str).str.strip().str.upper() == p["puan_turu"]]
                bos_veya_eksi_bolumler = []
                if 'En Düşük Sıralama' in df_filtered.columns:
                    def kontrol_et(x):
                        try:
                            x_sayi = int(str(x).replace('.', '').replace(',', ''))
                        except:
                            return False
                        # Eşleştirme mantığı:
                        # z_riskli varsa: x_sayi > z_riskli
                        # yoksa: x_sayi > z
                        if z_riskli is not None:
                            return x_sayi > z_riskli
                        else:
                            return x_sayi > z
                    df_filtered_main = df_filtered[df_filtered['En Düşük Sıralama'].apply(kontrol_et)]
                    bos_veya_eksi_bolumler = df_filtered[df_filtered['En Düşük Sıralama'].apply(lambda x: pd.isna(x) or str(x).strip() == "" or str(x).strip() == "-")]
                else:
                    df_filtered_main = df_filtered

                # Normal filtrelenmiş bölümler
                for _, row in df_filtered_main.iterrows():
                    program_adi = str(row.get('Program Adı', '')).strip()
                    burs = str(row.get('Burs/İndirim', '')).strip() if 'Burs/İndirim' in row else ''
                    if not burs:
                        for burs_kw in ["Burslu", "Ücretli", "%50 İndirimli", "%25 İndirimli", "%75 İndirimli", "%100 Burslu"]:
                            if burs_kw.lower() in program_adi.lower():
                                burs = burs_kw
                                break
                        if not burs:
                            import re
                            m = re.search(r'(%\d{1,3}\s*İndirimli)', program_adi, re.IGNORECASE)
                            if m:
                                burs = m.group(1)
                    ucret = row['Ücret'] if 'Ücret' in row and pd.notnull(row['Ücret']) else ''
                    if ucret:
                        try:
                            ucret_num = float(str(ucret).replace('.', '').replace(',', '').replace('₺','').strip())
                            ucret = f"{ucret_num:,.0f}".replace(",", ".") + " TL"
                        except:
                            ucret = str(ucret) + " TL"
                    if "(İngilizce)" in program_adi or "(ingilizce)" in program_adi:
                        dil = "EN"
                    else:
                        dil = "TR"
                    etiket = etiketle(ogr_siralama_int, row.get('En Düşük Sıralama', 0), z_riskli)
                    result.append({
                        'Bölüm Adı': program_adi,
                        'Puan Türü': row.get('Puan Türü', ''),
                        'Burs Oranı': burs,
                        'Taban Sıralama': row.get('En Düşük Sıralama', ''),
                        'Taban Puan': row.get('Taban Puan', ''),
                        'Tavan Puan': row.get('Tavan Puan', ''),
                        'Ücret': ucret,
                        'Dil': dil,
                        'Etiket': etiket,
                        'Riskli T': riskli_t_int,
                        'Z Riskli': z_riskli if z_riskli is not None else "",
                        'Parametre': f"{p['puan_turu']} / {p['ogr_siralama']} / {p['sinir']} / {p['riskli_t']}"
                    })

                # Boş veya '-' olan bölümler (tekrar eklenmesin diye ayıkla)
                if 'En Düşük Sıralama' in df_filtered.columns:
                    for _, row in bos_veya_eksi_bolumler.iterrows():
                        program_adi = str(row.get('Program Adı', '')).strip()
                        burs = str(row.get('Burs/İndirim', '')).strip() if 'Burs/İndirim' in row else ''
                        if not burs:
                            for burs_kw in ["Burslu", "Ücretli", "%50 İndirimli", "%25 İndirimli", "%75 İndirimli", "%100 Burslu"]:
                                if burs_kw.lower() in program_adi.lower():
                                    burs = burs_kw
                                    break
                            if not burs:
                                import re
                                m = re.search(r'(%\d{1,3}\s*İndirimli)', program_adi, re.IGNORECASE)
                                if m:
                                    burs = m.group(1)
                        ucret = row['Ücret'] if 'Ücret' in row and pd.notnull(row['Ücret']) else ''
                        if ucret:
                            try:
                                ucret_num = float(str(ucret).replace('.', '').replace(',', '').replace('₺','').strip())
                                ucret = f"{ucret_num:,.0f}".replace(",", ".") + " TL"
                            except:
                                ucret = str(ucret) + " TL"
                        if "(İngilizce)" in program_adi or "(ingilizce)" in program_adi:
                            dil = "EN"
                        else:
                            dil = "TR"
                        etiket = etiketle(ogr_siralama_int, row.get('En Düşük Sıralama', 0), z_riskli)
                        if not any(r['Bölüm Adı'] == program_adi and r['Taban Sıralama'] == row.get('En Düşük Sıralama', '') for r in result):
                            result.append({
                                'Bölüm Adı': program_adi,
                                'Puan Türü': row.get('Puan Türü', ''),
                                'Burs Oranı': burs,
                                'Taban Sıralama': row.get('En Düşük Sıralama', ''),
                                'Taban Puan': row.get('Taban Puan', ''),
                                'Tavan Puan': row.get('Tavan Puan', ''),
                                'Ücret': ucret,
                                'Dil': dil,
                                'Etiket': etiket,
                                'Riskli T': riskli_t_int,
                                'Z Riskli': z_riskli if z_riskli is not None else "",
                                'Parametre': f"{p['puan_turu']} / {p['ogr_siralama']} / {p['sinir']} / {p['riskli_t']}"
                            })

            if not result:
                result = [{'Bölüm Adı': 'Sonuç bulunamadı'}]
            result_df = pd.DataFrame(result)
            st.dataframe(result_df, use_container_width=True, hide_index=True)

            def to_excel(df):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sonuclar')
                return output.getvalue()

            st.download_button(
                label="⬇️ Excel Olarak İndir",
                data=to_excel(result_df),
                file_name="analiz_sonuclari.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# --- ALT BİLGİ ve LOGO (footer, URL ile) ---
footer_logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQBgIsV4SxpHYHByQlUC97x6Pkp-iizTssT2A&s"
st.markdown(
    f"""
    <div class="footer" style="text-align:left;">
        <img src="{footer_logo_url}" width="30" style="vertical-align:middle;margin-right:10px;">
        <span style="font-size:14px;vertical-align:middle;">
            IŞIK ÜNİVERSİTESİ ÖĞRENCİ İŞLERİ DAİRE BAŞKANLIĞI
        </span>
    </div>
    """,
    unsafe_allow_html=True
)


#    cd C:\Users\Cihan.TAZEOZ\Desktop\exam_project
#    streamlit run exam.py
# 2. Gerekli paketler 
#    pip install streamlit pandas openpyxl




# 4. Tarayıcıda otomatik açılmazsa, terminalde verilen URL'yi (genellikle http://localhost:8501) kopyalayıp tarayıcıya yapıştırın.

# Not: Uygulama sadece streamlit ile çalışır, python exam.py ile çalışmaz!

# PYINSTALLER İÇİN NOTLAR:
# 1. Streamlit uygulamaları klasik Flask gibi .exe'ye gömülüp tek başına çalıştırılamaz.
# 2. PyInstaller ile .exe yapmak teknik olarak mümkündür fakat:
#    - Streamlit, arka planda bir web sunucusu başlatır ve tarayıcıda çalışır.
#    - .exe dosyası çalışınca yine bir web sunucusu başlatır ve kullanıcıdan tarayıcıda açmasını ister.
#    - Streamlit uygulamasında "templates" ve "index.html" gibi dosyalar kullanılmaz, çünkü arayüz Python kodunda yazılır.
#    - Eğer Flask uygulaması olsaydı, templates klasörü ve index.html gömülürdü.
# 3. Eğer yine de .exe yapmak isterseniz:
#    - Tüm statik dosyalar (ör: static klasörü, resimler) ve Python dosyası aynı dizinde olmalı.
#    - PyInstaller ile aşağıdaki komutu kullanın:

# pyinstaller --add-data "static;static" --onefile exam.py

# 4. Kullanıcıya bilgi verin:
#    - .exe dosyasını çalıştırınca terminalde aşağıdaki komutun otomatik çalışmasını sağlayamazsınız:
#      streamlit run exam.py
#    - .exe dosyası çalışınca, kodun başında os.system("start streamlit run exam.py") gibi bir komutla Streamlit'i başlatabilirsiniz.
#    - Fakat en sağlıklı yol, kullanıcıya "Lütfen terminalden streamlit run exam.py komutunu çalıştırın" demektir.

# 5. Özet:
#    - Streamlit uygulamaları için .exe üretmek pratik değildir.
#    - Flask uygulamaları için PyInstaller ile .exe ve template gömme mümkündür.
#    - Streamlit'te HTML template yoktur, arayüz kodun içindedir.

# Streamlit'te Jinja2/HTML template kodları (ör: {% for d in debug %} ... {% endfor %}) kullanılamaz!
# Streamlit sadece Python kodu ve st.markdown/st.write ile çalışır.
# Arayüzde kod görünmesinin sebebi, HTML/Jinja2 kodlarının Streamlit'e yapıştırılmasıdır.
# Doğru kullanım örneği:

# Eğer debug çıktısı göstermek istiyorsanız:
if "debug" in st.session_state and st.session_state.debug:
    st.markdown("#### Debug Çıktıları")
    for d in st.session_state.debug:
        st.write(d)

# veya analiz sırasında debug listesini oluşturup:
# st.session_state.debug = debug

# Notlar:
# - Streamlit'te Jinja2 template kodları çalışmaz, sadece Python kodu ve Streamlit API'si kullanılır.
# - Github Actions ile Streamlit uygulamasını otomatik deploy etmek için Streamlit Community Cloud veya başka bir servis gerekir.
# - Localde çalışan arayüz ile Github'daki arayüz farklıysa, kodun tamamını Github'a yüklediğinizden ve requirements.txt dosyanızın güncel olduğundan emin olun.

if __name__ == "__main__":
    import webbrowser
    import threading
    import time

    def open_browser():
        # Biraz bekle, sonra tarayıcıda aç
        time.sleep(2)
        webbrowser.open_new("http://localhost:8501")

    threading.Thread(target=open_browser).start()
    # Streamlit uygulamasını başlat
    import os
    os.system("streamlit run " + __file__)
