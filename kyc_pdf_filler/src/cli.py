"""
Command-line interface for the KYC PDF Filler tool.
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from . import KYCProcessor, process_kyc_transcript


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """KYC PDF Filler - Automatically fill KYC forms from meeting transcripts."""
    pass


@cli.command()
@click.option('--transcript', '-t', required=True, type=click.Path(exists=True),
              help='Path to the meeting transcript file')
@click.option('--template', '-p', required=True, type=click.Path(exists=True),
              help='Path to the PDF form template')
@click.option('--output', '-o', required=True, type=click.Path(),
              help='Path for the filled PDF output')
@click.option('--template-name', '-n', type=str,
              help='Name of saved template to use for field mappings')
@click.option('--no-transformers', is_flag=True,
              help='Disable transformer models (faster but less accurate)')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def process(transcript: str, template: str, output: str, 
           template_name: Optional[str], no_transformers: bool, verbose: bool):
    """Process a transcript and fill a PDF form."""
    
    if verbose:
        click.echo(f"Processing transcript: {transcript}")
        click.echo(f"Using PDF template: {template}")
        click.echo(f"Output will be saved to: {output}")
    
    try:
        # Initialize processor
        processor = KYCProcessor(use_transformers=not no_transformers)
        
        # Process the transcript and fill PDF
        results = processor.process_transcript_to_pdf(
            transcript_path=transcript,
            pdf_template_path=template,
            output_path=output,
            template_name=template_name
        )
        
        # Display results
        if results["success"]:
            click.echo(click.style("✓ Success!", fg="green"))
            click.echo(f"Form completion: {results['completion_percentage']:.1f}%")
            click.echo(f"Output saved to: {output}")
            
            if verbose:
                click.echo("\nProcessing notes:")
                for note in results["processing_notes"]:
                    click.echo(f"  • {note}")
        else:
            click.echo(click.style("✗ Failed to process transcript", fg="red"))
            for error in results["errors"]:
                click.echo(f"Error: {error}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option('--transcript', '-t', required=True, type=click.Path(exists=True),
              help='Path to the meeting transcript file')
@click.option('--output', '-o', type=click.Path(),
              help='Path to save extracted data as JSON')
@click.option('--no-transformers', is_flag=True,
              help='Disable transformer models (faster but less accurate)')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def extract(transcript: str, output: Optional[str], no_transformers: bool, verbose: bool):
    """Extract KYC data from transcript without PDF processing."""
    
    if verbose:
        click.echo(f"Extracting KYC data from: {transcript}")
    
    try:
        processor = KYCProcessor(use_transformers=not no_transformers)
        result = processor.extract_kyc_from_transcript(transcript)
        
        completion = result.kyc_data.get_completion_percentage()
        click.echo(f"Extraction completed: {completion:.1f}% of fields populated")
        
        if verbose:
            click.echo("\nExtracted data summary:")
            kyc_dict = result.kyc_data.to_dict()
            for section, data in kyc_dict.items():
                if isinstance(data, dict) and any(v is not None for v in data.values()):
                    click.echo(f"  {section}:")
                    for field, value in data.items():
                        if value is not None:
                            click.echo(f"    {field}: {value}")
        
        if output:
            # Save extracted data to JSON
            with open(output, 'w') as f:
                json.dump(result.kyc_data.to_dict(), f, indent=2, default=str)
            click.echo(f"Data saved to: {output}")
            
    except Exception as e:
        click.echo(click.style(f"✗ Error extracting data: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option('--pdf', '-p', required=True, type=click.Path(exists=True),
              help='Path to the PDF form to analyze')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def analyze(pdf: str, verbose: bool):
    """Analyze a PDF form to identify fillable fields."""
    
    if verbose:
        click.echo(f"Analyzing PDF form: {pdf}")
    
    try:
        processor = KYCProcessor()
        analysis = processor.analyze_pdf_form(pdf)
        
        if "error" in analysis:
            click.echo(click.style(f"✗ Error analyzing PDF: {analysis['error']}", fg="red"))
            sys.exit(1)
        
        click.echo(f"PDF Analysis Results:")
        click.echo(f"  Pages: {analysis.get('pages', 0)}")
        click.echo(f"  Fillable fields: {analysis.get('has_fillable_fields', False)}")
        click.echo(f"  Total fields found: {len(analysis.get('fields', []))}")
        
        if verbose and analysis.get("fields"):
            click.echo("\nFields details:")
            for field in analysis["fields"]:
                click.echo(f"  • {field['name']} ({field['type']})")
                
        if analysis.get("text_fields_detected"):
            click.echo(f"\nText fields detected: {len(analysis['text_fields_detected'])}")
            if verbose:
                for field in analysis["text_fields_detected"][:10]:  # Show first 10
                    click.echo(f"  • {field}")
                    
    except Exception as e:
        click.echo(click.style(f"✗ Error analyzing PDF: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option('--pdf', '-p', required=True, type=click.Path(exists=True),
              help='Path to the PDF form')
@click.option('--name', '-n', required=True, type=str,
              help='Name for the new template')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def create_template(pdf: str, name: str, verbose: bool):
    """Create a reusable template from a PDF form."""
    
    if verbose:
        click.echo(f"Creating template '{name}' from: {pdf}")
    
    try:
        processor = KYCProcessor()
        success = processor.create_template_from_pdf(pdf, name)
        
        if success:
            click.echo(click.style(f"✓ Template '{name}' created successfully", fg="green"))
        else:
            click.echo(click.style(f"✗ Failed to create template", fg="red"))
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error creating template: {e}", fg="red"))
        sys.exit(1)


@cli.command()
def list_templates():
    """List all available PDF form templates."""
    
    try:
        processor = KYCProcessor()
        templates = processor.list_templates()
        
        if templates:
            click.echo("Available templates:")
            for template in templates:
                click.echo(f"  • {template}")
        else:
            click.echo("No templates found. Create one with 'create-template' command.")
            
    except Exception as e:
        click.echo(click.style(f"✗ Error listing templates: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option('--name', '-n', required=True, type=str,
              help='Name of the template to show')
def show_template(name: str):
    """Show details of a specific template."""
    
    try:
        processor = KYCProcessor()
        template = processor.get_template(name)
        
        if template:
            click.echo(f"Template: {template.template_name}")
            click.echo(f"PDF Path: {template.template_path}")
            click.echo(f"Created: {template.creation_date}")
            click.echo(f"Field mappings: {len(template.field_mappings)}")
            
            click.echo("\nField mappings:")
            for mapping in template.field_mappings:
                click.echo(f"  {mapping.kyc_field_path} → {mapping.pdf_field_name} ({mapping.field_type})")
        else:
            click.echo(click.style(f"✗ Template '{name}' not found", fg="red"))
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error showing template: {e}", fg="red"))
        sys.exit(1)


@cli.command()
@click.option('--kyc-data', '-k', required=True, type=click.Path(exists=True),
              help='Path to JSON file containing KYC data')
@click.option('--template', '-p', required=True, type=click.Path(exists=True),
              help='Path to the PDF form template')
@click.option('--output', '-o', required=True, type=click.Path(),
              help='Path for the filled PDF output')
@click.option('--template-name', '-n', type=str,
              help='Name of saved template to use for field mappings')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def fill_pdf(kyc_data: str, template: str, output: str, 
            template_name: Optional[str], verbose: bool):
    """Fill a PDF form with existing KYC data from JSON file."""
    
    if verbose:
        click.echo(f"Loading KYC data from: {kyc_data}")
        click.echo(f"Using PDF template: {template}")
    
    try:
        # Load KYC data from JSON
        with open(kyc_data, 'r') as f:
            kyc_dict = json.load(f)
        
        from .models import KYCData
        kyc_obj = KYCData(**kyc_dict)
        
        processor = KYCProcessor()
        success = processor.fill_pdf_with_kyc_data(
            kyc_obj, template, output, template_name
        )
        
        if success:
            click.echo(click.style("✓ PDF filled successfully", fg="green"))
            click.echo(f"Output saved to: {output}")
        else:
            click.echo(click.style("✗ Failed to fill PDF", fg="red"))
            sys.exit(1)
            
    except Exception as e:
        click.echo(click.style(f"✗ Error filling PDF: {e}", fg="red"))
        sys.exit(1)


if __name__ == '__main__':
    cli()