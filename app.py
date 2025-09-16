import datetime
import uuid
import io
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import psycopg2
import numpy as np
# import pdfkit
import logging
# logging.basicConfig(level=logging.DEBUG)
# pdfkit.configuration(wkhtmltopdf='C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe')
# logging.debug("wkhtmltopdf path: %s", pdfkit.configuration().wkhtmltopdf)

app = Flask(__name__, template_folder='templates')
app.jinja_env.globals.update(enumerate=enumerate)
app.secret_key = 'base64:FR7YiZvqW21xKl1j9S4kOdhx0bPZppEYjcYbvRjQ+Yk='

# koneksi ke database PostgreSQL
try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        database="proyekmcdm",
        user="postgres",
        password="" 
    )
    cur = conn.cursor()
except psycopg2.Error as e:
    print(f"Error connecting to database: {e}")
    conn = None
    cur = None

# Route untuk halaman utama
@app.route('/')
def index():
    return render_template('login.html')

# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username dan password tidak boleh kosong!', 'danger')
            return redirect(url_for('login'))

        try:
            cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
            admin = cur.fetchone()
        except psycopg2.Error as e:
            flash(f'Terjadi kesalahan saat login: {e}', 'danger')
            return redirect(url_for('login'))

        if admin:
            session['admin'] = username
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login gagal, username atau password salah', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

# Routee untuk dashboard
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    # Ambil data dari session
    total_kriteria = len(session.get('kriteria', []))
    total_alternatif = len(session.get('alternatif', []))
    recent_logs = session.get('recent_logs', [])
    last_login = session.get('last_login', 'Belum tersedia')

    return render_template(
        'dashboard.html',
        admin=session['admin'],
        total_kriteria=total_kriteria,
        total_alternatif=total_alternatif,
        recent_logs=recent_logs,
        last_login=last_login,
        active_page='dashboard'
    )


# Route untuk logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('login'))


# Routee untuk input kriteria
@app.route('/kriteria', methods=['GET', 'POST'])
def kriteria():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nama_kriteria = request.form.get('nama_kriteria')

        if not nama_kriteria:
            flash('Nama kriteria tidak boleh kosong!', 'danger')
            return redirect(url_for('kriteria'))

        if 'kriteria' not in session:
            session['kriteria'] = []

        new_kriteria = {
            'Kriteria': nama_kriteria,
        }
        
        session['kriteria'].append(new_kriteria)
        session.modified = True
        flash('Kriteria berhasil ditambahkan!', 'success')
        return redirect(url_for('kriteria'))

    return render_template(
        'master_data/kriteria.html',
        admin=session['admin'],
        active_page='master_data',
        sub_page='kriteria',
        data_kriteria=session.get('kriteria', [])
    )

# Rute untuk input alternatif
@app.route('/alternatif', methods=['GET', 'POST'])
def alternatif():
    if 'admin' not in session:
        return redirect(url_for('login'))

    if 'alternatif' not in session:
        session['alternatif'] = []

    if request.method == 'POST':
        nama_alternatif = request.form.get('nama_alternatif')

        if not nama_alternatif:
            flash('Nama alternatif tidak boleh kosong!', 'danger')
            return redirect(url_for('alternatif'))

        new_alternatif = {
            'id': str(uuid.uuid4()),
            'Nama': nama_alternatif,
            'Timestamp': datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        }
        session['alternatif'].append(new_alternatif)
        session.modified = True
        flash('Alternatif berhasil ditambahkan!', 'success')
        return redirect(url_for('alternatif'))

    return render_template('master_data/alternatif.html',
                          admin=session['admin'],
                          active_page='master_data',
                          sub_page='alternatif',
                          data_alternatif=session.get('alternatif', []))

# Route untuk delete alternatif 
@app.route('/hapus-alternatif/<string:id>', methods=['POST'])
def hapus_alternatif(id):
    if 'admin' not in session:
        return redirect(url_for('login'))

    if 'alternatif' in session:
        session['alternatif'] = [alt for alt in session['alternatif'] if alt['id'] != id]
        session.modified = True
        flash('Alternatif berhasil dihapus!', 'success')

    return redirect(url_for('alternatif'))

