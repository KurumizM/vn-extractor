import os
import cv2
import pytesseract
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# TODO: Users cloning this repo must point this to their Tesseract installation path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['video']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    cap = cv2.VideoCapture(filepath)
    success, frame = cap.read()
    cap.release()

    if success:
        preview_path = os.path.join(UPLOAD_FOLDER, 'preview.jpg')
        cv2.imwrite(preview_path, frame)
        return jsonify({'success': True, 'filename': file.filename, 'preview_url': '/uploads/preview.jpg'})
    
    return jsonify({'success': False, 'error': 'Could not read video'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/extract', methods=['POST'])
def extract_text():
    data = request.json
    filename = data['filename']
    x, y, w, h = int(data['x']), int(data['y']), int(data['w']), int(data['h'])
    
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps) if fps > 0 else 30 
    
    extracted_lines = []
    last_text = ""
    frame_count = 0

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        if frame_count % frame_interval == 0:
            cropped_frame = frame[y:y+h, x:x+w]
            gray = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2GRAY)
            # Add lang='jpn' here if translating Japanese visual novels
            text = pytesseract.image_to_string(gray).strip()
            
            if text and text != last_text:
                extracted_lines.append(text)
                last_text = text

        frame_count += 1

    cap.release()
    return jsonify({'script': "\n\n".join(extracted_lines)})

if __name__ == '__main__':
    app.run(debug=True)