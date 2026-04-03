import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
import json
import PyPDF2
from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables from .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/upload-pdf')  # Update this URL if needed
port = os.environ.get('PORT', 10000)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173","https://pdf-chatbot-frontend-one.vercel.app"], supports_credentials=True, methods=["GET", "POST", "OPTIONS"])  # Allow frontend origin, all methods
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST','OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return '', 200
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Extract PDF to JSON after saving
        pdf_json = extract_pdf_to_json(filepath)
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{os.path.splitext(filename)[0]}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(pdf_json, f, ensure_ascii=False, indent=2)
        return jsonify({'message': 'File uploaded and extracted successfully', 'document_id': filename}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400


@app.route('/query', methods=['POST', 'OPTIONS'])
def query():
    """Endpoint for Q&A about uploaded PDF."""
    if request.method == 'OPTIONS':
        # CORS preflight
        return '', 200
    data = request.get_json()
    pdf_name = data.get('pdf_name')
    question = data.get('question')
    if not pdf_name or not question:
        return jsonify({'error': 'Missing data'}), 400
    json_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{os.path.splitext(pdf_name)[0]}.json')
    if not os.path.exists(json_path):
        return jsonify({'error': 'Extracted content not found'}), 404
    with open(json_path, 'r', encoding='utf-8') as f:
        pdf_content = json.load(f)
    # Flatten all lines for context (for demo; you may want to improve retrieval)
    all_lines = []
    for page, lines in pdf_content.items():
        all_lines.extend(lines)
    context = '\n'.join(all_lines)
    answer = ask_groq(question, context)
    return jsonify({'answer': answer})

# --- Helper functions ---
def extract_pdf_to_json(pdf_path):
    """
    Extracts PDF content page by page, line by line, and returns a dict {page_number: [lines]}
    """
    pdf_json = {}
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            lines = text.split('\n')
            pdf_json[f'page_{i+1}'] = lines
    return pdf_json

def ask_groq(question, context):
    """
    Uses Groq to answer the question based on the provided context.
    """
    from groq import Groq
    import os
    groq_api_key = os.environ.get('GROQ-API-KEY')
    if not groq_api_key:
        return "Groq API key not set."
    client = Groq(api_key=groq_api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer based only on the provided context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
            max_tokens=512,
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error querying Groq: {e}"


@app.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    """Alias for /query to support frontend calling /ask."""
    if request.method == 'OPTIONS':
        return '', 200
    return query()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
