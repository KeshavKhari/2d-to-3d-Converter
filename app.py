from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
import sqlite3
import os
from image import process_image  # Import the process_image function

app = Flask(__name__)
app.config['SECRET_KEY'] = '10'  # Necessary for CSRF protection
app.config['UPLOAD_FOLDER'] = '/Users/keshavkhari/Desktop/Coding/SE/flask/images'  # Directory to save uploaded images
app.config['UPLOADED_IMAGES_DEST'] = app.config['UPLOAD_FOLDER']  # For Flask-Uploads

# Configure Flask-Uploads
images = UploadSet('images', IMAGES)
configure_uploads(app, images)

# Form class for file upload using Flask-WTF
class UploadForm(FlaskForm):
    image = FileField('Image', validators=[FileRequired()])

# Ensure the images directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database if it doesn't exist
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

init_db()  # Run database initialization

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_page', methods=['GET', 'POST'])
def upload_page():
    form = UploadForm()
    if form.validate_on_submit():  # Checks if the form was submitted and is valid
        file = form.image.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        images.save(file, name=filename)  # Saves file using Flask-Uploads

        # Call the image processing function
        processed_image_path = process_image(filepath)

        # Return the processed image path to display the result
        return render_template('output.html', processed_image=processed_image_path)
    return render_template('inp_out.html', form=form)

# Route for user signup
@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
        conn.commit()
        message = "Signup successful! You can now log in."
    except sqlite3.IntegrityError:
        message = "Signup failed. Username already exists."
    conn.close()

    return render_template('index.html', message=message)

# Route for user login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return redirect(url_for('upload_page'))  # Redirect to upload page after login
    else:
        return render_template('index.html', message="Login Failed! Invalid username or password.")

@app.route('/media/upload', methods=['POST'])
def upload_media():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'media not provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'no file selected'}), 400
    
    if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in IMAGES:  # Verify file extension
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'success': True, 'message': 'media uploaded successfully'}), 200

    return jsonify({'success': False, 'message': 'invalid file type'}), 400

# Route to serve processed image
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
