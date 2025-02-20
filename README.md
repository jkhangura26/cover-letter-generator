# Cover Letter Generator

This is a Flask-based application that generates a tailored cover letter PDF by processing a user's resume (in PDF format) and a provided job description. It leverages the Gemini API to generate professional cover letter content and uses ReportLab for PDF generation.

## Features

- **Resume Parsing:** Extracts text from uploaded PDF resumes.
- **Dynamic Cover Letter Generation:** Uses the Gemini API to generate a tailored cover letter based on the resume and job description.
- **Customizable Header:** Reads personal details (name, phone, email, LinkedIn, personal website) from environment variables.
- **PDF Output:** Generates a professional PDF with a custom header and signature section.
- **Reference Files:** Incorporates additional writing guides.


## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/jkhangura26/cover-letter-generator.git
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   > *Note:* Make sure you have access to the Gemini API library (`google-genai`) as used in the code.

## Configuration

1. **Create a `.env` file in the project root:**

   The application requires several environment variables for configuration. Create a file named `.env` and add the following:

   ```ini
   # Gemini API Key
   GEMINI_API_KEY=your_gemini_api_key_here

   # Personal information for header (replace with your details)
   NAME=Your Full Name
   PHONE=your_phone_number
   EMAIL=your_email_address
   LINKEDIN=your_linkedin_url
   PERSONAL_WEBSITE=your_personal_website_url
   ```

## Usage

1. **Run the Application:**

   With your virtual environment activated and environment variables configured, start the Flask server:

   ```bash
   python app.py
   ```

   The app will run in debug mode on [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

2. **Access the Web Interface:**

   Open your browser and navigate to [http://127.0.0.1:5000/](http://127.0.0.1:5000/). Use the provided form to:
   
   - Upload your PDF resume.
   - Enter a job description.

3. **Generate Cover Letter:**

   After submitting the form, the application will generate a tailored cover letter using the Gemini API, create a PDF with your personal header details, and prompt you to download the generated PDF.