# Route untuk perbandingan kriteria (AHP)
@app.route('/perbandingan_kriteria', methods=['GET', 'POST'])
def perbandingan_kriteria():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    n = len(kriteria)

    if n < 2:
        flash('Tambahkan minimal 2 kriteria terlebih dahulu.', 'warning')
        return redirect(url_for('kriteria'))

    if request.method == 'POST':
        perbandingan = {}
        for i in range(n):
            for j in range(i + 1, n):
                key = f"{i}_{j}"
                value = request.form.get(key)
                if not value:
                    flash(f'Nilai perbandingan untuk {kriteria[i]["Kriteria"]} vs {kriteria[j]["Kriteria"]} tidak boleh kosong!', 'danger')
                    return redirect(url_for('perbandingan_kriteria'))
                try:
                    # perbandingan[key] = float(value)
                    nilai= float(value)
                    if nilai <= 0:
                         flash(f'Nilai perbandingan untuk {kriteria[i]["Kriteria"]} vs {kriteria[j]["Kriteria"]} harus lebih besar dari 0!', 'danger')
                         return redirect(url_for('perbandingan_kriteria'))
                    
                    perbandingan[f"{i}_{j}"] = nilai
                    perbandingan[f"{j}_{i}"] = 1 / nilai
                    
                    if perbandingan[key] <= 0:
                        flash(f'Nilai perbandingan untuk {kriteria[i]["Kriteria"]} vs {kriteria[j]["Kriteria"]} harus lebih besar dari 0!', 'danger')
                        return redirect(url_for('perbandingan_kriteria'))
                except ValueError:
                    flash(f'Nilai perbandingan tidak valid untuk {kriteria[i]["Kriteria"]} vs {kriteria[j]["Kriteria"]}', 'danger')
                    return redirect(url_for('perbandingan_kriteria'))

        session['perbandingan_kriteria'] = perbandingan
        flash("Perbandingan kriteria berhasil disimpan!", "success")
        return redirect(url_for('hasil_kriteria'))

    return render_template('ahp/perbandingan_kriteria.html',
                          kriteria=kriteria,
                          admin=session['admin'],
                          active_page='ahp',
                          sub_page='perbandingan_kriteria')

# Route untuk hasil kriteria (AHP)
@app.route('/hasil-kriteria')
def hasil_kriteria():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    perbandingan = session.get('perbandingan_kriteria', {})
    n = len(kriteria)

    if not perbandingan or n < 2:
        flash('Perbandingan kriteria belum lengkap.', 'danger')
        return redirect(url_for('perbandingan_kriteria'))

    # Bangun matriks perbandingan
    matrix = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            key = f"{i}_{j}"
            value = perbandingan.get(key)
            if value:
                matrix[i][j] = value
                matrix[j][i] = 1 / value

    # Hitung jumlah tiap kolom
    col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]

    # Normalisasi matriks dan hitung bobot prioritas
    norm_matrix = [[matrix[i][j] / col_sums[j] if col_sums[j] != 0 else 0 for j in range(n)] for i in range(n)]
    priority = [sum(norm_matrix[i]) / n for i in range(n)]

    # Cek konsistensi
    lambda_max = sum(
        sum(matrix[i][j] * priority[j] for j in range(n)) / priority[i]
        for i in range(n) if priority[i] != 0
    ) / n
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0
    RI_list = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
    RI = RI_list.get(n, 1.45)
    CR = CI / RI if RI != 0 else 0

    return render_template('ahp/hasil_kriteria.html',
                          kriteria=kriteria,
                          matrix=matrix,
                          norm_matrix=norm_matrix,
                          priority=priority,
                          lambda_max=lambda_max,
                          CI=CI,
                          CR=CR,
                          admin=session['admin'],
                          active_page='ahp',
                          sub_page='hasil_kriteria')

