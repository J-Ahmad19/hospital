from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# ----------- Load env -----------
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# ----------- Supabase Postgres params (Session Pooler) -----------
PG_HOST = os.getenv("PG_HOST", "db.grwkcsknfbtxphpyygyr.supabase.co")
PG_PORT = int(os.getenv("PG_PORT", "6543"))         # pooled port; use 5432 if you prefer direct
PG_DB   = os.getenv("PG_DB", "postgres")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("PG_PASSWORD")                  # raw password; no URL-encoding needed



def get_db():
    try:
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT", 5432),
            dbname=os.getenv("PG_DB"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
            sslmode="require",
            connect_timeout=10,
            cursor_factory=RealDictCursor,
        )
        return conn
    except Exception as e:
        print("=== Postgres connection failed ===")
        print("Error:", e)
        return None


def init_db():
    """Initialize database tables (Postgres syntax)."""
    conn = get_db()
    if not conn:
        print("Failed to connect to database")
        return

    cur = conn.cursor()
    try:
        # Tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scheme (
                scheme_id BIGSERIAL PRIMARY KEY,
                sname     VARCHAR(255) NOT NULL UNIQUE,
                dscript   TEXT,
                start_date DATE NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patient (
                patient_id BIGSERIAL PRIMARY KEY,
                name       VARCHAR(255) NOT NULL,
                dob        DATE NOT NULL,
                email      VARCHAR(255),
                address    TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patient_scheme_enrollment (
                enrollment_id BIGSERIAL PRIMARY KEY,
                patient_id    BIGINT NOT NULL REFERENCES patient(patient_id) ON DELETE CASCADE,
                scheme_id     BIGINT NOT NULL REFERENCES scheme(scheme_id) ON DELETE CASCADE,
                enroll_date   DATE NOT NULL,
                amt_claimed   NUMERIC(10,2) DEFAULT 0
            );
        """)

        # Seed data
        cur.execute("SELECT COUNT(*) AS c FROM scheme;")
        count = cur.fetchone()["c"] or 0
        if count > 0:
            print(f"Found {count} existing schemes. Clearing and reinserting all schemes...")
            cur.execute("TRUNCATE TABLE scheme RESTART IDENTITY CASCADE;")

        schemes_to_insert = [
            ('Ayushman Bharat', 'Health insurance scheme for poor and vulnerable families', '2018-09-23'),
            ('PMJAY', 'Prime Ministers Scheme for cashless healthcare', '2018-09-23'),
            ('RSBY', 'Rashtriya Swasthya Bima Yojana for unorganized workers', '2007-10-01'),
            ('Atal Pension Yojana', 'Pension scheme for unorganized sector workers', '2015-05-09'),
            ('National Digital Health Mission', 'Digital health ecosystem with unique health IDs', '2020-08-15'),
            ('Sukanya Samriddhi Yojana', 'Savings scheme for girl child education and marriage', '2015-01-22'),
            ('Pradhan Mantri Matru Vandana Yojana', 'Maternity benefit program for pregnant and lactating women', '2017-01-01')
        ]
        cur.executemany(
            "INSERT INTO scheme (sname, dscript, start_date) VALUES (%s, %s, %s)",
            schemes_to_insert
        )
        conn.commit()
        print("All 7 government schemes inserted successfully")
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def home():
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template('index.html', total_patients=0, total_schemes=0, total_claimed=0)

    cur = conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) AS c FROM patient')
        total_patients = cur.fetchone()['c']

        cur.execute('SELECT COUNT(*) AS c FROM scheme')
        total_schemes = cur.fetchone()['c']

        cur.execute('SELECT COALESCE(SUM(amt_claimed),0) AS s FROM patient_scheme_enrollment')
        total_claimed = float(cur.fetchone()['s'])
    except Exception as e:
        print(f"Error fetching home stats: {e}")
        total_patients = total_schemes = 0
        total_claimed = 0
    finally:
        cur.close()
        conn.close()

    return render_template('index.html',
                           total_patients=total_patients,
                           total_schemes=total_schemes,
                           total_claimed=total_claimed)

@app.route('/add-patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form.get('name')
        dob = request.form.get('dob')
        email = request.form.get('email')
        address = request.form.get('address')
        scheme_id = request.form.get('scheme_id')
        enroll_date = request.form.get('enroll_date')
        amt_claimed = float(request.form.get('amt_claimed', 0))

        conn = get_db()
        if not conn:
            flash('Database connection failed', 'error')
            return redirect(url_for('add_patient'))

        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO patient (name, dob, email, address)
                VALUES (%s, %s, %s, %s) RETURNING patient_id;
            """, (name, dob, email, address))
            patient_id = cur.fetchone()['patient_id']

            if scheme_id:
                cur.execute("""
                    INSERT INTO patient_scheme_enrollment (patient_id, scheme_id, enroll_date, amt_claimed)
                    VALUES (%s, %s, %s, %s);
                """, (patient_id, scheme_id, enroll_date, amt_claimed))

            conn.commit()
            flash(f'Patient {name} added successfully!', 'success')
            return redirect(url_for('add_patient'))
        except Exception as e:
            conn.rollback()
            flash(f'Error adding patient: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()

    # GET: fetch schemes
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template('add_patient.html', schemes=[])

    cur = conn.cursor()
    try:
        cur.execute('SELECT scheme_id, sname FROM scheme ORDER BY sname')
        rows = cur.fetchall()
        schemes = [{'scheme_id': r['scheme_id'], 'sname': r['sname']} for r in rows]
    except Exception as e:
        print(f"Error fetching schemes: {e}")
        schemes = []
    finally:
        cur.close()
        conn.close()

    return render_template('add_patient.html', schemes=schemes)

@app.route('/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        dob = request.form.get('dob')
        email = request.form.get('email')
        address = request.form.get('address')

        try:
            cur.execute("""
                UPDATE patient
                SET name = %s, dob = %s, email = %s, address = %s
                WHERE patient_id = %s
            """, (name, dob, email, address, patient_id))
            conn.commit()
            flash(f'Patient {name} updated successfully!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating patient: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('admin'))

    try:
        cur.execute('SELECT * FROM patient WHERE patient_id = %s', (patient_id,))
        row = cur.fetchone()
        patient = None
        if row:
            patient = {
                'patient_id': row['patient_id'],
                'name': row['name'],
                'dob': row['dob'],
                'email': row['email'],
                'address': row['address']
            }
    except Exception as e:
        print(f"Error fetching patient: {e}")
        patient = None
    finally:
        cur.close()
        conn.close()

    if not patient:
        flash('Patient not found', 'error')
        return redirect(url_for('admin'))

    return render_template('edit_patient.html', patient=patient)

@app.route('/delete-patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    cur = conn.cursor()
    try:
        cur.execute('SELECT name FROM patient WHERE patient_id = %s', (patient_id,))
        row = cur.fetchone()
        if row:
            patient_name = row['name']
            cur.execute('DELETE FROM patient WHERE patient_id = %s', (patient_id,))
            conn.commit()
            flash(f'Patient {patient_name} deleted successfully!', 'success')
        else:
            flash('Patient not found', 'error')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting patient: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('admin'))

@app.route('/edit-enrollment/<int:enrollment_id>', methods=['GET', 'POST'])
def edit_enrollment(enrollment_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    cur = conn.cursor()

    if request.method == 'POST':
        scheme_id = request.form.get('scheme_id')
        enroll_date = request.form.get('enroll_date')
        amt_claimed = float(request.form.get('amt_claimed', 0))
        try:
            cur.execute("""
                UPDATE patient_scheme_enrollment
                SET scheme_id = %s, enroll_date = %s, amt_claimed = %s
                WHERE enrollment_id = %s
            """, (scheme_id, enroll_date, amt_claimed, enrollment_id))
            conn.commit()
            flash('Enrollment updated successfully!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            conn.rollback()
            flash(f'Error updating enrollment: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('admin'))

    try:
        cur.execute("""
            SELECT pse.enrollment_id, pse.patient_id, pse.scheme_id, pse.enroll_date,
                   pse.amt_claimed, p.name, s.sname
            FROM patient_scheme_enrollment pse
            JOIN patient p ON pse.patient_id = p.patient_id
            JOIN scheme s ON pse.scheme_id = s.scheme_id
            WHERE pse.enrollment_id = %s
        """, (enrollment_id,))
        e = cur.fetchone()

        cur.execute('SELECT scheme_id, sname FROM scheme ORDER BY sname')
        rows = cur.fetchall()
        schemes = [{'scheme_id': r['scheme_id'], 'sname': r['sname']} for r in rows]

        enrollment = None
        if e:
            enrollment = {
                'enrollment_id': e['enrollment_id'],
                'patient_id': e['patient_id'],
                'scheme_id': e['scheme_id'],
                'enroll_date': e['enroll_date'],
                'amt_claimed': float(e['amt_claimed']),
                'patient_name': e['name'],
                'sname': e['sname']
            }
    except Exception as ex:
        print(f"Error fetching enrollment: {ex}")
        enrollment, schemes = None, []
    finally:
        cur.close()
        conn.close()

    if not enrollment:
        flash('Enrollment not found', 'error')
        return redirect(url_for('admin'))

    return render_template('edit_enrollment.html', enrollment=enrollment, schemes=schemes)

@app.route('/delete-enrollment/<int:enrollment_id>', methods=['POST'])
def delete_enrollment(enrollment_id):
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM patient_scheme_enrollment WHERE enrollment_id = %s', (enrollment_id,))
        conn.commit()
        flash('Enrollment deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting enrollment: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template('admin.html',
                               total_patients=0, total_schemes=0, total_claimed=0,
                               scheme_stats=[], recent_enrollments=[], all_patients=[])
    cur = conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) AS c FROM patient')
        total_patients = cur.fetchone()['c']

        cur.execute('SELECT COUNT(*) AS c FROM scheme')
        total_schemes = cur.fetchone()['c']

        cur.execute('SELECT COALESCE(SUM(amt_claimed),0) AS s FROM patient_scheme_enrollment')
        total_claimed = float(cur.fetchone()['s'])

        cur.execute("""
            SELECT s.scheme_id, s.sname,
                   COUNT(pse.enrollment_id) AS enrollment_count,
                   COALESCE(SUM(pse.amt_claimed),0) AS total_amount
            FROM scheme s
            LEFT JOIN patient_scheme_enrollment pse ON s.scheme_id = pse.scheme_id
            GROUP BY s.scheme_id, s.sname
            ORDER BY s.sname
        """)
        scheme_stats_raw = cur.fetchall()
        scheme_stats = [
            {'scheme_id': s['scheme_id'], 'sname': s['sname'],
             'enrollment_count': s['enrollment_count'] or 0,
             'total_amount': float(s['total_amount'] or 0)}
            for s in scheme_stats_raw
        ]

        cur.execute("""
            SELECT pse.enrollment_id, p.patient_id, p.name, s.scheme_id, s.sname, pse.enroll_date, pse.amt_claimed
            FROM patient_scheme_enrollment pse
            JOIN patient p ON pse.patient_id = p.patient_id
            JOIN scheme s ON pse.scheme_id = s.scheme_id
            ORDER BY pse.enroll_date DESC
            LIMIT 10
        """)
        recent_enrollments_raw = cur.fetchall()
        recent_enrollments = [
            {
                'enrollment_id': e['enrollment_id'],
                'patient_id': e['patient_id'],
                'name': e['name'],
                'scheme_id': e['scheme_id'],
                'sname': e['sname'],
                'enroll_date': str(e['enroll_date']),
                'amt_claimed': float(e['amt_claimed'])
            } for e in recent_enrollments_raw
        ]

        cur.execute("""
            SELECT p.patient_id, p.name, p.dob, p.email, COUNT(pse.enrollment_id) AS scheme_count
            FROM patient p
            LEFT JOIN patient_scheme_enrollment pse ON p.patient_id = pse.patient_id
            GROUP BY p.patient_id, p.name, p.dob, p.email
            ORDER BY p.patient_id DESC
        """)
        all_patients_raw = cur.fetchall()
        all_patients = [
            {'patient_id': p['patient_id'], 'name': p['name'], 'dob': str(p['dob']),
             'email': p['email'], 'scheme_count': p['scheme_count']}
            for p in all_patients_raw
        ]
    except Exception as e:
        print(f"Error fetching admin data: {e}")
        total_patients = total_schemes = 0
        total_claimed = 0
        scheme_stats = recent_enrollments = all_patients = []
    finally:
        cur.close()
        conn.close()

    return render_template('admin.html',
                           total_patients=total_patients,
                           total_schemes=total_schemes,
                           total_claimed=total_claimed,
                           scheme_stats=scheme_stats,
                           recent_enrollments=recent_enrollments,
                           all_patients=all_patients)

if __name__ == '__main__':
    app.run(debug=True)
