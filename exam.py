import os
import io
import json
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "exam_secret_key"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TABLO_BASLIKLARI = [
    ("bolum_adi", "Bölüm Adı"),
    ("puan_turu", "Puan Türü"),
    ("burs_orani", "Burs Oranı"),
    ("taban_siralama", "Taban Sıralama"),
    ("taban_puan", "Taban Puan"),
    ("tavan_puan", "Tavan Puan"),
    ("ucret", "Ücret"),
    ("dil", "Dil"),
    ("etiket", "Etiket"),
    ("riskli_t", "Riskli T"),
    ("z_riskli", "Z Riskli"),
    ("parametre", "Parametre"),
]

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
    if taban >= ogr_siralama:
        return "Uygun"
    elif z_riskli is not None and taban >= z_riskli:
        return "Riskli"
    else:
        return "Uygunsuz"

def analiz_yap(df, eklenenler):
    result = []
    for p in eklenenler:
        ogr_siralama_int = temizle_sayi(p["puan"])
        sinir_int = temizle_sayi(p["sinir"])
        riskli_t_int = temizle_sayi(p.get("riskli_t", 0))
        z = ogr_siralama_int - sinir_int
        z_riskli = z - riskli_t_int if riskli_t_int else None

        df_filtered = df.copy()
        if p["tur"] and 'Puan Türü' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Puan Türü'].astype(str).str.strip().str.upper() == p["tur"]]
        bos_veya_eksi_bolumler = []
        if 'En Düşük Sıralama' in df_filtered.columns:
            def kontrol_et(x):
                try:
                    x_sayi = int(str(x).replace('.', '').replace(',', ''))
                except:
                    return False
                if z_riskli is not None:
                    return x_sayi > z_riskli
                else:
                    return x_sayi > z
            df_filtered_main = df_filtered[df_filtered['En Düşük Sıralama'].apply(kontrol_et)]
            bos_veya_eksi_bolumler = df_filtered[df_filtered['En Düşük Sıralama'].apply(lambda x: pd.isna(x) or str(x).strip() == "" or str(x).strip() == "-")]
        else:
            df_filtered_main = df_filtered

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
                "bolum_adi": program_adi,
                "puan_turu": row.get('Puan Türü', ''),
                "burs_orani": burs,
                "taban_siralama": row.get('En Düşük Sıralama', ''),
                "taban_puan": row.get('Taban Puan', ''),
                "tavan_puan": row.get('Tavan Puan', ''),
                "ucret": ucret,
                "dil": dil,
                "etiket": etiket,
                "riskli_t": riskli_t_int,
                "z_riskli": z_riskli if z_riskli is not None else "",
                "parametre": f"{p['tur']} / {p['puan']} / {p['sinir']}"
            })

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
                if not any(r['bolum_adi'] == program_adi and r['taban_siralama'] == row.get('En Düşük Sıralama', '') for r in result):
                    result.append({
                        "bolum_adi": program_adi,
                        "puan_turu": row.get('Puan Türü', ''),
                        "burs_orani": burs,
                        "taban_siralama": row.get('En Düşük Sıralama', ''),
                        "taban_puan": row.get('Taban Puan', ''),
                        "tavan_puan": row.get('Tavan Puan', ''),
                        "ucret": ucret,
                        "dil": dil,
                        "etiket": etiket,
                        "riskli_t": riskli_t_int,
                        "z_riskli": z_riskli if z_riskli is not None else "",
                        "parametre": f"{p['tur']} / {p['puan']} / {p['sinir']}"
                    })
    if not result:
        result = [{"bolum_adi": "Sonuç bulunamadı"}]
    return result

@app.route("/", methods=["GET", "POST"])
def index():
    eklenenler = []
    adsoyad = ""
    talep_bolum = ""
    result = None
    tablo_basliklari = TABLO_BASLIKLARI
    debug = []
    if request.method == "POST":
        adsoyad_ve_bolum = request.form.get("adsoyad", "")
        # Ad soyad ve talep edilen bölüm ayrıştır
        if "," in adsoyad_ve_bolum:
            adsoyad, talep_bolum = [x.strip() for x in adsoyad_ve_bolum.split(",", 1)]
        else:
            adsoyad, talep_bolum = adsoyad_ve_bolum.strip(), ""
        eklenenler_json = request.form.get("eklenenler", "[]")
        try:
            eklenenler = json.loads(eklenenler_json)
        except Exception as e:
            eklenenler = []
            debug.append(f"Parametre okuma hatası: {e}")
        file = request.files.get("veri_dosya")
        if not file or file.filename == "":
            flash("Excel dosyası yükleyin.", "danger")
        else:
            try:
                df = pd.read_excel(file)
                df.columns = df.columns.str.strip()
                result = analiz_yap(df, eklenenler)
                # Analiz sonuçlarını session'a kaydet
                session["analiz_df"] = result
                session["adsoyad"] = adsoyad
                session["talep_bolum"] = talep_bolum
            except Exception as e:
                result = None
                flash(f"Excel okuma hatası: {e}", "danger")
        return render_template(
            "index.html",
            adsoyad=adsoyad_ve_bolum,
            eklenenler=eklenenler,
            result=result,
            tablo_basliklari=tablo_basliklari,
            debug=debug
        )
    # GET
    return render_template(
        "index.html",
        adsoyad="",
        eklenenler=[],
        result=None,
        tablo_basliklari=tablo_basliklari,
        debug=[]
    )