# Route untuk perbandingan alternatif (AHP)
@app.route('/perbandingan-alternatif', methods=['GET', 'POST'])
def perbandingan_alternatif():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    alternatif = session.get('alternatif', [])

    if len(kriteria) == 0 or len(alternatif) < 2:
        flash('Tambahkan minimal 2 alternatif dan 1 kriteria.', 'warning')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        hasil = {}
        for krit in kriteria:
            nama_kriteria = krit['Kriteria']
            hasil[nama_kriteria] = {}
            for i in range(len(alternatif)):
                for j in range(i + 1, len(alternatif)):
                    key = f"{i}_{j}"
                    value = request.form.get(f"{nama_kriteria}_{key}")
                    if not value:
                        flash(f'Nilai perbandingan untuk {nama_kriteria} antara {alternatif[i]["Nama"]} vs {alternatif[j]["Nama"]} tidak boleh kosong!', 'danger')
                        return redirect(url_for('perbandingan_alternatif'))
                    try:
                        nilai = float(value)
                        if nilai <= 0:
                            flash(f'Nilai perbandingan untuk {nama_kriteria} antara {alternatif[i]["Nama"]} vs {alternatif[j]["Nama"]} harus lebih besar dari 0!', 'danger')
                            return redirect(url_for('perbandingan_alternatif'))
                        hasil[nama_kriteria][f"{alternatif[i]['Nama']} vs {alternatif[j]['Nama']}"] = nilai
                        hasil[nama_kriteria][f"{alternatif[j]['Nama']} vs {alternatif[i]['Nama']}"] = 1 / nilai
                    except ValueError:
                        flash(f'Nilai perbandingan tidak valid untuk {nama_kriteria} antara {alternatif[i]["Nama"]} vs {alternatif[j]["Nama"]}', 'danger')
                        return redirect(url_for('perbandingan_alternatif'))

        session['perbandingan_alternatif'] = hasil
        flash('Perbandingan alternatif berhasil disimpan!', 'success')
        return redirect(url_for('hasil_alternatif'))

    return render_template('ahp/perbandingan_alternatif.html',
                          kriteria=kriteria,
                          alternatif=alternatif,
                          admin=session['admin'],
                          active_page='ahp',
                          sub_page='perbandingan_alternatif')

# Route untuk hasil alternatif (AHP)
@app.route('/hasil-alternatif')
def hasil_alternatif():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    alternatif = session.get('alternatif', [])
    perbandingan = session.get('perbandingan_alternatif', {})
    
    if not perbandingan or len(alternatif) < 2:
        flash('Perbandingan alternatif belum lengkap.', 'danger')
        return redirect(url_for('perbandingan_alternatif'))

    hasil = {}
    for krit in kriteria:
        nama_kriteria = krit['Kriteria']
        n = len(alternatif)
        matrix = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                key = f"{alternatif[i]['Nama']} vs {alternatif[j]['Nama']}"
                value = perbandingan[nama_kriteria].get(key, 1)
                matrix[i][j] = value
                matrix[j][i] = 1 / value
        
        col_sums = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
        norm_matrix = [[matrix[i][j] / col_sums[j] if col_sums[j] != 0 else 0 for j in range(n)] for i in range(n)]
        priority = [sum(norm_matrix[i]) / n for i in range(n)]
        
        lambda_max = sum(sum(matrix[i][j] * priority[j] for j in range(n)) / priority[i] for i in range(n) if priority[i] != 0) / n
        CI = (lambda_max - n) / (n - 1) if n > 1 else 0
        RI_list = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}
        RI = RI_list.get(n, 1.45)
        CR = CI / RI if RI != 0 else 0
        
        hasil[nama_kriteria] = {
            'matrix': matrix,
            'norm_matrix': norm_matrix,
            'priority': priority,
            'lambda_max': lambda_max,
            'CI': CI,
            'CR': CR
        }

    return render_template('ahp/hasil_alternatif.html',
                          kriteria=kriteria,
                          alternatif=alternatif,
                          hasil=hasil,
                          admin=session['admin'],
                          active_page='ahp',
                          sub_page='hasil_alternatif')

