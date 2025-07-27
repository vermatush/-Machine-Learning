"""
PDF processing module for reading and filling KYC PDF forms.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json

import PyPDF2
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfform
from reportlab.lib.colors import black
import pdfrw
from pdfrw import PdfReader, PdfWriter, PageMerge

from .models import KYCData, PDFFieldMapping, PDFFormTemplate

logger = logging.getLogger(__name__)


class PDFFormAnalyzer:
    """Analyzes PDF forms to identify fillable fields."""
    
    def __init__(self):
        """Initialize the PDF form analyzer."""
        pass
    
    def analyze_pdf_form(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze a PDF form to identify all fillable fields.
        
        Args:
            pdf_path: Path to the PDF form
            
        Returns:
            Dictionary containing form analysis results
        """
        form_info = {
            "fields": [],
            "pages": 0,
            "has_fillable_fields": False,
            "field_types": {},
            "analysis_notes": []
        }
        
        try:
            # Try using pdfrw first for form field analysis
            form_info.update(self._analyze_with_pdfrw(pdf_path))
        except Exception as e:
            logger.warning(f"pdfrw analysis failed: {e}")
            
        try:
            # Use pdfplumber for additional text analysis
            additional_info = self._analyze_with_pdfplumber(pdf_path)
            form_info.update(additional_info)
        except Exception as e:
            logger.warning(f"pdfplumber analysis failed: {e}")
            
        return form_info
    
    def _analyze_with_pdfrw(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze PDF using pdfrw library."""
        reader = PdfReader(pdf_path)
        
        info = {
            "pages": len(reader.pages),
            "fields": [],
            "has_fillable_fields": False
        }
        
        # Check if PDF has a form
        if reader.Root.AcroForm is None:
            info["analysis_notes"] = ["No AcroForm found in PDF"]
            return info
        
        # Extract field information
        fields = reader.Root.AcroForm.Fields
        if fields:
            info["has_fillable_fields"] = True
            
            for field in fields:
                field_info = self._extract_field_info(field)
                if field_info:
                    info["fields"].append(field_info)
        
        return info
    
    def _extract_field_info(self, field) -> Optional[Dict[str, Any]]:
        """Extract information from a PDF field object."""
        try:
            field_info = {
                "name": str(field.T) if field.T else "Unknown",
                "type": "text",  # Default type
                "value": str(field.V) if field.V else "",
                "rect": None,
                "options": []
            }
            
            # Determine field type
            if field.FT:
                ft = str(field.FT)
                if ft == "/Tx":
                    field_info["type"] = "text"
                elif ft == "/Btn":
                    field_info["type"] = "checkbox" if field.Ff and (field.Ff & 32768) else "radio"
                elif ft == "/Ch":
                    field_info["type"] = "dropdown"
                    # Extract options if available
                    if field.Opt:
                        field_info["options"] = [str(opt) for opt in field.Opt]
            
            # Extract position information
            if hasattr(field, 'Rect') and field.Rect:
                field_info["rect"] = [float(x) for x in field.Rect]
            
            return field_info
            
        except Exception as e:
            logger.warning(f"Error extracting field info: {e}")
            return None
    
    def _analyze_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze PDF using pdfplumber for text and layout analysis."""
        additional_info = {
            "text_content": "",
            "tables": [],
            "text_fields_detected": []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
                
                # Look for table-like structures
                tables = page.extract_tables()
                if tables:
                    additional_info["tables"].extend(tables)
                
                # Look for text that might indicate form fields
                text_fields = self._detect_text_fields(page_text if page_text else "")
                additional_info["text_fields_detected"].extend(text_fields)
            
            additional_info["text_content"] = full_text
        
        return additional_info
    
    def _detect_text_fields(self, text: str) -> List[str]:
        """Detect potential form fields from text content."""
        import re
        
        # Common patterns that indicate form fields
        field_patterns = [
            r"Name:?\s*_+",
            r"First Name:?\s*_+",
            r"Last Name:?\s*_+",
            r"Date of Birth:?\s*_+",
            r"SSN:?\s*_+",
            r"Phone:?\s*_+",
            r"Email:?\s*_+",
            r"Address:?\s*_+",
            r"City:?\s*_+",
            r"State:?\s*_+",
            r"ZIP:?\s*_+",
            r"Income:?\s*_+",
            r"Employment:?\s*_+",
        ]
        
        detected_fields = []
        for pattern in field_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            detected_fields.extend(matches)
        
        return detected_fields


class PDFFormFiller:
    """Fills PDF forms with extracted KYC data."""
    
    def __init__(self):
        """Initialize the PDF form filler."""
        self.field_mappings = {}
        
    def load_field_mappings(self, mappings: List[PDFFieldMapping]):
        """Load field mappings for KYC to PDF field translation."""
        self.field_mappings = {mapping.kyc_field_path: mapping for mapping in mappings}
    
    def create_default_mappings(self, pdf_fields: List[Dict[str, Any]]) -> List[PDFFieldMapping]:
        """
        Create default field mappings based on PDF field names.
        
        Args:
            pdf_fields: List of PDF field information
            
        Returns:
            List of PDFFieldMapping objects
        """
        mappings = []
        
        # Common field name mappings
        field_map = {
            # Personal Info
            "first": "personal_info.first_name",
            "firstname": "personal_info.first_name",
            "fname": "personal_info.first_name",
            "last": "personal_info.last_name",
            "lastname": "personal_info.last_name",
            "lname": "personal_info.last_name",
            "name": "personal_info.first_name",
            "dob": "personal_info.date_of_birth",
            "dateofbirth": "personal_info.date_of_birth",
            "birthdate": "personal_info.date_of_birth",
            "ssn": "personal_info.social_security_number",
            "socialsecurity": "personal_info.social_security_number",
            "phone": "personal_info.phone_number",
            "telephone": "personal_info.phone_number",
            "email": "personal_info.email",
            "marital": "personal_info.marital_status",
            
            # Address
            "address": "address.street_address",
            "street": "address.street_address",
            "city": "address.city",
            "state": "address.state",
            "zip": "address.zip_code",
            "zipcode": "address.zip_code",
            
            # Employment
            "employer": "employment_info.employer_name",
            "company": "employment_info.employer_name",
            "job": "employment_info.job_title",
            "position": "employment_info.job_title",
            "income": "employment_info.annual_income",
            "salary": "employment_info.annual_income",
            "networth": "employment_info.net_worth",
            
            # Investment
            "risk": "investment_profile.risk_tolerance",
            "risktolerance": "investment_profile.risk_tolerance",
            "objective": "investment_profile.investment_objective",
            "goal": "investment_profile.investment_objective",
            "experience": "investment_profile.investment_experience_years"
        }
        
        for field in pdf_fields:
            field_name = field["name"].lower().replace(" ", "").replace("_", "")
            
            # Try to match field name to KYC field
            kyc_field = None
            for pdf_key, kyc_key in field_map.items():
                if pdf_key in field_name:
                    kyc_field = kyc_key
                    break
            
            if kyc_field:
                mapping = PDFFieldMapping(
                    kyc_field_path=kyc_field,
                    pdf_field_name=field["name"],
                    field_type=field["type"]
                )
                mappings.append(mapping)
        
        return mappings
    
    def fill_pdf_form(self, pdf_path: str, kyc_data: KYCData, output_path: str, 
                      field_mappings: Optional[List[PDFFieldMapping]] = None) -> bool:
        """
        Fill a PDF form with KYC data.
        
        Args:
            pdf_path: Path to the input PDF form
            kyc_data: KYC data to fill the form with
            output_path: Path for the filled PDF output
            field_mappings: Optional field mappings, will create defaults if not provided
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Analyze the PDF form first
            analyzer = PDFFormAnalyzer()
            form_info = analyzer.analyze_pdf_form(pdf_path)
            
            if not form_info["has_fillable_fields"]:
                logger.warning("PDF does not appear to have fillable fields")
                return self._create_overlay_pdf(pdf_path, kyc_data, output_path)
            
            # Use provided mappings or create defaults
            if field_mappings is None:
                field_mappings = self.create_default_mappings(form_info["fields"])
            
            # Fill the form using pdfrw
            return self._fill_form_with_pdfrw(pdf_path, kyc_data, output_path, field_mappings)
            
        except Exception as e:
            logger.error(f"Error filling PDF form: {e}")
            return False
    
    def _fill_form_with_pdfrw(self, pdf_path: str, kyc_data: KYCData, 
                              output_path: str, field_mappings: List[PDFFieldMapping]) -> bool:
        """Fill form using pdfrw library."""
        try:
            reader = PdfReader(pdf_path)
            
            # Create field value mapping
            field_values = self._create_field_value_mapping(kyc_data, field_mappings)
            
            # Fill the form fields
            if reader.Root.AcroForm and reader.Root.AcroForm.Fields:
                for field in reader.Root.AcroForm.Fields:
                    field_name = str(field.T) if field.T else ""
                    
                    if field_name in field_values:
                        value = field_values[field_name]
                        
                        # Set field value based on field type
                        if field.FT == "/Tx":  # Text field
                            field.V = pdfrw.PdfString(str(value))
                        elif field.FT == "/Btn":  # Button/checkbox
                            if isinstance(value, bool):
                                field.V = pdfrw.PdfName("Yes" if value else "Off")
                        elif field.FT == "/Ch":  # Choice field
                            field.V = pdfrw.PdfString(str(value))
                        
                        # Make field read-only (optional)
                        field.Ff = 1
            
            # Write the filled form
            writer = PdfWriter()
            writer.trailer = reader
            writer.write(output_path)
            
            logger.info(f"Successfully filled PDF form: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error filling form with pdfrw: {e}")
            return False
    
    def _create_field_value_mapping(self, kyc_data: KYCData, 
                                    field_mappings: List[PDFFieldMapping]) -> Dict[str, Any]:
        """Create mapping from PDF field names to values from KYC data."""
        field_values = {}
        kyc_dict = kyc_data.to_dict()
        
        for mapping in field_mappings:
            try:
                # Navigate to the nested field value
                value = self._get_nested_value(kyc_dict, mapping.kyc_field_path)
                
                if value is not None:
                    # Apply transformation if specified
                    if mapping.transformation:
                        value = self._apply_transformation(value, mapping.transformation)
                    
                    field_values[mapping.pdf_field_name] = value
                    
            except Exception as e:
                logger.warning(f"Error mapping field {mapping.kyc_field_path}: {e}")
        
        return field_values
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field_path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _apply_transformation(self, value: Any, transformation: str) -> Any:
        """Apply transformation function to a value."""
        if transformation == "format_currency":
            if isinstance(value, (int, float)):
                return f"${value:,.2f}"
        elif transformation == "format_date":
            if hasattr(value, "strftime"):
                return value.strftime("%m/%d/%Y")
        elif transformation == "format_phone":
            if isinstance(value, str):
                digits = ''.join(filter(str.isdigit, value))
                if len(digits) == 10:
                    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif transformation == "uppercase":
            return str(value).upper()
        elif transformation == "title_case":
            return str(value).title()
        
        return value
    
    def _create_overlay_pdf(self, pdf_path: str, kyc_data: KYCData, output_path: str) -> bool:
        """
        Create an overlay PDF for forms without fillable fields.
        This is a fallback method that creates a new PDF with data overlaid.
        """
        try:
            # This is a simplified implementation
            # In practice, you'd need to determine positioning based on the original PDF
            
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # Create overlay with data
            overlay_path = output_path.replace('.pdf', '_overlay.pdf')
            c = canvas.Canvas(overlay_path, pagesize=letter)
            
            # Add text at predefined positions (this would need to be customized)
            y_position = 750
            if kyc_data.personal_info.first_name:
                c.drawString(100, y_position, f"First Name: {kyc_data.personal_info.first_name}")
                y_position -= 20
            
            if kyc_data.personal_info.last_name:
                c.drawString(100, y_position, f"Last Name: {kyc_data.personal_info.last_name}")
                y_position -= 20
            
            # Add more fields as needed...
            
            c.save()
            
            # Merge overlay with original PDF
            return self._merge_pdfs(pdf_path, overlay_path, output_path)
            
        except Exception as e:
            logger.error(f"Error creating overlay PDF: {e}")
            return False
    
    def _merge_pdfs(self, background_pdf: str, overlay_pdf: str, output_pdf: str) -> bool:
        """Merge two PDFs with overlay on top."""
        try:
            background = PdfReader(background_pdf)
            overlay = PdfReader(overlay_pdf)
            
            writer = PdfWriter()
            
            for i, page in enumerate(background.pages):
                if i < len(overlay.pages):
                    # Merge overlay page with background page
                    merger = PageMerge(page)
                    merger.add(overlay.pages[i]).render()
                
                writer.addPage(page)
            
            writer.write(output_pdf)
            
            # Clean up temporary overlay file
            Path(overlay_pdf).unlink(missing_ok=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error merging PDFs: {e}")
            return False


class PDFTemplateManager:
    """Manages PDF form templates and their field mappings."""
    
    def __init__(self, templates_dir: str = "templates"):
        """Initialize template manager."""
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
    
    def save_template(self, template: PDFFormTemplate) -> bool:
        """Save a PDF form template configuration."""
        try:
            template_file = self.templates_dir / f"{template.template_name}.json"
            
            with open(template_file, 'w') as f:
                json.dump(template.dict(), f, indent=2, default=str)
            
            logger.info(f"Saved template: {template.template_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False
    
    def load_template(self, template_name: str) -> Optional[PDFFormTemplate]:
        """Load a PDF form template configuration."""
        try:
            template_file = self.templates_dir / f"{template_name}.json"
            
            if not template_file.exists():
                logger.warning(f"Template not found: {template_name}")
                return None
            
            with open(template_file, 'r') as f:
                template_data = json.load(f)
            
            return PDFFormTemplate(**template_data)
            
        except Exception as e:
            logger.error(f"Error loading template: {e}")
            return None
    
    def list_templates(self) -> List[str]:
        """List available template names."""
        return [f.stem for f in self.templates_dir.glob("*.json")]
    
    def create_template_from_pdf(self, pdf_path: str, template_name: str) -> Optional[PDFFormTemplate]:
        """Create a template by analyzing a PDF form."""
        try:
            analyzer = PDFFormAnalyzer()
            form_info = analyzer.analyze_pdf_form(pdf_path)
            
            if not form_info["has_fillable_fields"]:
                logger.warning("PDF has no fillable fields for template creation")
                return None
            
            # Create default mappings
            filler = PDFFormFiller()
            field_mappings = filler.create_default_mappings(form_info["fields"])
            
            template = PDFFormTemplate(
                template_name=template_name,
                template_path=pdf_path,
                field_mappings=field_mappings
            )
            
            # Save the template
            if self.save_template(template):
                return template
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating template from PDF: {e}")
            return None