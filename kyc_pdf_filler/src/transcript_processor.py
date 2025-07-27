"""
Transcript processing module for cleaning and segmenting meeting transcripts.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import spacy
from .models import TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass
class SpeakerPattern:
    """Pattern for identifying speakers in transcripts."""
    pattern: str
    speaker_type: str  # "advisor" or "client"
    

class TranscriptProcessor:
    """Processes meeting transcripts for KYC information extraction."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        self.nlp = None
        self._load_nlp_model()
        
        # Common speaker identification patterns
        self.speaker_patterns = [
            SpeakerPattern(r"^(Advisor|FA|Financial Advisor)[:]\s*", "advisor"),
            SpeakerPattern(r"^(Client|Customer|Mr\.|Mrs\.|Ms\.)[:]\s*", "client"),
            SpeakerPattern(r"^([A-Z][a-z]+)[:]\s*", "unknown"),  # Generic name pattern
        ]
        
        # Question indicators for advisors
        self.question_indicators = [
            r"\?",
            r"^(What|How|When|Where|Why|Who|Which|Can you|Could you|Would you|Do you|Are you|Have you)",
            r"(tell me|explain|describe|share)",
        ]
        
    def _load_nlp_model(self):
        """Load spaCy NLP model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Some features may be limited.")
            self.nlp = None
    
    def clean_transcript(self, raw_transcript: str) -> str:
        """Clean raw transcript text."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', raw_transcript)
        
        # Remove common transcript artifacts
        cleaned = re.sub(r'\[inaudible\]|\[unclear\]|\[crosstalk\]', '', cleaned, flags=re.IGNORECASE)
        
        # Remove timestamps if present (e.g., [00:12:34])
        cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)
        
        # Remove filler words patterns
        filler_patterns = [
            r'\b(um|uh|ah|er|hmm)\b',
            r'\b(you know|like|basically|actually)\b',
        ]
        for pattern in filler_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def identify_speaker(self, text: str) -> Tuple[str, str]:
        """
        Identify speaker and extract content from a line of transcript.
        
        Returns:
            Tuple of (speaker_type, content)
        """
        for pattern in self.speaker_patterns:
            match = re.match(pattern.pattern, text, re.IGNORECASE)
            if match:
                # Extract content after speaker identifier
                content = re.sub(pattern.pattern, '', text, flags=re.IGNORECASE).strip()
                return pattern.speaker_type, content
        
        # If no speaker pattern found, return as unknown
        return "unknown", text.strip()
    
    def is_question(self, text: str) -> bool:
        """Determine if text contains a question."""
        for indicator in self.question_indicators:
            if re.search(indicator, text, re.IGNORECASE):
                return True
        return False
    
    def segment_transcript(self, transcript: str) -> List[TranscriptSegment]:
        """
        Segment transcript into structured segments.
        
        Args:
            transcript: Cleaned transcript text
            
        Returns:
            List of TranscriptSegment objects
        """
        segments = []
        lines = transcript.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            speaker_type, content = self.identify_speaker(line)
            
            # Determine segment type
            if speaker_type == "advisor" and self.is_question(content):
                segment_type = "question"
            elif speaker_type == "client":
                segment_type = "answer"
            else:
                segment_type = "statement"
            
            segment = TranscriptSegment(
                speaker=speaker_type,
                content=content,
                segment_type=segment_type
            )
            segments.append(segment)
        
        return segments
    
    def extract_qa_pairs(self, segments: List[TranscriptSegment]) -> List[Dict[str, str]]:
        """
        Extract question-answer pairs from segments.
        
        Returns:
            List of dictionaries with 'question' and 'answer' keys
        """
        qa_pairs = []
        current_question = None
        
        for segment in segments:
            if segment.segment_type == "question":
                current_question = segment.content
            elif segment.segment_type == "answer" and current_question:
                qa_pairs.append({
                    "question": current_question,
                    "answer": segment.content
                })
                current_question = None
        
        return qa_pairs
    
    def extract_client_statements(self, segments: List[TranscriptSegment]) -> List[str]:
        """Extract all statements made by the client."""
        return [
            segment.content 
            for segment in segments 
            if segment.speaker == "client"
        ]
    
    def get_conversation_flow(self, segments: List[TranscriptSegment]) -> List[Dict[str, str]]:
        """
        Get the conversation flow with speaker turns.
        
        Returns:
            List of conversation turns with speaker and content
        """
        flow = []
        for segment in segments:
            flow.append({
                "speaker": segment.speaker,
                "content": segment.content,
                "type": segment.segment_type
            })
        return flow
    
    def extract_key_topics(self, transcript: str) -> List[str]:
        """
        Extract key topics from transcript using NLP.
        
        Args:
            transcript: Full transcript text
            
        Returns:
            List of key topics/entities
        """
        if not self.nlp:
            return []
        
        doc = self.nlp(transcript)
        
        # Extract named entities and key noun phrases
        topics = set()
        
        # Add named entities
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "MONEY", "DATE", "GPE"]:
                topics.add(ent.text)
        
        # Add key noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:  # Multi-word phrases
                topics.add(chunk.text)
        
        return list(topics)
    
    def process_transcript(self, raw_transcript: str) -> Dict[str, any]:
        """
        Complete transcript processing pipeline.
        
        Args:
            raw_transcript: Raw transcript text
            
        Returns:
            Dictionary containing processed transcript data
        """
        # Clean transcript
        cleaned_transcript = self.clean_transcript(raw_transcript)
        
        # Segment transcript
        segments = self.segment_transcript(cleaned_transcript)
        
        # Extract Q&A pairs
        qa_pairs = self.extract_qa_pairs(segments)
        
        # Extract client statements
        client_statements = self.extract_client_statements(segments)
        
        # Extract key topics
        key_topics = self.extract_key_topics(cleaned_transcript)
        
        # Get conversation flow
        conversation_flow = self.get_conversation_flow(segments)
        
        return {
            "cleaned_transcript": cleaned_transcript,
            "segments": segments,
            "qa_pairs": qa_pairs,
            "client_statements": client_statements,
            "key_topics": key_topics,
            "conversation_flow": conversation_flow,
            "total_segments": len(segments),
            "total_qa_pairs": len(qa_pairs)
        }