# Route untuk hasil akhir AHP
@app.route('/hasil-ahp')
def hasil_ahp():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    alternatif = session.get('alternatif', [])
    perb_kriteria = session.get('perbandingan_kriteria', {})
    perb_alternatif = session.get('perbandingan_alternatif', {})

    if not perb_kriteria or not perb_alternatif:
        flash("Data perbandingan belum lengkap!", "danger")
        return redirect(url_for('perbandingan_kriteria'))

    n_kriteria = len(kriteria)
    mat_kriteria = [[1 if i == j else perb_kriteria.get(f"{i}_{j}", 1/perb_kriteria.get(f"{j}_{i}", 1))
                    for j in range(n_kriteria)] for i in range(n_kriteria)]
    col_sums = [sum(mat_kriteria[i][j] for i in range(n_kriteria)) for j in range(n_kriteria)]
    norm_kriteria = [[mat_kriteria[i][j]/col_sums[j] if col_sums[j] != 0 else 0 for j in range(n_kriteria)] for i in range(n_kriteria)]
    bobot_kriteria = [sum(norm_kriteria[i])/n_kriteria for i in range(n_kriteria)]

    bobot_alternatif = {}
    n_alternatif = len(alternatif)
    for k_idx, krit in enumerate(kriteria):
        nama_krit = krit['Kriteria']
        mat_alternatif = [[1 if i == j else
                          perb_alternatif[nama_krit].get(f"{alternatif[i]['Nama']} vs {alternatif[j]['Nama']}", 1) if i < j else
                          1/perb_alternatif[nama_krit].get(f"{alternatif[j]['Nama']} vs {alternatif[i]['Nama']}", 1)
                         for j in range(n_alternatif)] for i in range(n_alternatif)]
        col_sums_alt = [sum(mat_alternatif[i][j] for i in range(n_alternatif)) for j in range(n_alternatif)]
        norm_alternatif = [[mat_alternatif[i][j]/col_sums_alt[j] if col_sums_alt[j] != 0 else 0 for j in range(n_alternatif)] for i in range(n_alternatif)]
        priority_alt = [sum(norm_alternatif[i])/n_alternatif for i in range(n_alternatif)]
        bobot_alternatif[nama_krit] = priority_alt

    ranking = []
    for i in range(n_alternatif):
        total = sum(
            bobot_kriteria[k_idx] * bobot_alternatif[krit['Kriteria']][i]
            for k_idx, krit in enumerate(kriteria)
        )
        ranking.append({
            'nama': alternatif[i]['Nama'],
            'nilai': total,
            'details': {
                krit['Kriteria']: bobot_alternatif[krit['Kriteria']][i]
                for krit in kriteria
            }
        })
    ranking.sort(key=lambda x: x['nilai'], reverse=True)

    return render_template('ahp/hasil_ahp.html',
                          ranking=ranking,
                          kriteria=kriteria,
                          bobot_kriteria=bobot_kriteria,
                          admin=session['admin'],
                          active_page='ahp',
                          sub_page='hasil_ahp')


