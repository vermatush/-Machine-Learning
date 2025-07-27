"""
Data models for KYC information extraction and PDF form filling.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class RiskTolerance(str, Enum):
    """Risk tolerance levels for investment purposes."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


class InvestmentObjective(str, Enum):
    """Investment objectives."""
    GROWTH = "growth"
    INCOME = "income"
    PRESERVATION = "preservation"
    SPECULATION = "speculation"
    BALANCED = "balanced"


class EmploymentStatus(str, Enum):
    """Employment status options."""
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"
    STUDENT = "student"


class MaritalStatus(str, Enum):
    """Marital status options."""
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    SEPARATED = "separated"


class PersonalInfo(BaseModel):
    """Personal information section of KYC."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    social_security_number: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    number_of_dependents: Optional[int] = None
    
    @validator('social_security_number')
    def validate_ssn(cls, v):
        if v and len(v.replace('-', '').replace(' ', '')) != 9:
            raise ValueError('SSN must be 9 digits')
        return v


class Address(BaseModel):
    """Address information."""
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = "USA"
    is_mailing_address: bool = True
    
    @validator('zip_code')
    def validate_zip(cls, v):
        if v and not (len(v) == 5 or len(v) == 10):
            raise ValueError('ZIP code must be 5 or 10 characters')
        return v


class EmploymentInfo(BaseModel):
    """Employment and financial information."""
    employment_status: Optional[EmploymentStatus] = None
    employer_name: Optional[str] = None
    job_title: Optional[str] = None
    years_employed: Optional[int] = None
    annual_income: Optional[float] = None
    net_worth: Optional[float] = None
    liquid_net_worth: Optional[float] = None
    
    @validator('annual_income', 'net_worth', 'liquid_net_worth')
    def validate_positive_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Financial amounts must be positive')
        return v


class InvestmentProfile(BaseModel):
    """Investment profile and experience."""
    investment_objective: Optional[InvestmentObjective] = None
    risk_tolerance: Optional[RiskTolerance] = None
    investment_experience_years: Optional[int] = None
    investment_knowledge_level: Optional[str] = None  # beginner, intermediate, advanced
    previous_investment_types: Optional[List[str]] = []
    time_horizon: Optional[str] = None  # short, medium, long term
    liquidity_needs: Optional[str] = None
    
    @validator('investment_experience_years')
    def validate_experience(cls, v):
        if v is not None and (v < 0 or v > 80):
            raise ValueError('Investment experience must be between 0 and 80 years')
        return v


class KYCData(BaseModel):
    """Complete KYC data structure."""
    personal_info: PersonalInfo = PersonalInfo()
    address: Address = Address()
    employment_info: EmploymentInfo = EmploymentInfo()
    investment_profile: InvestmentProfile = InvestmentProfile()
    additional_notes: Optional[str] = None
    form_completion_date: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for PDF form filling."""
        return self.dict(exclude_none=True)
    
    def get_completion_percentage(self) -> float:
        """Calculate how much of the form is completed."""
        total_fields = 0
        completed_fields = 0
        
        for field_name, field_value in self.dict().items():
            if isinstance(field_value, dict):
                for subfield_name, subfield_value in field_value.items():
                    total_fields += 1
                    if subfield_value is not None:
                        completed_fields += 1
            else:
                total_fields += 1
                if field_value is not None:
                    completed_fields += 1
        
        return (completed_fields / total_fields) * 100 if total_fields > 0 else 0.0


class TranscriptSegment(BaseModel):
    """Represents a segment of the transcript (Q&A pair or statement)."""
    speaker: str  # "advisor" or "client"
    content: str
    timestamp: Optional[str] = None
    segment_type: Literal["question", "answer", "statement"] = "statement"
    
    
class ExtractionResult(BaseModel):
    """Result of information extraction from transcript."""
    kyc_data: KYCData
    confidence_scores: Dict[str, float] = {}
    extracted_segments: List[TranscriptSegment] = []
    processing_notes: List[str] = []
    
    
class PDFFieldMapping(BaseModel):
    """Mapping between KYC data fields and PDF form fields."""
    kyc_field_path: str  # e.g., "personal_info.first_name"
    pdf_field_name: str  # e.g., "FirstName"
    field_type: Literal["text", "checkbox", "radio", "dropdown"] = "text"
    transformation: Optional[str] = None  # Optional transformation function name
    
    
class PDFFormTemplate(BaseModel):
    """PDF form template configuration."""
    template_name: str
    template_path: str
    field_mappings: List[PDFFieldMapping]
    creation_date: datetime = Field(default_factory=datetime.now)
    
    def get_mapping_by_kyc_field(self, kyc_field: str) -> Optional[PDFFieldMapping]:
        """Get PDF field mapping for a KYC field."""
        for mapping in self.field_mappings:
            if mapping.kyc_field_path == kyc_field:
                return mapping
        return None