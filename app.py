import logging
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
import os
from flask_cors import CORS, cross_origin
from pymongo import MongoClient
from datetime import datetime


# Initialize the Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max file size: 16MB
app.secret_key = 'supersecretkey'


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configure MongoDB
client = MongoClient("mongodb+srv://missingp:missing123@missingpersons.l4vcjps.mongodb.net/?retryWrites=true&w=majority&appName=MissingPersons")  # Change this if you're connecting to a remote MongoDB
db = client['missing_persons_db']
collection = db['missing_persons']

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def hoomepage():
    return render_template("index.html")

@app.route('/find', methods=['POST'])
def find_missing_person():
    try:
        # Extract data from the form submission
        location = request.form['location']
        start_date = datetime.strptime(request.form['startDate'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['endDate'], '%Y-%m-%d')
        
        logger.info(f"Searching for missing persons in {location} from {start_date} to {end_date}")

        # Query MongoDB based on the provided criteria
        missing_persons = collection.find({
            'last_seen_location': {'$regex': location, '$options': 'i'},
            'last_seen_date': {"$gte": start_date, "$lte": end_date}
        })

        # Convert MongoDB documents to a list of dictionaries
        results = []
        for person in missing_persons:
            results.append({
                 'file_path': person.get('file_path'),
                'filename': person.get('filename'),
                'last_seen_location': person.get('last_seen_location'),
                'last_seen_date': person.get('last_seen_date').strftime('%Y-%m-%d')
            })

        logger.info(f"Found {len(results)} missing persons matching the criteria")

        return render_template('search_results.html', results=results)
    
    except Exception as e:
        logger.error(f"Error finding missing persons: {e}")
        return str(e), 400

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'upload' not in request.files:
        flash('No file part', 'error')
        logger.warning("No file part in the request")
        return redirect(request.url)
    
    file = request.files['upload']
    if file.filename == '':
        flash('No selected file', 'error')
        logger.warning("No selected file in the request")
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        last_seen_location = request.form['lastSeenLocation']
        last_seen_date = request.form['lastSeenDate']

        logger.info(f"Uploading file {filename} and saving details to the database")

        # Save details to MongoDB
        missing_person = {
            'filename': filename,
            'file_path': os.path.join('uploads', filename),  # Store relative path
            'last_seen_location': last_seen_location,
            'last_seen_date': datetime.strptime(last_seen_date, '%Y-%m-%d')
        }
        collection.insert_one(missing_person)

        flash('File successfully uploaded and details saved', 'success')
        logger.info(f"File {filename} uploaded and details saved successfully")
        return redirect("/")
    else:
        flash('Allowed file types are png, jpg, jpeg, gif', 'error')
        logger.warning("Uploaded file type is not allowed")
        return redirect("/")

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
