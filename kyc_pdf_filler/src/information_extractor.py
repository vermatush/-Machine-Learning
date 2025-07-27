"""
Information extraction module for extracting structured KYC data from processed transcripts.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
import json
from dataclasses import dataclass

import spacy
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import pandas as pd
from fuzzywuzzy import fuzz

from .models import (
    KYCData, PersonalInfo, Address, EmploymentInfo, InvestmentProfile,
    RiskTolerance, InvestmentObjective, EmploymentStatus, MaritalStatus,
    ExtractionResult, TranscriptSegment
)
from .transcript_processor import KYCQuestionMatcher

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPattern:
    """Pattern for extracting specific information from text."""
    field_name: str
    patterns: List[str]
    extractor_type: str  # "regex", "ner", "classification"
    post_process_func: Optional[str] = None


class InformationExtractor:
    """Extracts structured KYC information from transcript data."""
    
    def __init__(self, use_transformers: bool = True):
        """
        Initialize the information extractor.
        
        Args:
            use_transformers: Whether to use transformer models for NER
        """
        self.use_transformers = use_transformers
        self.nlp = None
        self.ner_pipeline = None
        self.question_matcher = KYCQuestionMatcher()
        
        self._load_models()
        self._setup_extraction_patterns()
        
    def _load_models(self):
        """Load NLP models."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Some features may be limited.")
            
        if self.use_transformers:
            try:
                # Use a pre-trained NER model
                self.ner_pipeline = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    tokenizer="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple"
                )
            except Exception as e:
                logger.warning(f"Could not load transformer model: {e}")
                self.ner_pipeline = None
    
    def _setup_extraction_patterns(self):
        """Setup extraction patterns for different KYC fields."""
        self.extraction_patterns = {
            # Personal Information Patterns
            "first_name": ExtractionPattern(
                "first_name",
                [r"(?:my|i'm|i am|name is|call me)\s+([A-Z][a-z]+)", r"first name.{0,10}([A-Z][a-z]+)"],
                "regex",
                "clean_name"
            ),
            "last_name": ExtractionPattern(
                "last_name", 
                [r"last name.{0,10}([A-Z][a-z]+)", r"([A-Z][a-z]+)(?:\s+is my last name)"],
                "regex",
                "clean_name"
            ),
            "phone_number": ExtractionPattern(
                "phone_number",
                [r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})", r"(\(\d{3}\)\s?\d{3}[-.\s]?\d{4})"],
                "regex",
                "format_phone"
            ),
            "email": ExtractionPattern(
                "email",
                [r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"],
                "regex",
                "clean_email"
            ),
            "date_of_birth": ExtractionPattern(
                "date_of_birth",
                [
                    r"(\d{1,2}/\d{1,2}/\d{4})",
                    r"(\d{1,2}-\d{1,2}-\d{4})",
                    r"(born.{0,20}\d{4})",
                    r"(\d{1,2}\s+(?:years|yrs)\s+old)"
                ],
                "regex",
                "parse_date"
            ),
            
            # Financial Information Patterns
            "annual_income": ExtractionPattern(
                "annual_income",
                [
                    r"(?:make|earn|income).{0,20}\$?([0-9,]+)",
                    r"\$([0-9,]+).{0,20}(?:year|annual)",
                    r"([0-9,]+).{0,10}(?:thousand|k|million|m).{0,10}(?:year|annual)"
                ],
                "regex",
                "parse_currency"
            ),
            "net_worth": ExtractionPattern(
                "net_worth",
                [
                    r"net worth.{0,20}\$?([0-9,]+)",
                    r"worth.{0,20}\$?([0-9,]+)",
                    r"assets.{0,20}\$?([0-9,]+)"
                ],
                "regex",
                "parse_currency"
            ),
        }
    
    def extract_personal_info(self, text: str, qa_pairs: List[Dict[str, str]]) -> PersonalInfo:
        """Extract personal information from text and Q&A pairs."""
        personal_info = PersonalInfo()
        
        # Extract using named entity recognition
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ == "PERSON" and not personal_info.first_name:
                    name_parts = ent.text.split()
                    if len(name_parts) >= 1:
                        personal_info.first_name = name_parts[0]
                    if len(name_parts) >= 2:
                        personal_info.last_name = name_parts[-1]
        
        # Extract using regex patterns
        for field_name, pattern in self.extraction_patterns.items():
            if hasattr(personal_info, field_name):
                value = self._extract_with_pattern(text, pattern)
                if value:
                    setattr(personal_info, field_name, value)
        
        # Extract from Q&A pairs using field matching
        field_matches = self.question_matcher.match_questions_to_kyc_fields(qa_pairs)
        
        # Extract specific fields from matched Q&A pairs
        personal_fields = [
            "personal_info.first_name", "personal_info.last_name", 
            "personal_info.email", "personal_info.phone_number",
            "personal_info.date_of_birth", "personal_info.marital_status"
        ]
        
        for field_path in personal_fields:
            if field_path in field_matches and field_matches[field_path]:
                field_name = field_path.split(".")[-1]
                answer = field_matches[field_path][0]["answer"]  # Take first match
                extracted_value = self._extract_field_from_answer(field_name, answer)
                if extracted_value and hasattr(personal_info, field_name):
                    setattr(personal_info, field_name, extracted_value)
        
        return personal_info
    
    def extract_address(self, text: str, qa_pairs: List[Dict[str, str]]) -> Address:
        """Extract address information."""
        address = Address()
        
        # Address patterns
        address_patterns = {
            "street_address": [
                r"(?:live at|address is|street).{0,20}(\d+\s+[A-Za-z\s]+(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court))",
                r"(\d+\s+[A-Za-z\s]+(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|ct|court))"
            ],
            "city": [r"(?:city|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"],
            "state": [r"([A-Z]{2})\s+\d{5}", r"state\s+(?:of\s+)?([A-Z][a-z]+)"],
            "zip_code": [r"(\d{5}(?:-\d{4})?)", r"zip.{0,10}(\d{5})"]
        }
        
        for field_name, patterns in address_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and hasattr(address, field_name):
                    setattr(address, field_name, match.group(1).strip())
                    break
        
        return address
    
    def extract_employment_info(self, text: str, qa_pairs: List[Dict[str, str]]) -> EmploymentInfo:
        """Extract employment and financial information."""
        employment_info = EmploymentInfo()
        
        # Employment status extraction
        employment_keywords = {
            EmploymentStatus.EMPLOYED: ["employed", "work at", "job", "working"],
            EmploymentStatus.SELF_EMPLOYED: ["self-employed", "own business", "freelance", "contractor"],
            EmploymentStatus.RETIRED: ["retired", "retirement"],
            EmploymentStatus.UNEMPLOYED: ["unemployed", "not working", "between jobs"],
            EmploymentStatus.STUDENT: ["student", "studying", "school"]
        }
        
        text_lower = text.lower()
        for status, keywords in employment_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                employment_info.employment_status = status
                break
        
        # Extract employer and job title
        employer_patterns = [
            r"work at\s+([A-Z][A-Za-z\s&]+)",
            r"employed by\s+([A-Z][A-Za-z\s&]+)",
            r"company.{0,20}([A-Z][A-Za-z\s&]+)"
        ]
        
        for pattern in employer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                employment_info.employer_name = match.group(1).strip()
                break
        
        # Extract financial information using patterns
        for field_name in ["annual_income", "net_worth"]:
            if field_name in self.extraction_patterns:
                value = self._extract_with_pattern(text, self.extraction_patterns[field_name])
                if value and hasattr(employment_info, field_name):
                    setattr(employment_info, field_name, value)
        
        return employment_info
    
    def extract_investment_profile(self, text: str, qa_pairs: List[Dict[str, str]]) -> InvestmentProfile:
        """Extract investment profile information."""
        investment_profile = InvestmentProfile()
        
        # Risk tolerance extraction
        risk_keywords = {
            RiskTolerance.CONSERVATIVE: ["conservative", "safe", "low risk", "cautious"],
            RiskTolerance.MODERATE: ["moderate", "balanced", "medium risk"],
            RiskTolerance.AGGRESSIVE: ["aggressive", "high risk", "growth"],
            RiskTolerance.VERY_AGGRESSIVE: ["very aggressive", "speculation", "maximum risk"]
        }
        
        text_lower = text.lower()
        for risk_level, keywords in risk_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                investment_profile.risk_tolerance = risk_level
                break
        
        # Investment objective extraction
        objective_keywords = {
            InvestmentObjective.GROWTH: ["growth", "appreciate", "increase"],
            InvestmentObjective.INCOME: ["income", "dividends", "yield"],
            InvestmentObjective.PRESERVATION: ["preserve", "protect", "capital preservation"],
            InvestmentObjective.SPECULATION: ["speculation", "speculate", "high returns"],
            InvestmentObjective.BALANCED: ["balanced", "combination", "mix"]
        }
        
        for objective, keywords in objective_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                investment_profile.investment_objective = objective
                break
        
        # Extract investment experience
        experience_patterns = [
            r"(\d+)\s+years?.{0,20}(?:experience|investing)",
            r"investing.{0,20}(\d+)\s+years?",
            r"been investing.{0,20}(\d+)"
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    years = int(match.group(1))
                    investment_profile.investment_experience_years = years
                    break
                except ValueError:
                    continue
        
        return investment_profile
    
    def _extract_with_pattern(self, text: str, pattern: ExtractionPattern) -> Optional[Any]:
        """Extract information using a specific pattern."""
        if pattern.extractor_type == "regex":
            for regex_pattern in pattern.patterns:
                match = re.search(regex_pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    if pattern.post_process_func:
                        value = self._post_process(value, pattern.post_process_func)
                    return value
        
        elif pattern.extractor_type == "ner" and self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in pattern.patterns:
                    return ent.text
        
        return None
    
    def _extract_field_from_answer(self, field_name: str, answer: str) -> Optional[Any]:
        """Extract specific field value from an answer."""
        if field_name == "marital_status":
            status_map = {
                "single": MaritalStatus.SINGLE,
                "married": MaritalStatus.MARRIED,
                "divorced": MaritalStatus.DIVORCED,
                "widowed": MaritalStatus.WIDOWED,
                "separated": MaritalStatus.SEPARATED
            }
            
            answer_lower = answer.lower()
            for status_key, status_value in status_map.items():
                if status_key in answer_lower:
                    return status_value
        
        elif field_name in self.extraction_patterns:
            return self._extract_with_pattern(answer, self.extraction_patterns[field_name])
        
        else:
            # Simple extraction for basic fields
            return answer.strip()
        
        return None
    
    def _post_process(self, value: str, func_name: str) -> Any:
        """Apply post-processing function to extracted value."""
        if func_name == "clean_name":
            return value.strip().title()
        
        elif func_name == "format_phone":
            # Remove all non-digits and format
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            return value
        
        elif func_name == "clean_email":
            return value.lower().strip()
        
        elif func_name == "parse_date":
            # Try to parse various date formats
            date_patterns = [
                r"(\d{1,2})/(\d{1,2})/(\d{4})",
                r"(\d{1,2})-(\d{1,2})-(\d{4})",
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, value)
                if match:
                    try:
                        month, day, year = map(int, match.groups())
                        return date(year, month, day)
                    except ValueError:
                        continue
            
            # Try to extract year from age
            age_match = re.search(r"(\d{1,2})\s+(?:years|yrs)\s+old", value)
            if age_match:
                age = int(age_match.group(1))
                birth_year = datetime.now().year - age
                return date(birth_year, 1, 1)  # Approximate
            
            return None
        
        elif func_name == "parse_currency":
            # Extract numeric value and convert to float
            # Handle k (thousands) and m (millions)
            value_clean = re.sub(r'[,$]', '', value)
            
            if 'k' in value_clean.lower():
                numeric = re.search(r'(\d+(?:\.\d+)?)', value_clean)
                if numeric:
                    return float(numeric.group(1)) * 1000
            
            elif 'm' in value_clean.lower():
                numeric = re.search(r'(\d+(?:\.\d+)?)', value_clean)
                if numeric:
                    return float(numeric.group(1)) * 1000000
            
            else:
                numeric = re.search(r'(\d+(?:\.\d+)?)', value_clean)
                if numeric:
                    return float(numeric.group(1))
            
            return None
        
        return value
    
    def extract_kyc_data(self, processed_transcript: Dict[str, Any]) -> ExtractionResult:
        """
        Extract complete KYC data from processed transcript.
        
        Args:
            processed_transcript: Output from TranscriptProcessor.process_transcript()
            
        Returns:
            ExtractionResult containing extracted KYC data
        """
        full_text = processed_transcript["cleaned_transcript"]
        qa_pairs = processed_transcript["qa_pairs"]
        client_statements = processed_transcript["client_statements"]
        
        # Combine all client text for comprehensive extraction
        client_text = " ".join(client_statements)
        
        # Extract each section
        personal_info = self.extract_personal_info(client_text, qa_pairs)
        address = self.extract_address(client_text, qa_pairs)
        employment_info = self.extract_employment_info(client_text, qa_pairs)
        investment_profile = self.extract_investment_profile(client_text, qa_pairs)
        
        # Create KYC data object
        kyc_data = KYCData(
            personal_info=personal_info,
            address=address,
            employment_info=employment_info,
            investment_profile=investment_profile
        )
        
        # Calculate confidence scores based on field completion
        confidence_scores = self._calculate_confidence_scores(kyc_data, qa_pairs)
        
        # Create processing notes
        processing_notes = []
        completion_percentage = kyc_data.get_completion_percentage()
        processing_notes.append(f"Form completion: {completion_percentage:.1f}%")
        
        if completion_percentage < 50:
            processing_notes.append("Low completion rate - consider asking for more information")
        
        return ExtractionResult(
            kyc_data=kyc_data,
            confidence_scores=confidence_scores,
            extracted_segments=processed_transcript["segments"],
            processing_notes=processing_notes
        )
    
    def _calculate_confidence_scores(self, kyc_data: KYCData, qa_pairs: List[Dict[str, str]]) -> Dict[str, float]:
        """Calculate confidence scores for extracted data."""
        scores = {}
        
        # Base confidence on whether we found matching Q&A pairs
        field_matches = self.question_matcher.match_questions_to_kyc_fields(qa_pairs)
        
        for field_path in field_matches:
            if field_matches[field_path]:
                scores[field_path] = 0.8  # High confidence if found in Q&A
            else:
                scores[field_path] = 0.3  # Lower confidence if extracted from general text
        
        return scores