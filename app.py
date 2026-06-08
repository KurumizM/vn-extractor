import os
import cv2
import shutil
import re
import pytesseract
from difflib import SequenceMatcher
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for  # <--- Added url_for

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def find_tesseract_cmd():
    env_cmd = os.environ.get('TESSERACT_CMD')
    candidates = []
    if env_cmd:
        candidates.append(env_cmd)
    candidates.extend([
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ])

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    return shutil.which('tesseract')

tesseract_cmd = find_tesseract_cmd()
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
else:
    print('WARNING: Tesseract OCR executable not found. Install Tesseract and/or set TESSERACT_CMD to the executable path.')

def is_same_sentence(old_text, new_text):
    # Remove all spaces, punctuation, and garbage characters to compare pure letters
    clean_old = re.sub(r'\W+', '', old_text.lower())
    clean_new = re.sub(r'\W+', '', new_text.lower())
    
    if not clean_old or not clean_new: 
        return False
        
    # If the old text is almost entirely inside the new text (or vice versa)
    if clean_old in clean_new or clean_new in clean_old:
        return True
        
    # Check the longest continuous chunk of matching letters
    s = SequenceMatcher(None, clean_old, clean_new)
    match = s.find_longest_match(0, len(clean_old), 0, len(clean_new))
    
    # If 70% of the shorter text is perfectly inside the longer text, it's a match
    similarity = match.size / min(len(clean_old), len(clean_new))
    return similarity > 0.70

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Uploaded file has no filename'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        cap.release()
        return jsonify({'success': False, 'error': 'Could not open uploaded video file'}), 400

    success, frame = cap.read()
    cap.release()

    if success and frame is not None:
        preview_path = os.path.join(UPLOAD_FOLDER, 'preview.jpg')
        cv2.imwrite(preview_path, frame)
        return jsonify({
            'success': True,
            'filename': file.filename,
            'preview_url': url_for('uploaded_file', filename='preview.jpg')
        })

    return jsonify({'success': False, 'error': 'Could not read video frames'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/extract', methods=['POST'])
def extract_text():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Request must include JSON body'}), 400

    filename = data.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': 'Missing filename parameter'}), 400

    try:
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        w = int(data.get('width', 0))
        h = int(data.get('height', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Crop coordinates must be numeric'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(video_path):
        return jsonify({'success': False, 'error': 'Uploaded video not found'}), 404

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        return jsonify({'success': False, 'error': 'Could not open saved video file'}), 400

    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # TYPEWRITER FIX: Check 2 times a second instead of once
    frame_interval = int(fps / 2) if fps and fps > 0 else 15 

    extracted_lines = []
    frame_count = 0

    while cap.isOpened():
        success, frame = cap.read()
        if not success or frame is None:
            break

        if frame_count % frame_interval == 0:
            cropped_frame = frame[y:y+h, x:x+w]
            if cropped_frame.size == 0:
                cap.release()
                return jsonify({'success': False, 'error': 'Crop box is outside the frame bounds'}), 400

            gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
            
            # --- THE MAGIC BULLET 1: UPSCALING ---
            # Double the image size so Tesseract stops reading background noise as letters
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            try:
                raw_text = pytesseract.image_to_string(gray).strip()
                text = " ".join(raw_text.split())
            except pytesseract.TesseractNotFoundError:
                cap.release()
                return jsonify({'success': False, 'error': 'Tesseract OCR is not installed.'}), 500
            except pytesseract.TesseractError as exc:
                cap.release()
                return jsonify({'success': False, 'error': f'OCR failed: {exc}'}), 500

            # --- THE MAGIC BULLET 2: SMART MATCHING ---
            # Only process text if it has at least a few actual word characters
            if text and len(re.sub(r'\W+', '', text)) > 3:
                if not extracted_lines:
                    extracted_lines.append(text)
                else:
                    last_line = extracted_lines[-1]
                    
                    if text != last_line:
                        if is_same_sentence(last_line, text):
                            # It's the same sentence! Keep whichever one has MORE letters
                            if len(text) > len(last_line):
                                extracted_lines[-1] = text
                        else:
                            # It's a completely new dialogue box
                            extracted_lines.append(text)

        frame_count += 1
        
    cap.release()
    return jsonify({'success': True, 'script': "\n\n".join(extracted_lines)})

if __name__ == '__main__':
    app.run(debug=True)