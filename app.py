from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import os
import io
import base64
import matplotlib 
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

DATABASE = 'hospital_schemes.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database"""
    if not os.path.exists(DATABASE):
        db = get_db()
        cursor = db.cursor()
        
        # Create SCHEME table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheme (
                scheme_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sname TEXT NOT NULL UNIQUE,
                dscript TEXT,
                start_date DATE NOT NULL
            )
        ''')
        
        # Create PATIENT table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dob DATE NOT NULL,
                email TEXT,
                address TEXT
            )
        ''')
        
        # Create PatientSchemeEnrollment table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_scheme_enrollment (
                enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                scheme_id INTEGER NOT NULL,
                enroll_date DATE NOT NULL,
                amt_claimed REAL DEFAULT 0,
                FOREIGN KEY(patient_id) REFERENCES patient(patient_id),
                FOREIGN KEY(scheme_id) REFERENCES scheme(scheme_id)
            )
        ''')
        
        # Insert sample schemes
        cursor.execute("INSERT INTO scheme (sname, dscript, start_date) VALUES ('Ayushman Bharat', 'Health insurance scheme', '2018-09-23')")
        cursor.execute("INSERT INTO scheme (sname, dscript, start_date) VALUES ('PMJAY', 'Prime Ministers Scheme', '2018-09-23')")
        
        db.commit()
        db.close()

# Initialize database on startup
init_db()

@app.route('/')
def home():
    """Home page"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM patient')
    total_patients = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM scheme')
    total_schemes = cursor.fetchone()['count']
    
    cursor.execute('SELECT SUM(amt_claimed) as total FROM patient_scheme_enrollment')
    total_claimed = cursor.fetchone()['total'] or 0
    
    db.close()
    
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
        amt_claimed = request.form.get('amt_claimed', 0)
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute('''
                INSERT INTO patient (name, dob, email, address)
                VALUES (?, ?, ?, ?)
            ''', (name, dob, email, address))
            
            patient_id = cursor.lastrowid
            
            if scheme_id:
                cursor.execute('''
                    INSERT INTO patient_scheme_enrollment (patient_id, scheme_id, enroll_date, amt_claimed)
                    VALUES (?, ?, ?, ?)
                ''', (patient_id, scheme_id, enroll_date, amt_claimed))
            
            db.commit()
            db.close()
            
            flash(f'Patient {name} added successfully!', 'success')
            return redirect(url_for('add_patient'))
        except Exception as e:
            flash(f'Error adding patient: {str(e)}', 'error')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT scheme_id, sname FROM scheme')
    schemes = cursor.fetchall()
    db.close()
    
    return render_template('add_patient.html', schemes=schemes)

@app.route('/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    """Edit patient details"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        dob = request.form.get('dob')
        email = request.form.get('email')
        address = request.form.get('address')
        
        try:
            cursor.execute('''
                UPDATE patient 
                SET name = ?, dob = ?, email = ?, address = ?
                WHERE patient_id = ?
            ''', (name, dob, email, address, patient_id))
            
            db.commit()
            flash(f'Patient {name} updated successfully!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f'Error updating patient: {str(e)}', 'error')
    
    cursor.execute('SELECT * FROM patient WHERE patient_id = ?', (patient_id,))
    patient = cursor.fetchone()
    db.close()
    
    if not patient:
        flash('Patient not found', 'error')
        return redirect(url_for('admin'))
    
    return render_template('edit_patient.html', patient=patient)

@app.route('/delete-patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    """Delete patient and their enrollments"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('SELECT name FROM patient WHERE patient_id = ?', (patient_id,))
        patient = cursor.fetchone()
        
        if patient:
            patient_name = patient['name']
            # Delete enrollments first (foreign key constraint)
            cursor.execute('DELETE FROM patient_scheme_enrollment WHERE patient_id = ?', (patient_id,))
            # Delete patient
            cursor.execute('DELETE FROM patient WHERE patient_id = ?', (patient_id,))
            
            db.commit()
            flash(f'Patient {patient_name} deleted successfully!', 'success')
        else:
            flash('Patient not found', 'error')
    except Exception as e:
        flash(f'Error deleting patient: {str(e)}', 'error')
    finally:
        db.close()
    
    return redirect(url_for('admin'))

@app.route('/edit-enrollment/<int:enrollment_id>', methods=['GET', 'POST'])
def edit_enrollment(enrollment_id):
    """Edit patient scheme enrollment"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        scheme_id = request.form.get('scheme_id')
        enroll_date = request.form.get('enroll_date')
        amt_claimed = request.form.get('amt_claimed', 0)
        
        try:
            cursor.execute('''
                UPDATE patient_scheme_enrollment 
                SET scheme_id = ?, enroll_date = ?, amt_claimed = ?
                WHERE enrollment_id = ?
            ''', (scheme_id, enroll_date, amt_claimed, enrollment_id))
            
            db.commit()
            flash('Enrollment updated successfully!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f'Error updating enrollment: {str(e)}', 'error')
    
    cursor.execute('''
        SELECT pse.*, p.name as patient_name, s.sname 
        FROM patient_scheme_enrollment pse
        JOIN patient p ON pse.patient_id = p.patient_id
        JOIN scheme s ON pse.scheme_id = s.scheme_id
        WHERE enrollment_id = ?
    ''', (enrollment_id,))
    enrollment = cursor.fetchone()
    
    cursor.execute('SELECT scheme_id, sname FROM scheme')
    schemes = cursor.fetchall()
    
    db.close()
    
    if not enrollment:
        flash('Enrollment not found', 'error')
        return redirect(url_for('admin'))
    
    return render_template('edit_enrollment.html', enrollment=enrollment, schemes=schemes)

@app.route('/delete-enrollment/<int:enrollment_id>', methods=['POST'])
def delete_enrollment(enrollment_id):
    """Delete patient scheme enrollment"""
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('DELETE FROM patient_scheme_enrollment WHERE enrollment_id = ?', (enrollment_id,))
        db.commit()
        flash('Enrollment deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting enrollment: {str(e)}', 'error')
    finally:
        db.close()
    
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    """Admin dashboard for analysis"""
    db = get_db()
    cursor = db.cursor()
    
    # Total statistics
    cursor.execute('SELECT COUNT(*) as count FROM patient')
    total_patients = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM scheme')
    total_schemes = cursor.fetchone()['count']
    
    
    cursor.execute('SELECT SUM(amt_claimed) as total FROM patient_scheme_enrollment')
    total_claimed = cursor.fetchone()['total'] or 0
    
    # Scheme-wise enrollment
    cursor.execute('''
        SELECT s.sname, COUNT(pse.enrollment_id) as enrollment_count, 
               SUM(pse.amt_claimed) as total_amount
        FROM scheme s
        LEFT JOIN patient_scheme_enrollment pse ON s.scheme_id = pse.scheme_id
        GROUP BY s.scheme_id, s.sname
    ''')
    scheme_stats = cursor.fetchall()
    
    # scheme_names = [row['sname'] for row in scheme_stats]
    # enrollment_counts = [row['enrollment_count'] for row in scheme_stats]

    # # 1. Create the figure
    # plt.figure(figsize=(10,6))
    
    # # 2. Plot the data
    # plt.bar(scheme_names, enrollment_counts, color='skyblue')
    
    # # 3. Add labels and title
    # plt.xlabel('Scheme Name')
    # plt.ylabel('Number of Enrollments')
    # plt.title('Enrollments per Scheme')
    # plt.xticks(rotation=15, ha='right') # Improve label visibility
    # plt.tight_layout()
    
    # # 4. Save figure to an in-memory buffer (BytesIO)
    # img = io.BytesIO()
    # plt.savefig(img, format='png')
    
    # # 5. Close the figure to free up memory (MANDATORY in web apps)
    # plt.close()
    
    # # 6. Rewind the buffer's cursor to the beginning
    # img.seek(0)
    
    # # 7. Encode the binary image data to a Base64 string
    # plot_url = base64.b64encode(img.getvalue()).decode()
    
    

    cursor.execute('''
        SELECT pse.enrollment_id, p.name, s.sname, pse.enroll_date, pse.amt_claimed
        FROM patient_scheme_enrollment pse
        JOIN patient p ON pse.patient_id = p.patient_id
        JOIN scheme s ON pse.scheme_id = s.scheme_id
        ORDER BY pse.enroll_date DESC
        LIMIT 10
    ''')
    recent_enrollments = cursor.fetchall()
    
    cursor.execute('''
        SELECT p.patient_id, p.name, p.dob, p.email, COUNT(pse.enrollment_id) as scheme_count
        FROM patient p
        LEFT JOIN patient_scheme_enrollment pse ON p.patient_id = pse.patient_id
        GROUP BY p.patient_id, p.name, p.dob, p.email
        ORDER BY p.patient_id DESC
    ''')
    all_patients = cursor.fetchall()
    
    db.close()
    
    return render_template('admin.html', 
                         total_patients=total_patients,
                         total_schemes=total_schemes,
                         total_claimed=total_claimed,
                         scheme_stats=scheme_stats,
                         recent_enrollments=recent_enrollments,
                         all_patients=all_patients)

if __name__ == '__main__':
    app.run(debug=True)
