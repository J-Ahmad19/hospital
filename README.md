# Hospital Government Schemes Monitoring System

A Flask-based web application for monitoring and managing government health schemes in hospitals with patient enrollment tracking.

## Features

- **Home Page**: Dashboard with key statistics
- **Patient Management**: Add new patients and enroll them in government schemes
- **Admin Dashboard**: Comprehensive analysis and reporting
- **Scheme Tracking**: Monitor enrollments and claimed amounts

## Database Schema

- **SCHEME**: Government health schemes (Ayushman Bharat, PMJAY, etc.)
- **PATIENT**: Patient information (name, DOB, email, address)
- **PATIENT_SCHEME_ENROLLMENT**: Links patients to schemes with enrollment and claim details

## Installation

1. Install Python dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

2. Run the Flask application:
\`\`\`bash
python app.py
\`\`\`

3. Open your browser and navigate to `http://localhost:5000`

## Usage

- **Home Page** (`/`): View system statistics
- **Add Patient** (`/add-patient`): Register new patients and enroll in schemes
- **Admin Dashboard** (`/admin`): View analytics and reports

## Project Structure

\`\`\`
.
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   ├── base.html         # Base template
│   ├── index.html        # Home page
│   ├── add_patient.html  # Patient entry form
│   └── admin.html        # Admin dashboard
└── static/
    └── style.css         # Stylesheet
\`\`\`

## Notes

- Database is automatically created on first run (SQLite)
- Two sample schemes are pre-populated
- All forms work without JavaScript as requested
