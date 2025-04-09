import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, flash, send_file, session
from werkzeug.utils import secure_filename
from google import genai
from pypdf import PdfReader
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Load environment variables from .env
load_dotenv()

# Basic logging configuration
logging.basicConfig(level=logging.INFO)

# Flask app configuration
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'generated'
ALLOWED_EXTENSIONS = {'pdf'}

# Set a permanent session lifetime (here, one day)
app.permanent_session_lifetime = timedelta(days=1)

# Ensure required folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Environment variables for contact info
NAME = os.getenv('NAME', 'Your Name')
PHONE = os.getenv('PHONE', 'Your Phone')
EMAIL = os.getenv('EMAIL', 'Your Email')
LINKEDIN = os.getenv('LINKEDIN', 'Your LinkedIn')
PERSONAL_WEBSITE = os.getenv('PERSONAL_WEBSITE', 'Your Website')

# Set your Gemini API key
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')
if not app.config['GEMINI_API_KEY']:
    raise ValueError("Please set the environment variable GEMINI_API_KEY")

# Configure the Gemini API client
client = genai.Client(api_key=app.config['GEMINI_API_KEY'])


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(filepath):
    """Extract text from a PDF file given its path."""
    text = ""
    reader = PdfReader(filepath)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def generate_cover_letter(resume_text, job_description, tone, focus):
    """Generate a tailored cover letter using Gemini API with tone and focus settings."""
    reference_texts = []
    for i in range(1, 5):
        file_name = f"{i}.txt"
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as file:
                reference_texts.append(file.read())
    references = "\n\n".join(reference_texts)

    prompt = (
        f"You are a professional cover letter generator. Your task is to create a clear, concise, and tailored cover letter.\n\n"
        f"Resume Details:\n{resume_text}\n\n"
        f"Job Description:\n{job_description}\n\n"
        f"Tone Preference: {tone}\n"
        f"Focus Areas: {focus}\n\n"
        f"Cover Letter Guides for Reference:\n{references}\n\n"
        "Instructions:\n"
        "1. Generate a cover letter that highlights the candidate's skills and experience, aligning with the job requirements.\n"
        "2. Structure the letter with an introduction (starting with 'Dear Hiring Manager' or a specific name if available), two body paragraphs, and a conclusion paragraph.\n"
        "3. Do not include placeholders – use all provided details.\n"
        "4. Keep the tone professional and reflective of the tone and focus provided. Fit the content on one page.\n"
        "5. Exclude any 'Sincerely' part or name after the signature.\n\n"
        "6. Exclude any extraneous commentary—only include the cover letter content.\n"
        "Please generate the cover letter based on the above guidelines."
    )

    logging.info("Sending prompt to Gemini API...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[prompt]
    )
    logging.info("Cover letter generated successfully.")
    return response.text


