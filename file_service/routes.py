import os

from flask import Blueprint, request, redirect, url_for, send_from_directory, flash, current_app, render_template_string
from werkzeug.utils import secure_filename

from tools.logHandler import SingletonLogger

upload_bp = Blueprint('upload', __name__)
logging = SingletonLogger().logger
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'csv'}


@upload_bp.route('/', methods=['GET', 'POST'])
def upload_file():
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            flash('File successfully uploaded')
            return redirect(url_for('upload.uploaded_file', filename=filename))
        else:
            flash(f'可上传的文件类型={ALLOWED_EXTENSIONS}')

    files = os.listdir(current_app.config['UPLOAD_FOLDER'])
    return render_template_string('''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
        <form method=post enctype=multipart/form-data>
          <input type=file name=file>
          <input type=submit value=Upload>
        </form>
        <h2>Uploaded Files</h2>
        <ul>
        {% for file in files %}
          <li>
            <a href="{{ url_for('upload.uploaded_file', filename=file) }}">{{ file }}</a>
            <form method="post" action="{{ url_for('upload.delete_file', filename=file) }}" style="display:inline;">
              <button type="submit">Delete</button>
            </form>
          </li>
        {% endfor %}
        </ul>
        ''', files=files)


@upload_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@upload_bp.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    try:
        os.remove(file_path)
        flash('File successfully deleted')
    except FileNotFoundError:
        flash('File not found')
    except Exception as e:
        flash(f'An error occurred: {str(e)}')
    return redirect(url_for('upload.upload_file'))
