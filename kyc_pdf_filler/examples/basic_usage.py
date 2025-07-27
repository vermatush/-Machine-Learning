"""
Basic usage example for the KYC PDF Filler.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import KYCProcessor, process_kyc_transcript


def basic_example():
    """Basic example of using the KYC PDF Filler."""
    
    # File paths
    transcript_path = "examples/sample_transcript.txt"
    pdf_template_path = "examples/sample_kyc_form.pdf"  # You would need to provide this
    output_path = "examples/filled_kyc_form.pdf"
    
    print("=== KYC PDF Filler - Basic Usage Example ===\n")
    
    # Method 1: Using the convenience function
    print("Method 1: Using convenience function")
    
    if os.path.exists(transcript_path) and os.path.exists(pdf_template_path):
        results = process_kyc_transcript(
            transcript_path=transcript_path,
            pdf_template_path=pdf_template_path,
            output_path=output_path
        )
        
        print(f"Success: {results['success']}")
        print(f"Completion: {results['completion_percentage']:.1f}%")
        print(f"Notes: {results['processing_notes']}")
    else:
        print("PDF template not found, skipping PDF filling example")
    
    print("\n" + "="*50 + "\n")
    
    # Method 2: Using the processor class for more control
    print("Method 2: Using KYCProcessor class")
    
    processor = KYCProcessor(use_transformers=False)  # Disable transformers for faster processing
    
    # Step 1: Extract KYC data from transcript
    if os.path.exists(transcript_path):
        print("Extracting KYC data from transcript...")
        extraction_result = processor.extract_kyc_from_transcript(transcript_path)
        
        print(f"Extraction completed: {extraction_result.kyc_data.get_completion_percentage():.1f}% complete")
        
        # Show extracted data
        kyc_data = extraction_result.kyc_data
        print("\nExtracted Information:")
        
        if kyc_data.personal_info.first_name:
            print(f"  Name: {kyc_data.personal_info.first_name} {kyc_data.personal_info.last_name}")
        if kyc_data.personal_info.email:
            print(f"  Email: {kyc_data.personal_info.email}")
        if kyc_data.personal_info.phone_number:
            print(f"  Phone: {kyc_data.personal_info.phone_number}")
        if kyc_data.employment_info.annual_income:
            print(f"  Income: ${kyc_data.employment_info.annual_income:,.2f}")
        if kyc_data.investment_profile.risk_tolerance:
            print(f"  Risk Tolerance: {kyc_data.investment_profile.risk_tolerance.value}")
        
        # Step 2: Save extracted data to JSON
        import json
        output_json = "examples/extracted_kyc_data.json"
        with open(output_json, 'w') as f:
            json.dump(kyc_data.to_dict(), f, indent=2, default=str)
        print(f"\nExtracted data saved to: {output_json}")
        
        # Step 3: Fill PDF if template exists
        if os.path.exists(pdf_template_path):
            print("\nFilling PDF form...")
            success = processor.fill_pdf_with_kyc_data(
                kyc_data=kyc_data,
                pdf_template_path=pdf_template_path,
                output_path=output_path
            )
            
            if success:
                print(f"PDF filled successfully: {output_path}")
            else:
                print("Failed to fill PDF")
        else:
            print("PDF template not available for filling")
    
    print("\n" + "="*50 + "\n")
    
    # Method 3: Analyze a PDF form (if available)
    print("Method 3: PDF Form Analysis")
    
    if os.path.exists(pdf_template_path):
        print("Analyzing PDF form structure...")
        analysis = processor.analyze_pdf_form(pdf_template_path)
        
        print(f"Pages: {analysis.get('pages', 0)}")
        print(f"Has fillable fields: {analysis.get('has_fillable_fields', False)}")
        print(f"Total fields: {len(analysis.get('fields', []))}")
        
        if analysis.get('fields'):
            print("\nFields found:")
            for field in analysis['fields'][:5]:  # Show first 5 fields
                print(f"  - {field['name']} ({field['type']})")
    else:
        print("No PDF template available for analysis")


def demonstrate_template_management():
    """Demonstrate template creation and management."""
    
    print("=== Template Management Example ===\n")
    
    processor = KYCProcessor()
    
    # List existing templates
    templates = processor.list_templates()
    print(f"Existing templates: {templates}")
    
    # Create a template from PDF (if available)
    pdf_path = "examples/sample_kyc_form.pdf"
    if os.path.exists(pdf_path):
        template_name = "sample_kyc_template"
        success = processor.create_template_from_pdf(pdf_path, template_name)
        
        if success:
            print(f"Created template: {template_name}")
            
            # Show template details
            template = processor.get_template(template_name)
            if template:
                print(f"Template has {len(template.field_mappings)} field mappings")
        else:
            print("Failed to create template")
    else:
        print("No PDF available for template creation")


if __name__ == "__main__":
    # Run the basic example
    basic_example()
    
    print("\n" + "="*60 + "\n")
    
    # Demonstrate template management
    demonstrate_template_management()
    
    print("\n=== Example completed ===")
    print("\nTo run this with your own files:")
    print("1. Place your meeting transcript in examples/sample_transcript.txt")
    print("2. Place your KYC PDF form in examples/sample_kyc_form.pdf")
    print("3. Run this script again")