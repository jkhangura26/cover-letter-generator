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
app.secret_key = 'supersecretkey'  # Change for production use!
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Ensure required folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Set your Gemini API key from environment variable
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', None)
NAME = os.getenv('NAME', None)
PHONE = os.getenv('PHONE', None)
EMAIL = os.getenv('EMAIL', None)
LINKEDIN = os.getenv('LINKEDIN', None)
PERSONAL_WEBSITE = os.getenv('PERSONAL_WEBSITE', None)

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

def generate_cover_letter(resume_text, job_description):
    """Generate a cover letter using the Gemini API, incorporating writing references."""
    
    # Read the contents of the reference files
    reference_texts = []
    for i in range(1, 5):
        file_name = f"{i}.txt"
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as file:
                reference_texts.append(file.read())

    # Combine reference texts
    references = "\n\n".join(reference_texts)

    # Construct the prompt
    prompt = (
        f"You are a professional cover letter generator. Your task is to create a clear and concise cover letter.\n\n"
        f"Resume Details:\n{resume_text}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Cover Letter Guides for Reference:\n{references}\n\n"
        "Instructions:\n"
        "1. Generate a tailored cover letter that highlights the candidate's skills and experience, and aligns with the job requirements.\n"
        "2. The cover letter must be structured with the following parts:\n"
        "   - An introduction starting with 'Dear Hiring Manager' (or the specific name if available).\n"
        "   - Two body paragraphs.\n"
        "   - A conclusion paragraph.\n"
        "3. Do not leave any placeholders or blank fields; fill in all information using the provided details.\n"
        "4. Exclude any extraneous commentary—only include the cover letter content.\n"
        "5. Maintain a professional yet personable tone. The final cover letter should fit on one page.\n"
        "6. Do not write the sincerely part or name after.\n"
        "7. There is no need to mention where the job came from"
        "\n"
        "Please generate the cover letter based on the above guidelines."
    )

    # Call Gemini API
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )

    return response.text

def save_cover_letter_to_pdf(cover_body, output_path):
    """Generate professional cover letter PDF with redesigned header layout"""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    margin = 72  # 1 inch margins

    pdfmetrics.registerFont(TTFont("name", "name.ttf"))
    pdfmetrics.registerFont(TTFont("regular", "reg.ttf"))
    pdfmetrics.registerFont(TTFont("CursiveFont", "cursive.ttf"))

    # ===== Header Section =====
    # Retrieve contact information from environment variables
    name_parts = NAME.split()  # Split the name into parts (first, last, etc.)
    contact_info = [PHONE, EMAIL, LINKEDIN, PERSONAL_WEBSITE]

    # Calculate positions for the header
    name_font_size = 34
    contact_font_size = 10
    c.setFont("name", name_font_size)
    
    # Calculate name column width
    name_column = margin  # Left-aligned name column

    # Draw name parts
    y_name = height - margin
    for part in name_parts:
        x_name = name_column 
        c.drawString(x_name, y_name, part)
        y_name -= 38  # Name line spacing

    # Draw contact info (right-aligned)
    c.setFont("regular", contact_font_size)
    y_contact = height - margin + 10
    for line in contact_info:
        x_contact = width - margin - c.stringWidth(line, "regular", contact_font_size)
        c.drawString(x_contact, y_contact, line)
        y_contact -= 14  # Contact line spacing

    # Draw separator lines
    lowest_y = min(y_name, y_contact)
    line_y = lowest_y + 7  # Space below header content
    c.setLineWidth(1)
    c.line(margin, line_y, width - margin, line_y)
    c.line(margin, line_y - 4, width - margin, line_y - 4)

    # Draw date
    current_date = datetime.now().strftime("%B %d, %Y")
    c.setFont("regular", 12)
    date_width = c.stringWidth(current_date, "regular", 12)
    date_y = line_y - 30  # Space below separator lines
    c.drawString(width - margin - date_width, date_y, current_date)

    # ===== Body Section =====
    y_position = date_y + 4   # Space below date

    body_style = ParagraphStyle(
        'Body',
        fontName='regular',
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=0,
        spaceAfter=16,
        firstLineIndent=36
    )

    none_style = ParagraphStyle(
        'Body',
        fontName='regular',
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=0,
        spaceAfter=16
    )

    paragraphs = [p.strip() for p in cover_body.split('\n\n')]
    first_paragraph = True

    for para in paragraphs:
        if first_paragraph:
            p = Paragraph(para.replace('\n', '<br/>'), none_style)
            first_paragraph = False
        else:
            p = Paragraph(para.replace('\n', '<br/>'), body_style)
            
        p.wrap(width - 2*margin, height)
        p_height = p.wrap(width - 2*margin, height)[1]
        
        if y_position - p_height < margin + 100:  # Page break check
            c.showPage()
            y_position = height - margin
        
        p.drawOn(c, margin, y_position - p_height)
        y_position -= p_height + body_style.spaceAfter

    # ===== Signature Section =====
    y_position -= 40  # Space above signature
    c.setFont("regular", 12)
    c.drawString(margin, y_position, "Sincerely,")
    c.drawString(margin, y_position - 20, NAME)

    # Cursive signature
    c.setFont("CursiveFont", 27)
    sig_width = c.stringWidth(NAME, "CursiveFont", 27)
    c.drawString(width - margin - sig_width, y_position - 20, NAME)

    c.save()

@app.route('/', methods=['GET'])
def index():
    """Render the main form where users can upload their resume and enter the job description."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """
    Process the submitted form data (PDF resume file and job description),
    generate a tailored cover letter via the Gemini API, and return as a downloadable PDF.
    """
    job_description = request.form.get('job_description')

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
        cover_letter = generate_cover_letter(resume_text, job_description)
    except Exception as e:
        return f"An error occurred during generation: {str(e)}"

    # Save cover letter as a PDF
    pdf_filename = f"cover_letter_{NAME.replace(' ', '_')}.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    save_cover_letter_to_pdf(cover_letter, output_path)

    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