# Route untuk export AHP ke Excel
@app.route('/export-ahp-excel')
def export_ahp_excel():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    alternatif = session.get('alternatif', [])
    perb_kriteria = session.get('perbandingan_kriteria', {})
    perb_alternatif = session.get('perbandingan_alternatif', {})

    if not perb_kriteria or not perb_alternatif:
        flash("Data perbandingan belum lengkap!", "danger")
        return redirect(url_for('perbandingan_kriteria'))

    # Hitung bobot kriteria
    n_kriteria = len(kriteria)
    mat_kriteria = [[1 if i == j else perb_kriteria.get(f"{i}_{j}", 1/perb_kriteria.get(f"{j}_{i}", 1))
                    for j in range(n_kriteria)] for i in range(n_kriteria)]
    col_sums = [sum(mat_kriteria[i][j] for i in range(n_kriteria)) for j in range(n_kriteria)]
    norm_kriteria = [[mat_kriteria[i][j]/col_sums[j] if col_sums[j] != 0 else 0 for j in range(n_kriteria)] for i in range(n_kriteria)]
    bobot_kriteria = [sum(norm_kriteria[i])/n_kriteria for i in range(n_kriteria)]

    # Hitung bobot alternatif dan ranking
    bobot_alternatif = {}
    n_alternatif = len(alternatif)
    for k_idx, krit in enumerate(kriteria):
        nama_krit = krit['Kriteria']
        mat_alternatif = [[1 if i == j else
                          perb_alternatif[nama_krit].get(f"{alternatif[i]['Nama']} vs {alternatif[j]['Nama']}", 1) if i < j else
                          1/perb_alternatif[nama_krit].get(f"{alternatif[j]['Nama']} vs {alternatif[i]['Nama']}", 1)
                         for j in range(n_alternatif)] for i in range(n_alternatif)]
        col_sums_alt = [sum(mat_alternatif[i][j] for i in range(n_alternatif)) for j in range(n_alternatif)]
        norm_alternatif = [[mat_alternatif[i][j]/col_sums_alt[j] if col_sums_alt[j] != 0 else 0 for j in range(n_alternatif)] for i in range(n_alternatif)]
        priority_alt = [sum(norm_alternatif[i])/n_alternatif for i in range(n_alternatif)]
        bobot_alternatif[nama_krit] = priority_alt

    ranking = []
    for i in range(n_alternatif):
        total = sum(
            bobot_kriteria[k_idx] * bobot_alternatif[krit['Kriteria']][i]
            for k_idx, krit in enumerate(kriteria)
        )
        ranking.append({
            'nama': alternatif[i]['Nama'],
            'nilai': total,
            'details': {
                krit['Kriteria']: bobot_alternatif[krit['Kriteria']][i]
                for krit in kriteria
            }
        })
    ranking.sort(key=lambda x: x['nilai'], reverse=True)

    # Prepare data for Excel
    # Bobot Kriteria
    df_kriteria = pd.DataFrame({
        'Kriteria': [krit['Kriteria'] for krit in kriteria],
        'Bobot Prioritas': [f"{val:.4f}" for val in bobot_kriteria]
    })

    # Matriks Perbandingan Kriteria
    df_mat_kriteria = pd.DataFrame(mat_kriteria, columns=[krit['Kriteria'] for krit in kriteria], index=[krit['Kriteria'] for krit in kriteria])
    df_mat_kriteria.index.name = 'Kriteria'

    # Normalisasi Matriks Kriteria
    df_norm_kriteria = pd.DataFrame(norm_kriteria, columns=[krit['Kriteria'] for krit in kriteria], index=[krit['Kriteria'] for krit in kriteria])
    df_norm_kriteria.index.name = 'Kriteria'

    # Ranking Alternatif
    columns = ['Ranking', 'Alternatif', 'Nilai Akhir'] + [krit['Kriteria'] for krit in kriteria]
    data = []
    for idx, alt in enumerate(ranking, 1):
        row = [idx, alt['nama'], f"{alt['nilai']:.4f}"] + [f"{alt['details'][krit['Kriteria']]:.4f}" for krit in kriteria]
        data.append(row)
    df_ranking = pd.DataFrame(data, columns=columns)

    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_kriteria.to_excel(writer, sheet_name='Bobot Kriteria', index=False)
        df_mat_kriteria.to_excel(writer, sheet_name='Matriks Perbandingan Kriteria', index=True)
        df_norm_kriteria.to_excel(writer, sheet_name='Normalisasi Matriks Kriteria', index=True)
        df_ranking.to_excel(writer, sheet_name='Ranking Alternatif', index=False)
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        download_name='AHP_Results.xlsx',
        as_attachment=True
    )


