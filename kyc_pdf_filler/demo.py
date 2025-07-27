#!/usr/bin/env python3
"""
Simple demo of KYC information extraction from transcript.
This demo works without external dependencies to show the concept.
"""

import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class SimpleKYCExtractor:
    """Simplified KYC information extractor for demonstration."""
    
    def __init__(self):
        """Initialize the extractor with basic patterns."""
        self.patterns = {
            'name': [
                r'(?:my name is|i\'?m|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'name.*?([A-Z][a-z]+\s+[A-Z][a-z]+)'
            ],
            'email': [
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ],
            'phone': [
                r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
                r'(\(\d{3}\)\s?\d{3}[-.\s]?\d{4})'
            ],
            'address': [
                r'(?:live at|address is?)\s+(.+?)(?:\.|,|$)',
                r'(\d+\s+[A-Za-z\s]+(?:st|street|ave|avenue|rd|road|blvd|dr|ln|ct),?\s+[A-Z][a-z]+,?\s+[A-Z]{2}\s+\d{5})'
            ],
            'income': [
                r'(?:make|earn|income).*?\$?([0-9,]+)',
                r'\$([0-9,]+).*?(?:year|annual)',
                r'([0-9,]+).*?(?:thousand|k).*?(?:year|annual)'
            ],
            'net_worth': [
                r'net worth.*?\$?([0-9,]+)',
                r'worth.*?\$?([0-9,]+)'
            ],
            'employment': [
                r'work at\s+([A-Z][A-Za-z\s&]+)',
                r'employed (?:by|at)\s+([A-Z][A-Za-z\s&]+)'
            ],
            'risk_tolerance': [
                r'(conservative|moderate|aggressive)(?:\s+risk)?',
                r'risk.*?(conservative|moderate|aggressive)'
            ]
        }
    
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract KYC information from text."""
        results = {}
        text_lower = text.lower()
        
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    
                    # Post-process specific fields
                    if field == 'income' and value:
                        if 'k' in value.lower():
                            value = str(int(re.sub(r'[^\d]', '', value)) * 1000)
                        else:
                            value = re.sub(r'[^\d]', '', value)
                    elif field == 'net_worth' and value:
                        value = re.sub(r'[^\d]', '', value)
                    
                    results[field] = value
                    break  # Use first match
        
        return results
    
    def process_transcript(self, transcript_path: str) -> Dict[str, Any]:
        """Process a transcript file and extract KYC information."""
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = f.read()
            
            # Simple extraction - combine all client responses
            client_text = ""
            lines = transcript.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('Client:'):
                    client_text += line[7:].strip() + " "
            
            # Extract information
            extracted_data = self.extract_from_text(client_text)
            
            # Calculate completion percentage
            total_fields = len(self.patterns)
            filled_fields = len([v for v in extracted_data.values() if v])
            completion_pct = (filled_fields / total_fields) * 100
            
            return {
                'extracted_data': extracted_data,
                'completion_percentage': completion_pct,
                'total_fields': total_fields,
                'filled_fields': filled_fields,
                'client_text': client_text.strip()
            }
            
        except FileNotFoundError:
            return {'error': f'File not found: {transcript_path}'}
        except Exception as e:
            return {'error': f'Error processing transcript: {e}'}


def demo_kyc_extraction():
    """Demonstrate KYC information extraction."""
    print("=== KYC PDF Filler Demo ===\n")
    
    extractor = SimpleKYCExtractor()
    
    # Test with the sample transcript
    transcript_path = 'examples/sample_transcript.txt'
    
    print(f"Processing transcript: {transcript_path}")
    results = extractor.process_transcript(transcript_path)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    print(f"\nExtraction Results:")
    print(f"Completion: {results['completion_percentage']:.1f}% ({results['filled_fields']}/{results['total_fields']} fields)")
    print(f"\nExtracted Information:")
    
    for field, value in results['extracted_data'].items():
        if value:
            print(f"  {field.replace('_', ' ').title()}: {value}")
    
    # Save results to JSON
    output_file = 'examples/demo_extracted_data.json'
    try:
        with open(output_file, 'w') as f:
            json.dump({
                'extraction_timestamp': datetime.now().isoformat(),
                'results': results
            }, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    except Exception as e:
        print(f"Could not save results: {e}")
    
    print(f"\nClient Text Processed:")
    print(f"  \"{results['client_text'][:200]}{'...' if len(results['client_text']) > 200 else ''}\"")


def demo_question_answer_extraction():
    """Demonstrate Q&A pair extraction."""
    print("\n" + "="*50)
    print("=== Question-Answer Pair Extraction Demo ===\n")
    
    transcript_path = 'examples/sample_transcript.txt'
    
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
        
        # Simple Q&A extraction
        qa_pairs = []
        lines = transcript.split('\n')
        current_question = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('Advisor:'):
                question = line[8:].strip()
                if '?' in question:
                    current_question = question
            elif line.startswith('Client:') and current_question:
                answer = line[7:].strip()
                qa_pairs.append({
                    'question': current_question,
                    'answer': answer
                })
                current_question = None
        
        print(f"Extracted {len(qa_pairs)} Q&A pairs:\n")
        
        for i, qa in enumerate(qa_pairs[:5], 1):  # Show first 5
            print(f"{i}. Q: {qa['question']}")
            print(f"   A: {qa['answer']}\n")
        
        if len(qa_pairs) > 5:
            print(f"... and {len(qa_pairs) - 5} more pairs")
            
    except Exception as e:
        print(f"Error: {e}")


def show_pdf_concept():
    """Show how PDF filling would work conceptually."""
    print("\n" + "="*50)
    print("=== PDF Form Filling Concept ===\n")
    
    print("In a real implementation, the tool would:")
    print("1. Analyze the PDF form to identify fillable fields")
    print("2. Map extracted KYC data to appropriate PDF fields")
    print("3. Fill the PDF form with the extracted data")
    print("4. Save the completed form")
    
    print("\nExample field mappings:")
    mappings = [
        ("extracted 'name'", "PDF field 'ClientName'"),
        ("extracted 'email'", "PDF field 'EmailAddress'"),
        ("extracted 'phone'", "PDF field 'PhoneNumber'"),
        ("extracted 'income'", "PDF field 'AnnualIncome'"),
        ("extracted 'risk_tolerance'", "PDF field 'RiskProfile'")
    ]
    
    for extracted, pdf_field in mappings:
        print(f"  {extracted:25} → {pdf_field}")
    
    print(f"\nThis demo shows the NLP extraction component.")
    print(f"For full PDF processing, install the complete package with:")
    print(f"  pip install -r requirements.txt")


if __name__ == '__main__':
    demo_kyc_extraction()
    demo_question_answer_extraction()
    show_pdf_concept()
    
    print(f"\n" + "="*60)
    print("Demo completed! This shows the core concept of extracting")
    print("structured KYC information from meeting transcripts.")
    print("The full implementation includes PDF form filling,")
    print("advanced NLP models, and a complete CLI interface.")