def save_cover_letter_to_pdf(cover_body, output_path):
    """Generate a professional PDF (without a banner) with an enhanced header layout."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    margin = 72  # 1 inch margins

    # Register fonts (ensure corresponding .ttf files are available)
    pdfmetrics.registerFont(TTFont("name", "name.ttf"))
    pdfmetrics.registerFont(TTFont("regular", "reg.ttf"))
    pdfmetrics.registerFont(TTFont("CursiveFont", "cursive.ttf"))

    # ===== Header Section =====
    # Draw applicant name and contact details
    y_name = height - margin
    for part in NAME.split():
        c.setFont("name", 28)
        c.drawString(margin, y_name, part)
        y_name -= 32

    contact_info = [PHONE, EMAIL, LINKEDIN, PERSONAL_WEBSITE]
    y_contact = height - margin
    c.setFont("regular", 10)
    for line in contact_info:
        x_contact = width - margin - c.stringWidth(line, "regular", 10)
        c.drawString(x_contact, y_contact, line)
        y_contact -= 14

    # Separator lines
    lowest_y = min(y_name, y_contact)
    line_y = lowest_y + 7
    c.setLineWidth(1)
    c.line(margin, line_y, width - margin, line_y)
    c.line(margin, line_y - 4, width - margin, line_y - 4)

    # Date
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
    paragraphs = [p.strip() for p in cover_body.split('\n\n') if p.strip()]
    first_paragraph = True

    for para in paragraphs:
        style = body_style if not first_paragraph else ParagraphStyle(
            'First',
            fontName='regular',
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
            spaceAfter=16
        )
        first_paragraph = False
        p = Paragraph(para.replace('\n', '<br/>'), style)
        w, p_height = p.wrap(width - 2 * margin, height)
        if y_position - p_height < margin + 100:
            c.showPage()
            y_position = height - margin
        p.drawOn(c, margin, y_position - p_height)
        y_position -= p_height + style.spaceAfter

    # ===== Signature Section =====
    y_position -= 40
    c.setFont("regular", 12)
    c.drawString(margin, y_position, "Sincerely,")
    c.drawString(margin, y_position - 20, NAME)
    c.setFont("CursiveFont", 27)
    sig_width = c.stringWidth(NAME, "CursiveFont", 27)
    c.drawString(width - margin - sig_width, y_position - 20, NAME)

    c.save()


@app.route('/', methods=['GET'])
def index():
    """Display the form for uploading a resume and entering job details."""
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """
    Process the form data, generate the cover letter, store parameters in session,
    and then redirect to a results page that displays the PDF.
    """
    session.permanent = True  # Make the session permanent so data persists
    job_description = request.form.get('job_description')
    tone = request.form.get('tone') or "Professional and personable"
    focus = request.form.get('focus') or "Highlight relevant skills and experiences"

    # Process file upload
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
        flash('Invalid file type. Allowed type: PDF.')
        return redirect(url_for('index'))

    if not resume_text or not job_description:
        flash('Please provide both resume and job description.')
        return redirect(url_for('index'))

    # Save inputs in session so regeneration is possible
    session['resume_text'] = resume_text
    session['job_description'] = job_description
    session['tone'] = tone
    session['focus'] = focus

    try:
        cover_letter = generate_cover_letter(resume_text, job_description, tone, focus)
    except Exception as e:
        logging.error("Generation error: %s", str(e))
        flash(f"Error during generation: {str(e)}")
        return redirect(url_for('index'))

    pdf_filename = f"Cover_Letter_{NAME.replace(' ', '_')}.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    save_cover_letter_to_pdf(cover_letter, output_path)

    # Store PDF filename in session for easy regeneration
    session['pdf_filename'] = pdf_filename

    return redirect(url_for('result', filename=pdf_filename))


@app.route('/regenerate', methods=['GET'])
def regenerate():
    """
    Use the stored session parameters to regenerate the cover letter without requiring
    the user to re-upload their resume.
    """
    session.permanent = True  # Ensure session persists
    resume_text = session.get('resume_text')
    job_description = session.get('job_description')
    tone = session.get('tone', "Professional and personable")
    focus = session.get('focus', "Highlight relevant skills and experiences")

    if not resume_text or not job_description:
        flash("Session expired. Please generate your cover letter again.")
        return redirect(url_for('index'))

    try:
        cover_letter = generate_cover_letter(resume_text, job_description, tone, focus)
    except Exception as e:
        logging.error("Regeneration error: %s", str(e))
        flash(f"Error during regeneration: {str(e)}")
        return redirect(url_for('index'))

    pdf_filename = f"Cover_Letter_{NAME.replace(' ', '_')}.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    save_cover_letter_to_pdf(cover_letter, output_path)
    session['pdf_filename'] = pdf_filename
    return redirect(url_for('result', filename=pdf_filename))


@app.route('/result')
def result():
    """Render the result page with the embedded PDF."""
    filename = request.args.get('filename')
    if not filename:
        flash('Missing file.')
        return redirect(url_for('index'))
    # Pass a timestamp to help with cache busting.
    timestamp = int(datetime.now().timestamp())
    return render_template('result.html', filename=filename, timestamp=timestamp)

@app.route('/view/<filename>')
def view_pdf(filename):
    """Serve the generated PDF file for embedding/viewing."""
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename))


if __name__ == '__main__':
    app.run(debug=True)