# Route untuk input DEMATEL
@app.route('/dematel', methods=['GET', 'POST'])
def dematel():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    n = len(kriteria)

    if n < 2:
        flash('Tambahkan minimal 2 kriteria terlebih dahulu.', 'warning')
        return redirect(url_for('kriteria'))

    if request.method == 'POST':
        direct_matrix = [[0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    key = f"{i}_{j}"
                    value = request.form.get(key)
                    if not value:
                        flash(f'Nilai pengaruh untuk {kriteria[i]["Kriteria"]} -> {kriteria[j]["Kriteria"]} tidak boleh kosong!', 'danger')
                        return redirect(url_for('dematel'))
                    try:
                        nilai = int(value)
                        if nilai < 1 or nilai > 5:
                            flash(f'Nilai pengaruh untuk {kriteria[i]["Kriteria"]} -> {kriteria[j]["Kriteria"]} harus dalam range 1-5!', 'danger')
                            return redirect(url_for('dematel'))
                        direct_matrix[i][j] = nilai
                    except ValueError:
                        flash(f'Nilai pengaruh tidak valid untuk {kriteria[i]["Kriteria"]} -> {kriteria[j]["Kriteria"]}', 'danger')
                        return redirect(url_for('dematel'))

        session['dematel_direct_matrix'] = direct_matrix
        flash("Matriks pengaruh langsung berhasil disimpan!", "success")
        return redirect(url_for('hasil_dematel'))

    scales = list(range(5))
    return render_template('dematel/input_dematel.html',
                          kriteria=kriteria,
                          scales=scales,
                          admin=session['admin'],
                          active_page='dematel',
                          sub_page='dematel_input')

@app.route('/hasil_dematel')
def hasil_dematel():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    direct_matrix = session.get('dematel_direct_matrix', [])
    n = len(kriteria)

    # Validasi input
    if not direct_matrix or n < 2:
        flash('Matriks pengaruh langsung belum lengkap atau kurang dari 2 kriteria.', 'danger')
        return redirect(url_for('dematel'))

    if not all(len(row) == n for row in direct_matrix):
        flash('Matriks pengaruh langsung tidak sesuai (ukuran tidak konsisten).', 'danger')
        return redirect(url_for('dematel'))

    try:
        # Konversi ke numpy array
        D = np.array(direct_matrix, dtype=float)

        # Validasi matriks tidak kosong (semua nilai 0)
        if np.all(D == 0):
            flash('Matriks pengaruh tidak valid (semua nilai 0).', 'danger')
            return redirect(url_for('dematel'))

        # Hitung faktor normalisasi (menggunakan maksimum dari jumlah baris)
        row_sums = np.sum(D, axis=1)
        max_row_sum = np.max(row_sums)
        if max_row_sum == 0:
            flash('Matriks pengaruh tidak valid (tidak ada hubungan antar kriteria).', 'danger')
            return redirect(url_for('dematel'))

        # Normalisasi matriks pengaruh langsung: D_norm = D / max_row_sum
        D_norm = D / max_row_sum

        # Matriks identitas
        I = np.eye(n)

        # Hitung (I - D_norm)
        I_minus_D_norm = I - D_norm

        # Validasi matriks dapat diinvers
        if np.linalg.matrix_rank(I_minus_D_norm) < n:
            flash('Matriks (I - D_norm) tidak dapat diinvers (singular matrix).', 'danger')
            return redirect(url_for('dematel'))

        # Hitung invers (I - D_norm)^(-1)
        inv_I_minus_D_norm = np.linalg.inv(I_minus_D_norm)

        # Hitung matriks total hubungan: T = D_norm * (I - D_norm)^(-1)
        T = np.dot(D_norm, inv_I_minus_D_norm)

        # Hitung R (jumlah baris) dan C (jumlah kolom) dari matriks total
        R = np.sum(T, axis=1)  # Pengaruh yang diberikan
        C = np.sum(T, axis=0)  # Pengaruh yang diterima

        # Hitung R + C (prominence) dan R - C (relation)
        R_plus_C = R + C  # Menunjukkan pentingnya kriteria
        R_minus_C = R - C  # Menunjukkan apakah kriteria adalah penyebab (>0) atau akibat (<0)

        # Siapkan hasil untuk ditampilkan
        results = [
            {
                'kriteria': kriteria[i]['Kriteria'],
                'R': round(float(R[i]), 4),  # Pengaruh yang diberikan
                'C': round(float(C[i]), 4),  # Pengaruh yang diterima
                'R_plus_C': round(float(R_plus_C[i]), 4),  # Kepentingan
                'R_minus_C': round(float(R_minus_C[i]), 4),  # Hubungan
                'cause_effect': 'Penyebab' if R_minus_C[i] > 0 else 'Akibat'
            }
            for i in range(n)
        ]

        # Format matriks untuk tampilan
        direct_matrix = [[round(val, 4) for val in row] for row in direct_matrix]
        normalized_matrix = [[round(val, 4) for val in row] for row in D_norm.tolist()]
        inverse_matrix = [[round(val, 4) for val in row] for row in inv_I_minus_D_norm.tolist()]
        total_matrix = [[round(val, 4) for val in row] for row in T.tolist()]

        return render_template('dematel/hasil_dematel.html',
                              kriteria=kriteria,
                              direct_matrix=direct_matrix,
                              normalized_matrix=normalized_matrix,
                              inverse_matrix=inverse_matrix,
                              total_matrix=total_matrix,
                              results=results,
                              admin=session['admin'],
                              active_page='dematel',
                              sub_page='hasil_dematel')

    except np.linalg.LinAlgError:
        flash('Matriks (I - D_norm) tidak dapat diinvers (singular matrix).', 'danger')
        return redirect(url_for('dematel'))
    except ValueError as ve:
        flash(f'Kesalahan pada data matriks: {str(ve)}', 'danger')
        return redirect(url_for('dematel'))
    except Exception as e:
        flash(f'Kesalahan sistem: {str(e)}', 'danger')
        return redirect(url_for('dematel'))

# Route untuk export DEMATEL ke Excel
@app.route('/export-dematel-excel')
def export_dematel_excel():
    if 'admin' not in session:
        return redirect(url_for('login'))

    kriteria = session.get('kriteria', [])
    direct_matrix = session.get('dematel_direct_matrix', [])
    n = len(kriteria)

    # Validasi input
    if not direct_matrix or n < 2:
        flash('Matriks pengaruh langsung belum lengkap atau kurang dari 2 kriteria.', 'danger')
        return redirect(url_for('dematel'))

    try:
        D = np.array(direct_matrix, dtype=float)
        if np.all(D == 0):
            flash('Matriks pengaruh tidak valid (semua nilai 0).', 'danger')
            return redirect(url_for('dematel'))

        row_sums = np.sum(D, axis=1)
        max_row_sum = np.max(row_sums)
        if max_row_sum == 0:
            flash('Matriks pengaruh tidak valid (tidak ada hubungan antar kriteria).', 'danger')
            return redirect(url_for('dematel'))

        D_norm = D / max_row_sum
        I = np.eye(n)
        I_minus_D_norm = I - D_norm
        if np.linalg.matrix_rank(I_minus_D_norm) < n:
            flash('Matriks (I - D_norm) tidak dapat diinvers (singular matrix).', 'danger')
            return redirect(url_for('dematel'))

        inv_I_minus_D_norm = np.linalg.inv(I_minus_D_norm)
        T = np.dot(D_norm, inv_I_minus_D_norm)
        R = np.sum(T, axis=1)
        C = np.sum(T, axis=0)
        R_plus_C = R + C
        R_minus_C = R - C

        results = [
            {
                'kriteria': kriteria[i]['Kriteria'],
                'R': round(float(R[i]), 4),
                'C': round(float(C[i]), 4),
                'R_plus_C': round(float(R_plus_C[i]), 4),
                'R_minus_C': round(float(R_minus_C[i]), 4),
                'cause_effect': 'Penyebab' if R_minus_C[i] > 0 else 'Akibat'
            }
            for i in range(n)
        ]

        # Prepare data for Excel
        # Matriks Pengaruh Langsung
        df_direct = pd.DataFrame(direct_matrix, columns=[krit['Kriteria'] for krit in kriteria], index=[krit['Kriteria'] for krit in kriteria])
        df_direct.index.name = 'Kriteria'

        # Matriks Normalisasi
        df_normalized = pd.DataFrame(D_norm, columns=[krit['Kriteria'] for krit in kriteria], index=[krit['Kriteria'] for krit in kriteria])
        df_normalized = df_normalized.round(4)
        df_normalized.index.name = 'Kriteria'

        # Matriks Invers
        df_inverse = pd.DataFrame(inv_I_minus_D_norm, columns=[krit['Kriteria'] for krit in kriteria], index=[krit['Kriteria'] for krit in kriteria])
        df_inverse = df_inverse.round(4)
        df_inverse.index.name = 'Kriteria'

        # Matriks Total Hubungan
        df_total = pd.DataFrame(T, columns=[krit['Kriteria'] for krit in kriteria], index=[krit['Kriteria'] for krit in kriteria])
        df_total = df_total.round(4)
        df_total.index.name = 'Kriteria'

        # Analisis Penyebab dan Akibat
        df_results = pd.DataFrame(results)

        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_direct.to_excel(writer, sheet_name='Matriks Pengaruh Langsung')
            df_normalized.to_excel(writer, sheet_name='Matriks Normalisasi')
            df_inverse.to_excel(writer, sheet_name='Matriks Invers')
            df_total.to_excel(writer, sheet_name='Matriks Total Hubungan')
            df_results.to_excel(writer, sheet_name='Analisis Penyebab Akibat', index=False)
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='DEMATEL_Results.xlsx',
            as_attachment=True
        )

    except Exception as e:
        flash(f'Gagal membuat Excel: {str(e)}', 'danger')
        return redirect(url_for('hasil_dematel'))


    
if __name__ == "__main__":
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'cur' in globals() and cur:
            cur.close()
        if 'conn' in globals() and conn:

            conn.close()