class KYCQuestionMatcher:
    """Matches transcript content to known KYC questions."""
    
    def __init__(self):
        """Initialize with predefined KYC question patterns."""
        self.kyc_question_patterns = {
            # Personal Information
            "personal_info.first_name": [
                r"(what is|what's|can you tell me) your first name",
                r"your first name (is|please)",
                r"name.*first"
            ],
            "personal_info.last_name": [
                r"(what is|what's) your last name",
                r"surname|family name",
                r"last name"
            ],
            "personal_info.date_of_birth": [
                r"date of birth|birth date|when were you born",
                r"what is your birthday",
                r"age|how old"
            ],
            "personal_info.phone_number": [
                r"phone number|contact number|telephone",
                r"how can we reach you",
                r"best number to call"
            ],
            "personal_info.email": [
                r"email address|e-mail",
                r"electronic mail",
                r"email"
            ],
            "personal_info.marital_status": [
                r"marital status|married|single",
                r"spouse|partner|wife|husband",
                r"relationship status"
            ],
            
            # Employment Information
            "employment_info.employment_status": [
                r"employment status|work|job",
                r"are you employed|working",
                r"occupation|profession"
            ],
            "employment_info.annual_income": [
                r"annual income|yearly income|salary",
                r"how much do you make|earn",
                r"income|earnings"
            ],
            "employment_info.net_worth": [
                r"net worth|total assets",
                r"financial worth|wealth",
                r"assets.*liabilities"
            ],
            
            # Investment Information
            "investment_profile.risk_tolerance": [
                r"risk tolerance|comfort with risk",
                r"conservative|aggressive|moderate",
                r"risk appetite"
            ],
            "investment_profile.investment_objective": [
                r"investment (goal|objective|purpose)",
                r"what are you looking to achieve",
                r"financial goals"
            ],
            "investment_profile.investment_experience": [
                r"investment experience|investing experience",
                r"how long have you been investing",
                r"previous investments"
            ]
        }
    
    def match_questions_to_kyc_fields(self, qa_pairs: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Match questions to KYC fields based on content.
        
        Returns:
            Dictionary mapping KYC fields to relevant Q&A pairs
        """
        field_matches = {}
        
        for kyc_field, patterns in self.kyc_question_patterns.items():
            field_matches[kyc_field] = []
            
            for qa_pair in qa_pairs:
                question = qa_pair["question"].lower()
                
                for pattern in patterns:
                    if re.search(pattern, question, re.IGNORECASE):
                        field_matches[kyc_field].append(qa_pair)
                        break  # Avoid duplicate matches for same Q&A pair
        
        return field_matches