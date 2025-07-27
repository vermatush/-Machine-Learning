"""
Tests for transcript processor module.
"""

import unittest
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.transcript_processor import TranscriptProcessor, KYCQuestionMatcher


class TestTranscriptProcessor(unittest.TestCase):
    """Test cases for TranscriptProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = TranscriptProcessor()
    
    def test_clean_transcript(self):
        """Test transcript cleaning functionality."""
        raw_transcript = """
        [00:12:34] Advisor: Um, what is your name?
        [inaudible] 
        Client: My name is, uh, John Smith.
        """
        
        cleaned = self.processor.clean_transcript(raw_transcript)
        
        # Should remove timestamps, filler words, and artifacts
        self.assertNotIn("[00:12:34]", cleaned)
        self.assertNotIn("[inaudible]", cleaned)
        self.assertNotIn("um", cleaned.lower())
        self.assertNotIn("uh", cleaned.lower())
    
    def test_identify_speaker(self):
        """Test speaker identification."""
        test_cases = [
            ("Advisor: What is your name?", ("advisor", "What is your name?")),
            ("Client: My name is John", ("client", "My name is John")),
            ("FA: How old are you?", ("advisor", "How old are you?")),
            ("Mr. Smith: I am 35", ("client", "I am 35")),
            ("Random text", ("unknown", "Random text"))
        ]
        
        for text, expected in test_cases:
            with self.subTest(text=text):
                result = self.processor.identify_speaker(text)
                self.assertEqual(result, expected)
    
    def test_is_question(self):
        """Test question identification."""
        questions = [
            "What is your name?",
            "How old are you?",
            "Can you tell me about your income?",
            "Are you married?"
        ]
        
        statements = [
            "My name is John.",
            "I am 35 years old.",
            "I work at a bank.",
            "I am married."
        ]
        
        for question in questions:
            with self.subTest(text=question):
                self.assertTrue(self.processor.is_question(question))
        
        for statement in statements:
            with self.subTest(text=statement):
                self.assertFalse(self.processor.is_question(statement))
    
    def test_segment_transcript(self):
        """Test transcript segmentation."""
        transcript = """Advisor: What is your name?
Client: My name is John Smith.
Advisor: How old are you?
Client: I am 35 years old."""
        
        segments = self.processor.segment_transcript(transcript)
        
        self.assertEqual(len(segments), 4)
        self.assertEqual(segments[0].speaker, "advisor")
        self.assertEqual(segments[0].segment_type, "question")
        self.assertEqual(segments[1].speaker, "client")
        self.assertEqual(segments[1].segment_type, "answer")
    
    def test_extract_qa_pairs(self):
        """Test Q&A pair extraction."""
        transcript = """Advisor: What is your name?
Client: My name is John Smith.
Advisor: How old are you?
Client: I am 35 years old."""
        
        segments = self.processor.segment_transcript(transcript)
        qa_pairs = self.processor.extract_qa_pairs(segments)
        
        self.assertEqual(len(qa_pairs), 2)
        self.assertEqual(qa_pairs[0]["question"], "What is your name?")
        self.assertEqual(qa_pairs[0]["answer"], "My name is John Smith.")


class TestKYCQuestionMatcher(unittest.TestCase):
    """Test cases for KYCQuestionMatcher class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.matcher = KYCQuestionMatcher()
    
    def test_match_questions_to_kyc_fields(self):
        """Test matching questions to KYC fields."""
        qa_pairs = [
            {"question": "What is your first name?", "answer": "John"},
            {"question": "What is your email address?", "answer": "john@email.com"},
            {"question": "What is your annual income?", "answer": "$50,000"},
            {"question": "What is your favorite color?", "answer": "Blue"}  # Should not match
        ]
        
        matches = self.matcher.match_questions_to_kyc_fields(qa_pairs)
        
        # Should match first name, email, and income questions
        self.assertIn("personal_info.first_name", matches)
        self.assertIn("personal_info.email", matches)
        self.assertIn("employment_info.annual_income", matches)
        
        # Check that matches contain the correct Q&A pairs
        self.assertEqual(len(matches["personal_info.first_name"]), 1)
        self.assertEqual(matches["personal_info.first_name"][0]["answer"], "John")


if __name__ == '__main__':
    unittest.main()