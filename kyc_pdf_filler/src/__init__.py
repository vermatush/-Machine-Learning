"""
KYC PDF Filler - Automated tool for filling KYC forms from meeting transcripts.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .models import KYCData, ExtractionResult, PDFFormTemplate
from .transcript_processor import TranscriptProcessor
from .information_extractor import InformationExtractor
from .pdf_processor import PDFFormFiller, PDFTemplateManager, PDFFormAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class KYCProcessor:
    """
    Main processor class that orchestrates the entire KYC PDF filling workflow.
    """
    
    def __init__(self, use_transformers: bool = True, templates_dir: str = "templates"):
        """
        Initialize the KYC processor.
        
        Args:
            use_transformers: Whether to use transformer models for better NLP
            templates_dir: Directory to store PDF form templates
        """
        self.transcript_processor = TranscriptProcessor()
        self.information_extractor = InformationExtractor(use_transformers=use_transformers)
        self.pdf_filler = PDFFormFiller()
        self.template_manager = PDFTemplateManager(templates_dir)
        self.pdf_analyzer = PDFFormAnalyzer()
        
        logger.info("KYC Processor initialized successfully")
    
    def process_transcript_to_pdf(self, 
                                  transcript_path: str,
                                  pdf_template_path: str,
                                  output_path: str,
                                  template_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete workflow: process transcript and fill PDF form.
        
        Args:
            transcript_path: Path to the meeting transcript file
            pdf_template_path: Path to the PDF form template
            output_path: Path for the filled PDF output
            template_name: Optional name of saved template to use
            
        Returns:
            Dictionary containing processing results and metadata
        """
        results = {
            "success": False,
            "kyc_data": None,
            "extraction_result": None,
            "pdf_filled": False,
            "completion_percentage": 0.0,
            "processing_notes": [],
            "errors": []
        }
        
        try:
            # Step 1: Read and process transcript
            logger.info("Step 1: Processing transcript...")
            with open(transcript_path, 'r', encoding='utf-8') as f:
                raw_transcript = f.read()
            
            processed_transcript = self.transcript_processor.process_transcript(raw_transcript)
            results["processing_notes"].append(f"Processed {processed_transcript['total_segments']} transcript segments")
            
            # Step 2: Extract KYC information
            logger.info("Step 2: Extracting KYC information...")
            extraction_result = self.information_extractor.extract_kyc_data(processed_transcript)
            results["extraction_result"] = extraction_result
            results["kyc_data"] = extraction_result.kyc_data
            results["completion_percentage"] = extraction_result.kyc_data.get_completion_percentage()
            results["processing_notes"].extend(extraction_result.processing_notes)
            
            logger.info(f"Extracted KYC data with {results['completion_percentage']:.1f}% completion")
            
            # Step 3: Fill PDF form
            logger.info("Step 3: Filling PDF form...")
            
            # Use saved template if specified
            field_mappings = None
            if template_name:
                template = self.template_manager.load_template(template_name)
                if template:
                    field_mappings = template.field_mappings
                    results["processing_notes"].append(f"Using template: {template_name}")
                else:
                    results["processing_notes"].append(f"Template '{template_name}' not found, using defaults")
            
            # Fill the PDF
            pdf_success = self.pdf_filler.fill_pdf_form(
                pdf_template_path,
                extraction_result.kyc_data,
                output_path,
                field_mappings
            )
            
            results["pdf_filled"] = pdf_success
            
            if pdf_success:
                results["success"] = True
                results["processing_notes"].append(f"Successfully created filled PDF: {output_path}")
                logger.info(f"KYC PDF processing completed successfully")
            else:
                results["errors"].append("Failed to fill PDF form")
                
        except FileNotFoundError as e:
            error_msg = f"File not found: {e}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during processing: {e}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def analyze_pdf_form(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze a PDF form to understand its structure and fields.
        
        Args:
            pdf_path: Path to the PDF form
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            analysis = self.pdf_analyzer.analyze_pdf_form(pdf_path)
            logger.info(f"Analyzed PDF form: {len(analysis.get('fields', []))} fields found")
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing PDF form: {e}")
            return {"error": str(e)}
    
    def create_template_from_pdf(self, pdf_path: str, template_name: str) -> bool:
        """
        Create and save a template from a PDF form.
        
        Args:
            pdf_path: Path to the PDF form
            template_name: Name for the new template
            
        Returns:
            True if successful, False otherwise
        """
        try:
            template = self.template_manager.create_template_from_pdf(pdf_path, template_name)
            if template:
                logger.info(f"Created template '{template_name}' from PDF")
                return True
            else:
                logger.warning(f"Failed to create template from PDF")
                return False
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return False
    
    def extract_kyc_from_transcript(self, transcript_path: str) -> ExtractionResult:
        """
        Extract KYC data from transcript without PDF processing.
        
        Args:
            transcript_path: Path to the meeting transcript file
            
        Returns:
            ExtractionResult containing extracted KYC data
        """
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                raw_transcript = f.read()
            
            processed_transcript = self.transcript_processor.process_transcript(raw_transcript)
            extraction_result = self.information_extractor.extract_kyc_data(processed_transcript)
            
            logger.info(f"Extracted KYC data from transcript: {extraction_result.kyc_data.get_completion_percentage():.1f}% complete")
            return extraction_result
            
        except Exception as e:
            logger.error(f"Error extracting KYC from transcript: {e}")
            # Return empty result on error
            return ExtractionResult(
                kyc_data=KYCData(),
                processing_notes=[f"Error: {str(e)}"]
            )
    
    def fill_pdf_with_kyc_data(self, 
                               kyc_data: KYCData, 
                               pdf_template_path: str, 
                               output_path: str,
                               template_name: Optional[str] = None) -> bool:
        """
        Fill a PDF form with existing KYC data.
        
        Args:
            kyc_data: KYC data to fill the form with
            pdf_template_path: Path to the PDF form template
            output_path: Path for the filled PDF output
            template_name: Optional name of saved template to use
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use saved template if specified
            field_mappings = None
            if template_name:
                template = self.template_manager.load_template(template_name)
                if template:
                    field_mappings = template.field_mappings
            
            success = self.pdf_filler.fill_pdf_form(
                pdf_template_path,
                kyc_data,
                output_path,
                field_mappings
            )
            
            if success:
                logger.info(f"Successfully filled PDF form: {output_path}")
            else:
                logger.warning("Failed to fill PDF form")
                
            return success
            
        except Exception as e:
            logger.error(f"Error filling PDF with KYC data: {e}")
            return False
    
    def list_templates(self) -> list:
        """List all available PDF form templates."""
        return self.template_manager.list_templates()
    
    def get_template(self, template_name: str) -> Optional[PDFFormTemplate]:
        """Get a specific template by name."""
        return self.template_manager.load_template(template_name)


# Convenience function for simple usage
def process_kyc_transcript(transcript_path: str, 
                          pdf_template_path: str, 
                          output_path: str,
                          use_transformers: bool = True) -> Dict[str, Any]:
    """
    Convenience function to process a KYC transcript and fill a PDF form.
    
    Args:
        transcript_path: Path to the meeting transcript file
        pdf_template_path: Path to the PDF form template
        output_path: Path for the filled PDF output
        use_transformers: Whether to use transformer models for better NLP
        
    Returns:
        Dictionary containing processing results
    """
    processor = KYCProcessor(use_transformers=use_transformers)
    return processor.process_transcript_to_pdf(
        transcript_path, 
        pdf_template_path, 
        output_path
    )


# Export main classes and functions
__all__ = [
    "KYCProcessor",
    "process_kyc_transcript",
    "KYCData",
    "ExtractionResult",
    "PDFFormTemplate",
    "TranscriptProcessor",
    "InformationExtractor",
    "PDFFormFiller",
    "PDFTemplateManager",
    "PDFFormAnalyzer"
]