@app.route("/download", methods=["POST"])
def download():
    # Session'dan analiz sonuçlarını ve adsoyad'ı al
    result = session.get("analiz_df", None)
    adsoyad = session.get("adsoyad", "")
    talep_bolum = session.get("talep_bolum", "")

    if not result or not adsoyad:
        flash("Önce analiz yapmalısınız.", "warning")
        return redirect(url_for("index"))

    # Sütun sırasını korumak için TABLO_BASLIKLARI'ndaki sırayı kullan
    columns = [col for col, _ in TABLO_BASLIKLARI]
    df = pd.DataFrame(result)
    df = df[[col for col in columns if col in df.columns]]

    output = io.BytesIO()
    import xlsxwriter
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet_name = 'Sonuclar'
        df.to_excel(writer, index=False, sheet_name=worksheet_name, startrow=1)
        worksheet = writer.sheets[worksheet_name]
        # İlk satıra talep edilen bölümü yaz
        worksheet.write(0, 0, talep_bolum)
    output.seek(0)

    dosya_adi = (adsoyad.strip().replace(" ", "_") if adsoyad else "analiz_sonuclari") + ".xlsx"

    return send_file(
        output,
        as_attachment=True,
        download_name=dosya_adi,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/adsoyad", methods=["POST"])
def adsoyad_bolum():
    adsoyad_ve_bolum = request.form.get("adsoyad_bolum", "")
    if "," in adsoyad_ve_bolum:
        adsoyad, talep_bolum = [x.strip() for x in adsoyad_ve_bolum.split(",", 1)]
    else:
        adsoyad, talep_bolum = adsoyad_ve_bolum.strip(), ""
    session["adsoyad"] = adsoyad
    session["talep_bolum"] = talep_bolum
    return redirect(url_for("index"))

@app.route("/indir")
def indir():
    analiz_df = session.get("analiz_df", None)
    adsoyad = session.get("adsoyad", "")
    talep_bolum = session.get("talep_bolum", "")
    if analiz_df:
        df = pd.DataFrame(analiz_df)
        output = io.BytesIO()
        import xlsxwriter
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            worksheet_name = 'Sonuclar'
            df.to_excel(writer, index=False, sheet_name=worksheet_name, startrow=1)
            worksheet = writer.sheets[worksheet_name]
            worksheet.write(0, 0, f"Talep Edilen Bölüm: {talep_bolum}")
        output.seek(0)
        dosya_adi = (adsoyad.strip().replace(" ", "_") if adsoyad else "analiz_sonuclari") + ".xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=dosya_adi,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        flash("Önce analiz yapmalısınız.", "warning")
        return redirect(url_for("index"))

@app.route("/gemini-chat", methods=["POST"])
def gemini_chat():
    import base64
    import os
    from google import genai
    from google.genai import types

    data = request.get_json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"reply": "Lütfen bir soru veya anahtar kelime girin."})

    # Gemini API anahtarı doğrudan burada kullanılıyor
    api_key = "AIzaSyBCJHZ9fJAGSxCrxr20w0o8hwz7jVy8Cbk"
    client = genai.Client(api_key=api_key)

    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
    )

    try:
        reply = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            reply += chunk.text
        return jsonify({"reply": reply.strip()})
    except Exception as e:
        return jsonify({"reply": f"Hata: {str(e)}"})

if __name__ == "__main__":
    import sys

    def resource_path(relative_path):
        # PyInstaller ile paketlenmiş dosyalar için yol düzeltmesi
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    # Flask app'ini PyInstaller ile uyumlu başlat
    app.template_folder = resource_path('templates')
    app.static_folder = resource_path('static')
    app.run()