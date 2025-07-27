# KYC PDF Filler

An automated tool for filling KYC (Know Your Customer) PDF forms based on meeting transcripts between financial advisors and clients.

## Overview

This tool processes post-meeting transcripts and automatically extracts relevant client information to populate KYC PDF forms. It uses advanced NLP techniques to understand and map client responses to appropriate form fields.

## Features

- **Transcript Processing**: Cleans and segments meeting transcripts into Q&A pairs
- **Information Extraction**: Uses GPT-4 and other NLP models to extract KYC-relevant information
- **PDF Form Filling**: Automatically populates PDF form fields with extracted data
- **Field Mapping**: Intelligent mapping between extracted information and PDF form fields
- **Validation**: Data validation and error handling for form completion

## Installation

1. Clone or download this project
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Download spaCy model:
   ```bash
   python -m spacy download en_core_web_sm
   ```

## Usage

### Basic Usage

```python
from kyc_pdf_filler import KYCProcessor

# Initialize the processor
processor = KYCProcessor()

# Process transcript and fill PDF
processor.process_transcript_to_pdf(
    transcript_path="meeting_transcript.txt",
    pdf_template_path="kyc_form_template.pdf",
    output_path="filled_kyc_form.pdf"
)
```

### Command Line Interface

```bash
python -m kyc_pdf_filler --transcript transcript.txt --template form.pdf --output filled_form.pdf
```

## Project Structure

```
kyc_pdf_filler/
├── src/
│   ├── __init__.py
│   ├── transcript_processor.py    # Transcript cleaning and segmentation
│   ├── information_extractor.py  # NLP-based information extraction
│   ├── pdf_processor.py          # PDF reading and form filling
│   ├── field_mapper.py           # Mapping extracted data to PDF fields
│   └── models.py                 # Data models and schemas
├── examples/
│   ├── sample_transcript.txt
│   └── sample_kyc_form.pdf
├── tests/
├── requirements.txt
└── README.md
```

## Configuration

The tool can be configured through:
- Environment variables (`.env` file)
- Configuration file (`config.yaml`)
- Command line arguments

## Dependencies

- **PDF Processing**: PyPDF2, pdfplumber, reportlab
- **NLP**: transformers, spacy, sentence-transformers
- **Data Processing**: pydantic, pandas, numpy
- **Utilities**: click, tqdm, python-dotenv

## License

This project is intended for educational and professional use in financial advisory contexts.