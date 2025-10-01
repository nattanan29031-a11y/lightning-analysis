import os
from flask import Flask, request, session, render_template, redirect, url_for, flash
import pandas as pd
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app = Flask(__name__)
# Simple secret for session handling in development. In production use env var or config file.
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')


@app.route('/', methods=['GET', 'POST'])
def index():
    # Handle file upload on POST
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('กรุณาเลือกไฟล์ Excel เพื่ออัปโหลด')
            return redirect(request.url)
        file = request.files['excel_file']
        if file.filename == '':
            flash('ไม่มีไฟล์ที่ถูกเลือก')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        # store path in session
        session['excel_path'] = save_path
        flash('อัปโหลดไฟล์สำเร็จ')
        return redirect(url_for('select_line'))

    # GET -> render upload form
    return render_template('index.html')



@app.route('/select_line')
def select_line():
    excel_path = session.get('excel_path')
    if not excel_path or not os.path.exists(excel_path):
        flash('ไม่มีไฟล์ Excel ใน session หรือไฟล์ไม่พบ กรุณาอัปโหลดก่อน')
        return redirect(url_for('index'))
    try:
        xls = pd.ExcelFile(excel_path)
        sheets = xls.sheet_names
    except Exception as e:
        flash(f'ไม่สามารถอ่านไฟล์ Excel เพื่อดึง sheet: {e}')
        return redirect(url_for('index'))
    return render_template('select_line.html', lines=sheets)


@app.route('/analyze', methods=['POST'])
def analyze():
    # Read chosen sheet name
    line = request.form.get('line_name') or request.form.get('line_name_manual')

    # Ensure we have an excel path in session
    excel_path = session.get('excel_path')
    if not excel_path or not os.path.exists(excel_path):
        flash('ไม่มีไฟล์ Excel ใน session หรือไฟล์ไม่พบ กรุณาอัปโหลดก่อน')
        return redirect(url_for('index'))

    # Try reading the requested sheet
    try:
        # If line is None, read the first sheet
        if not line:
            df = pd.read_excel(excel_path)
        else:
            df = pd.read_excel(excel_path, sheet_name=line)
    except Exception as e:
        flash(f'ไม่สามารถอ่านไฟล์ Excel หรือ sheet ที่ระบุ: {e}')
        return redirect(url_for('index'))

    # Normalize column names (trim/strip) to ease matching
    df.columns = [str(c).strip() for c in df.columns]

    # Try to find amplitude column (possible names)
    amp_cols = [c for c in df.columns if 'amplitude' in c.lower() or 'amp' == c.lower()]
    if not amp_cols:
        # fallback to any numeric column besides lat/lon
        amp_cols = [c for c in df.select_dtypes(include=['number']).columns if c.lower() not in ('latitude','longitude')]

    # Required columns candidates
    lat_col = next((c for c in df.columns if c.lower() in ('latitude', 'lat')), None)
    lon_col = next((c for c in df.columns if c.lower() in ('longitude', 'lon', 'lng')), None)
    tower_col = next((c for c in df.columns if 'tower' in c.lower()), None)

    if lat_col is None or lon_col is None or tower_col is None:
        flash('คอลัมน์ Latitude/Longitude/Tower ไม่พบใน sheet กรุณาตรวจสอบไฟล์ Excel')
        return redirect(url_for('index'))

    amp_col = amp_cols[0] if amp_cols else None

    # Build per-tower aggregation
    try:
        agg = df.groupby(tower_col).agg(
            lat=(lat_col, 'mean'),
            lon=(lon_col, 'mean'),
            events=(lat_col, 'count'),
            amplitude_sum=(amp_col, 'sum') if amp_col else (lat_col, 'count'),
        ).reset_index()
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดระหว่างการสรุปข้อมูล: {e}')
        return redirect(url_for('index'))

    # Compute a simple risk score: normalize amplitude_sum to 0-100
    vals = agg['amplitude_sum'].astype(float)
    if vals.max() == vals.min():
        # avoid division by zero
        agg['risk'] = 0 if vals.max() == 0 else 100
    else:
        agg['risk'] = ((vals - vals.min()) / (vals.max() - vals.min())) * 100

    def color_for(r):
        r = float(r)
        if r >= 66:
            return '#e60000'  # red
        if r >= 33:
            return '#ffd11a'  # yellow
        return '#7fff7f'     # green

    processed_data = []
    for _, row in agg.iterrows():
        processed_data.append({
            'tower': row[tower_col],
            'lat': float(row['lat']) if not pd.isna(row['lat']) else None,
            'lon': float(row['lon']) if not pd.isna(row['lon']) else None,
            'risk': round(float(row['risk']), 1),
            'color': color_for(row['risk']),
        })

    # map_html placeholder: template expects map_html variable
    map_html = session.get('map_html', '')

    return render_template('results.html', data=processed_data, map_html=map_html)


if __name__ == '__main__':
    # Run in debug on localhost for development
    app.run(host='127.0.0.1', port=5000, debug=True)
