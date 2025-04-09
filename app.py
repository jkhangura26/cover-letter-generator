import os
from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from google import genai
from pypdf import PdfReader
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import fonts
from datetime import datetime

load_dotenv()  # Load environment variables from a .env file

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'generated'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.secret_key = 'supersecretkey' 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Ensure required folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Set your Gemini API key from environment variable
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', None)
NAME = os.getenv('NAME', 'Your Name')
PHONE = os.getenv('PHONE', 'Your Phone')
EMAIL = os.getenv('EMAIL', 'Your Email')
LINKEDIN = os.getenv('LINKEDIN', 'Your LinkedIn')
PERSONAL_WEBSITE = os.getenv('PERSONAL_WEBSITE', 'Your Website')

if not app.config['GEMINI_API_KEY']:
    raise ValueError("Please set the environment variable GEMINI_API_KEY")

# Configure the Gemini API client
client = genai.Client(api_key=app.config['GEMINI_API_KEY'])

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath):
    """Extract text from a PDF file given its file path."""
    text = ""
    reader = PdfReader(filepath)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def generate_cover_letter(resume_text, job_description, tone, focus):
    """Generate a cover letter using the Gemini API, incorporating writing references and additional tone/focus settings."""
    
    # Read the contents of the reference files
    reference_texts = []
    for i in range(1, 5):
        file_name = f"{i}.txt"
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as file:
                reference_texts.append(file.read())
    references = "\n\n".join(reference_texts)

    # Construct the prompt with additional tone and focus instructions
    prompt = (
        f"You are a professional cover letter generator. Your task is to create a clear, concise, and tailored cover letter.\n\n"
        f"Resume Details:\n{resume_text}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Tone Preference: {tone}\n"
        f"Focus Areas: {focus}\n\n"
        f"Cover Letter Guides for Reference:\n{references}\n\n"
        "Instructions:\n"
        "1. Generate a tailored cover letter that highlights the candidate's skills and experience while aligning with the job requirements.\n"
        "2. The cover letter must be structured with the following parts:\n"
        "   - An introduction starting with 'Dear Hiring Manager' (or the specific name if available).\n"
        "   - Two body paragraphs.\n"
        "   - A conclusion paragraph.\n"
        "3. Do not leave any placeholders or blank fields; fill in all information using the provided details.\n"
        "4. Exclude any extraneous commentary—only include the cover letter content.\n"
        "5. Maintain a professional tone that reflects the selected tone preference and focus areas. The final cover letter should fit on one page.\n"
        "6. Do not write the 'Sincerely' part or the name after.\n"
        "7. There is no need to mention where the job came from.\n\n"
        "Please generate the cover letter based on the above guidelines."
    )

    # Call Gemini API
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    return response.text

def save_cover_letter_to_pdf(cover_body, output_path):
    """Generate professional cover letter PDF with a clean and modern header layout."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    margin = 72  # 1 inch margins

    # Register fonts (ensure that the .ttf files are in place)
    pdfmetrics.registerFont(TTFont("name", "name.ttf"))
    pdfmetrics.registerFont(TTFont("regular", "reg.ttf"))
    pdfmetrics.registerFont(TTFont("CursiveFont", "cursive.ttf"))

    # ===== Header Section =====
    name_parts = NAME.split()  # Split the name into parts (first, last, etc.)
    contact_info = [PHONE, EMAIL, LINKEDIN, PERSONAL_WEBSITE]

    # Calculate positions for the header
    name_font_size = 34
    contact_font_size = 10
    c.setFont("name", name_font_size)
    
    name_column = margin  # Left-aligned name column
    y_name = height - margin
    for part in name_parts:
        c.drawString(name_column, y_name, part)
        y_name -= 38  # Name line spacing

    # Draw contact info (right-aligned)
    c.setFont("regular", contact_font_size)
    y_contact = height - margin + 10
    for line in contact_info:
        x_contact = width - margin - c.stringWidth(line, "regular", contact_font_size)
        c.drawString(x_contact, y_contact, line)
        y_contact -= 14  # Contact line spacing

    # Separator lines
    lowest_y = min(y_name, y_contact)
    line_y = lowest_y + 7
    c.setLineWidth(1)
    c.line(margin, line_y, width - margin, line_y)
    c.line(margin, line_y - 4, width - margin, line_y - 4)

    # Draw date
    current_date = datetime.now().strftime("%B %d, %Y")
    c.setFont("regular", 12)
    date_width = c.stringWidth(current_date, "regular", 12)
    date_y = line_y - 30
    c.drawString(width - margin - date_width, date_y, current_date)

    # ===== Body Section =====
    y_position = date_y + 4
    body_style = ParagraphStyle(
        'Body',
        fontName='regular',
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        firstLineIndent=36,
        spaceAfter=16
    )
    none_style = ParagraphStyle(
        'Body',
        fontName='regular',
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=16
    )

    paragraphs = [p.strip() for p in cover_body.split('\n\n') if p.strip()]
    first_paragraph = True

    for para in paragraphs:
        style = none_style if first_paragraph else body_style
        first_paragraph = False
        p = Paragraph(para.replace('\n', '<br/>'), style)
        w, p_height = p.wrap(width - 2 * margin, height)
        if y_position - p_height < margin + 100:  # Page break check
            c.showPage()
            y_position = height - margin
        p.drawOn(c, margin, y_position - p_height)
        y_position -= p_height + style.spaceAfter

    # ===== Signature Section =====
    y_position -= 40  # Space above signature
    c.setFont("regular", 12)
    c.drawString(margin, y_position, "Sincerely,")
    c.drawString(margin, y_position - 20, NAME)
    c.setFont("CursiveFont", 27)
    sig_width = c.stringWidth(NAME, "CursiveFont", 27)
    c.drawString(width - margin - sig_width, y_position - 20, NAME)

    c.save()

@app.route('/', methods=['GET'])
def index():
    """Render the main form where users can upload their resume, enter the job description, and choose tone/focus."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """
    Process the submitted form data (PDF resume, job description, tone, and focus),
    generate a tailored cover letter via the Gemini API, and return it as a downloadable PDF.
    """
    job_description = request.form.get('job_description')
    tone = request.form.get('tone', 'Professional and personable')
    focus = request.form.get('focus', 'Highlight relevant skills and experiences')

    if 'resume' not in request.files or request.files['resume'].filename == '':
        flash('Please upload a PDF resume file.')
        return redirect(url_for('index'))

    file = request.files['resume']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        resume_text = extract_text_from_file(filepath)
    else:
        flash('Invalid file type. Allowed type: pdf.')
        return redirect(url_for('index'))

    if not resume_text or not job_description:
        flash('Please provide both resume details and a job description.')
        return redirect(url_for('index'))

    try:
        cover_letter = generate_cover_letter(resume_text, job_description, tone, focus)
    except Exception as e:
        return f"An error occurred during generation: {str(e)}"

    pdf_filename = f"cover_letter_{NAME.replace(' ', '_')}.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    save_cover_letter_to_pdf(cover_letter, output_path)

    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
