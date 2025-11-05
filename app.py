from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'hospital_schemes'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'ssl_disabled': False,
    'autocommit': False
}

def get_db():
    """Get database connection with DictCursor for named columns"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def dict_from_cursor(cursor, row):
    """Convert cursor row to dictionary"""
    desc = cursor.description
    if desc is None:
        return {}
    return dict(zip([col[0] for col in desc], row))

def init_db():
    """Initialize database tables"""
    conn = get_db()
    if not conn:
        print("Failed to connect to database")
        return
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheme (
                scheme_id INT AUTO_INCREMENT PRIMARY KEY,
                sname VARCHAR(255) NOT NULL UNIQUE,
                dscript TEXT,
                start_date DATE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient (
                patient_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                dob DATE NOT NULL,
                email VARCHAR(255),
                address TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_scheme_enrollment (
                enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                scheme_id INT NOT NULL,
                enroll_date DATE NOT NULL,
                amt_claimed DECIMAL(10, 2) DEFAULT 0,
                FOREIGN KEY(patient_id) REFERENCES patient(patient_id) ON DELETE CASCADE,
                FOREIGN KEY(scheme_id) REFERENCES scheme(scheme_id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM scheme")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Inserting sample schemes...")
            cursor.execute(
                "INSERT INTO scheme (sname, dscript, start_date) VALUES (%s, %s, %s)",
                ('Ayushman Bharat', 'Health insurance scheme for poor and vulnerable families', '2018-09-23')
            )
            cursor.execute(
                "INSERT INTO scheme (sname, dscript, start_date) VALUES (%s, %s, %s)",
                ('PMJAY', 'Prime Ministers Scheme for cashless healthcare', '2018-09-23')
            )
            cursor.execute(
                "INSERT INTO scheme (sname, dscript, start_date) VALUES (%s, %s, %s)",
                ('RSBY', 'Rashtriya Swasthya Bima Yojana for unorganized workers', '2007-10-01')
            )
            conn.commit()
            print("Sample schemes inserted successfully")
        
        conn.commit()
        print("Database initialized successfully")
    except Error as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# Initialize database on startup
init_db()

@app.route('/')
def home():
    """Home page"""
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template('index.html', total_patients=0, total_schemes=0, total_claimed=0)
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) FROM patient')
        total_patients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scheme')
        total_schemes = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amt_claimed) FROM patient_scheme_enrollment')
        result = cursor.fetchone()
        total_claimed = float(result[0]) if result[0] else 0
    except Error as e:
        print(f"Error fetching home stats: {e}")
        total_patients = total_schemes = 0
        total_claimed = 0
    finally:
        cursor.close()
        conn.close()
    
    return render_template('index.html', 
                         total_patients=total_patients,
                         total_schemes=total_schemes,
                         total_claimed=total_claimed)

@app.route('/add-patient', methods=['GET', 'POST'])
def add_patient():
    """Add new patient"""
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
        
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO patient (name, dob, email, address)
                VALUES (%s, %s, %s, %s)
            ''', (name, dob, email, address))
            
            patient_id = cursor.lastrowid
            
            if scheme_id:
                cursor.execute('''
                    INSERT INTO patient_scheme_enrollment (patient_id, scheme_id, enroll_date, amt_claimed)
                    VALUES (%s, %s, %s, %s)
                ''', (patient_id, scheme_id, enroll_date, amt_claimed))
            
            conn.commit()
            flash(f'Patient {name} added successfully!', 'success')
            return redirect(url_for('add_patient'))
        except Error as e:
            conn.rollback()
            flash(f'Error adding patient: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template('add_patient.html', schemes=[])
    
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT scheme_id, sname FROM scheme ORDER BY sname')
        schemes = cursor.fetchall()
        schemes = [{'scheme_id': s[0], 'sname': s[1]} for s in schemes]
    except Error as e:
        print(f"Error fetching schemes: {e}")
        schemes = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('add_patient.html', schemes=schemes)

@app.route('/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    """Edit patient details"""
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        dob = request.form.get('dob')
        email = request.form.get('email')
        address = request.form.get('address')
        
        try:
            cursor.execute('''
                UPDATE patient 
                SET name = %s, dob = %s, email = %s, address = %s
                WHERE patient_id = %s
            ''', (name, dob, email, address, patient_id))
            
            conn.commit()
            flash(f'Patient {name} updated successfully!', 'success')
            return redirect(url_for('admin'))
        except Error as e:
            conn.rollback()
            flash(f'Error updating patient: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('admin'))
    
    try:
        cursor.execute('SELECT * FROM patient WHERE patient_id = %s', (patient_id,))
        patient = cursor.fetchone()
        if patient:
            patient = {
                'patient_id': patient[0],
                'name': patient[1],
                'dob': patient[2],
                'email': patient[3],
                'address': patient[4]
            }
    except Error as e:
        print(f"Error fetching patient: {e}")
        patient = None
    finally:
        cursor.close()
        conn.close()
    
    if not patient:
        flash('Patient not found', 'error')
        return redirect(url_for('admin'))
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/delete-patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    """Delete patient and their enrollments"""
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT name FROM patient WHERE patient_id = %s', (patient_id,))
        patient = cursor.fetchone()
        
        if patient:
            patient_name = patient[0]
            cursor.execute('DELETE FROM patient WHERE patient_id = %s', (patient_id,))
            conn.commit()
            flash(f'Patient {patient_name} deleted successfully!', 'success')
        else:
            flash('Patient not found', 'error')
    except Error as e:
        conn.rollback()
        flash(f'Error deleting patient: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin'))

@app.route('/edit-enrollment/<int:enrollment_id>', methods=['GET', 'POST'])
def edit_enrollment(enrollment_id):
    """Edit patient scheme enrollment"""
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    
    cursor = conn.cursor()
    
    if request.method == 'POST':
        scheme_id = request.form.get('scheme_id')
        enroll_date = request.form.get('enroll_date')
        amt_claimed = float(request.form.get('amt_claimed', 0))
        
        try:
            cursor.execute('''
                UPDATE patient_scheme_enrollment 
                SET scheme_id = %s, enroll_date = %s, amt_claimed = %s
                WHERE enrollment_id = %s
            ''', (scheme_id, enroll_date, amt_claimed, enrollment_id))
            
            conn.commit()
            flash('Enrollment updated successfully!', 'success')
            return redirect(url_for('admin'))
        except Error as e:
            conn.rollback()
            flash(f'Error updating enrollment: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('admin'))
    
    try:
        cursor.execute('''
            SELECT pse.enrollment_id, pse.patient_id, pse.scheme_id, pse.enroll_date, 
                   pse.amt_claimed, p.name, s.sname 
            FROM patient_scheme_enrollment pse
            JOIN patient p ON pse.patient_id = p.patient_id
            JOIN scheme s ON pse.scheme_id = s.scheme_id
            WHERE pse.enrollment_id = %s
        ''', (enrollment_id,))
        enrollment = cursor.fetchone()
        
        if enrollment:
            enrollment = {
                'enrollment_id': enrollment[0],
                'patient_id': enrollment[1],
                'scheme_id': enrollment[2],
                'enroll_date': enrollment[3],
                'amt_claimed': float(enrollment[4]),
                'patient_name': enrollment[5],
                'sname': enrollment[6]
            }
        
        cursor.execute('SELECT scheme_id, sname FROM scheme ORDER BY sname')
        schemes = cursor.fetchall()
        schemes = [{'scheme_id': s[0], 'sname': s[1]} for s in schemes]
    except Error as e:
        print(f"Error fetching enrollment: {e}")
        enrollment = None
        schemes = []
    finally:
        cursor.close()
        conn.close()
    
    if not enrollment:
        flash('Enrollment not found', 'error')
        return redirect(url_for('admin'))
    
    return render_template('edit_enrollment.html', enrollment=enrollment, schemes=schemes)

@app.route('/delete-enrollment/<int:enrollment_id>', methods=['POST'])
def delete_enrollment(enrollment_id):
    """Delete patient scheme enrollment"""
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return redirect(url_for('admin'))
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM patient_scheme_enrollment WHERE enrollment_id = %s', (enrollment_id,))
        conn.commit()
        flash('Enrollment deleted successfully!', 'success')
    except Error as e:
        conn.rollback()
        flash(f'Error deleting enrollment: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    """Admin dashboard for analysis"""
    conn = get_db()
    if not conn:
        flash('Database connection failed', 'error')
        return render_template('admin.html', 
                             total_patients=0, total_schemes=0, total_claimed=0,
                             scheme_stats=[], recent_enrollments=[], all_patients=[])
    
    cursor = conn.cursor()
    
    try:
        # Total statistics
        cursor.execute('SELECT COUNT(*) FROM patient')
        total_patients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scheme')
        total_schemes = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amt_claimed) FROM patient_scheme_enrollment')
        result = cursor.fetchone()
        total_claimed = float(result[0]) if result[0] else 0
        
        cursor.execute('''
            SELECT s.scheme_id, s.sname, COUNT(pse.enrollment_id) as enrollment_count, 
                   SUM(pse.amt_claimed) as total_amount
            FROM scheme s
            LEFT JOIN patient_scheme_enrollment pse ON s.scheme_id = pse.scheme_id
            GROUP BY s.scheme_id, s.sname
            ORDER BY s.sname
        ''')
        scheme_stats_raw = cursor.fetchall()
        scheme_stats = [{'scheme_id': s[0], 'sname': s[1], 'enrollment_count': s[2] or 0, 'total_amount': float(s[3] or 0)} for s in scheme_stats_raw]
        
        cursor.execute('''
            SELECT pse.enrollment_id, p.patient_id, p.name, s.scheme_id, s.sname, pse.enroll_date, pse.amt_claimed
            FROM patient_scheme_enrollment pse
            JOIN patient p ON pse.patient_id = p.patient_id
            JOIN scheme s ON pse.scheme_id = s.scheme_id
            ORDER BY pse.enroll_date DESC
            LIMIT 10
        ''')
        recent_enrollments_raw = cursor.fetchall()
        recent_enrollments = [
            {
                'enrollment_id': e[0],
                'patient_id': e[1],
                'name': e[2],
                'scheme_id': e[3],
                'sname': e[4],
                'enroll_date': str(e[5]),
                'amt_claimed': float(e[6])
            }
            for e in recent_enrollments_raw
        ]
        
        cursor.execute('''
            SELECT p.patient_id, p.name, p.dob, p.email, COUNT(pse.enrollment_id) as scheme_count
            FROM patient p
            LEFT JOIN patient_scheme_enrollment pse ON p.patient_id = pse.patient_id
            GROUP BY p.patient_id, p.name, p.dob, p.email
            ORDER BY p.patient_id DESC
        ''')
        all_patients_raw = cursor.fetchall()
        all_patients = [
            {'patient_id': p[0], 'name': p[1], 'dob': str(p[2]), 'email': p[3], 'scheme_count': p[4]}
            for p in all_patients_raw
        ]
    except Error as e:
        print(f"Error fetching admin data: {e}")
        total_patients = total_schemes = 0
        total_claimed = 0
        scheme_stats = recent_enrollments = all_patients = []
    finally:
        cursor.close()
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
