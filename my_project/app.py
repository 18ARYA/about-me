import sqlite3
import pandas as pd
from fpdf import FPDF
import os
import logging
from datetime import datetime
from flask import Flask, request, session, redirect, url_for, flash, send_file, render_template

# --- Configuration ---
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')
    DATABASE_NAME = 'users.db'
    EXCEL_FILE_NAME = 'users.xlsx'
    PDF_OUTPUT_DIR = 'pdfs'

# --- Initialize Flask App ---
app = Flask(__name__)
app.config.from_object(Config)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
os.makedirs(app.config['PDF_OUTPUT_DIR'], exist_ok=True)

# --- Database Setup ---
def init_db():
    try:
        with sqlite3.connect(app.config['DATABASE_NAME']) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    submission_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")

# --- Helper Functions ---
def save_to_sqlite(user_data):
    try:
        with sqlite3.connect(app.config['DATABASE_NAME']) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (name, contact, age) VALUES (?, ?, ?)",
                      (user_data['name'], user_data['contact'], user_data['age']))
            conn.commit()
            logging.info(f"Saved to DB: {user_data['name']}")
            return True
    except sqlite3.Error as e:
        logging.error(f"DB error saving {user_data['name']}: {e}")
        return False

def save_to_excel(user_data):
    path = app.config['EXCEL_FILE_NAME']
    try:
        new_df = pd.DataFrame([user_data])
        if os.path.exists(path):
            existing_df = pd.read_excel(path)
            df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            df = new_df
        df.to_excel(path, index=False)
        logging.info(f"Saved to Excel: {user_data['name']}")
        return True
    except Exception as e:
        logging.error(f"Excel error for {user_data['name']}: {e}")
        return False

def generate_pdf(user_data):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="User Submission Details", ln=True, align="C")
        pdf.ln(10)
        for key, value in user_data.items():
            pdf.cell(200, 10, txt=f"{key.capitalize()}: {value}", ln=True)
        pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)

        filename = f"{user_data['name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        path = os.path.join(app.config['PDF_OUTPUT_DIR'], filename)
        pdf.output(path)
        logging.info(f"PDF generated: {path}")
        return path
    except Exception as e:
        logging.error(f"PDF generation failed: {e}")
        return None

# --- Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/news')
def news():
    return render_template('news.html')

@app.route('/form')
def form_page():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit_user_data():
    name = request.form.get('name', '').strip()
    contact = request.form.get('email', '').strip()  # Updated to match the form field
    age_str = request.form.get('age', '').strip()


    # 1. Input Validation
    if not name or not contact or not age_str:
        flash("All fields are required.", 'error')
        return redirect(url_for('form_page'))

    if not (2 <= len(name) <= 100):
        flash("Name must be between 2 and 100 characters.", 'error')
        return redirect(url_for('form_page'))

    if not (5 <= len(contact) <= 200):
        flash("Email must be between 5 and 200 characters.", 'error')
        return redirect(url_for('form_page'))

    try:
        age_int = int(age_str)
        if not (1 <= age_int <= 119):
            flash("Age must be between 1 and 119.", 'error')
            return redirect(url_for('form_page'))
    except ValueError:
        flash("Invalid age. Must be a number.", 'error')
        return redirect(url_for('form_page'))

    user_data = {
        'name': name,
        'contact': contact,
        'age': age_int
    }

    # Save operations (SQLite, Excel, PDF)
    save_to_sqlite(user_data)
    save_to_excel(user_data)
    pdf_path = generate_pdf(user_data)
    session['pdf_file_to_download'] = pdf_path

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (name, contact, age) VALUES (?, ?, ?)', (name, contact, age_int))
    conn.commit()
    conn.close()

    flash('Form submitted successfully!', 'success')
    return redirect(url_for('thank_you'))

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')


@app.route('/download_pdf')
def download_pdf():
    pdf_path = session.pop('pdf_file_to_download', None)
    if pdf_path and os.path.exists(pdf_path):
        try:
            return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
        except Exception as e:
            logging.error(f"PDF download error: {e}")
            flash("Could not download PDF.", 'error')
    else:
        flash("No PDF available.", 'error')
    return redirect(url_for('form_page'))

# --- Run App ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
