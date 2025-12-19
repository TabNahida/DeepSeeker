"""
HTML Text Extractor
Extracts key text content from HTML, removing tags, scripts, styles, and other noise.
"""
from __future__ import annotations

import re
from html import unescape
from typing import Optional

from .text_extraction_config import (
    REMOVAL_PATTERNS,
    IMPORTANT_TAGS,
    CONTENT_TAGS,
    MIN_RELEVANT_LENGTH
)


class TextExtractor:
    """Tool class for extracting clean text from HTML content"""
    
    def __init__(self, max_length: int = 8000):
        self.max_length = max_length
    
    def extract(self, html: str) -> str:
        """
        Extract key text content from HTML
        
        Args:
            html: HTML content string
            
        Returns:
            Cleaned text content
        """
        if not html:
            return ""
        
        # 1. Remove script and style tags with their content
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # 2. Remove all tags but keep text between them
        html = re.sub(r'<[^>]+>', ' ', html)
        
        # 3. Handle HTML entities
        html = unescape(html)
        
        # 4. Clean whitespace
        html = re.sub(r'\s+', ' ', html)
        html = html.strip()
        
        # 5. Remove common noise patterns using config
        for pattern in REMOVAL_PATTERNS:
            html = re.sub(pattern, '', html, flags=re.IGNORECASE)
        
        # 6. Clean up whitespace again
        html = re.sub(r'\s+', ' ', html)
        html = html.strip()
        
        # 7. Remove duplicate sentences/words
        html = self._remove_duplicates(html)
        
        # 8. Truncate if needed
        if len(html) > self.max_length:
            truncate_point = self._find_sentence_boundary(html, self.max_length)
            html = html[:truncate_point].strip()
        
        return html
    
    def _remove_duplicates(self, text: str) -> str:
        """
        Remove duplicate sentences and repeated content
        
        Args:
            text: Text to clean
            
        Returns:
            Text with duplicates removed
        """
        # Split into sentences using multiple delimiters
        sentence_delimiters = r'[。！？.!?]+'
        sentences = [s.strip() for s in re.split(sentence_delimiters, text) if s.strip()]
        
        if not sentences:
            return text
        
        # Remove duplicates while preserving order
        seen = set()
        unique_sentences = []
        
        for sentence in sentences:
            # Normalize for comparison: lowercase, remove extra spaces
            normalized = re.sub(r'\s+', ' ', sentence.lower()).strip()
            
            # Also check for near-duplicates (very similar sentences)
            is_duplicate = False
            for existing in seen:
                # If sentences share 80%+ of words, consider them duplicates
                existing_words = set(existing.split())
                current_words = set(normalized.split())
                if len(existing_words) > 0 and len(current_words) > 0:
                    intersection = existing_words.intersection(current_words)
                    union = existing_words.union(current_words)
                    similarity = len(intersection) / len(union)
                    if similarity > 0.8:
                        is_duplicate = True
                        break
            
            if not is_duplicate and normalized:
                seen.add(normalized)
                unique_sentences.append(sentence)
        
        # Reconstruct text with proper punctuation
        result = '. '.join(unique_sentences)
        if result and not result.endswith(('.', '。', '!', '！', '?', '？')):
            result += '.'
        
        return result
    
    def _find_sentence_boundary(self, text: str, max_len: int) -> int:
        """
        Find sentence boundary within specified length
        
        Args:
            text: Text content
            max_len: Maximum length
            
        Returns:
            Truncation position
        """
        # First try to truncate after punctuation marks
        for punct in ['。', '.', '！', '!', '？', '?']:
            last_punct = text.rfind(punct, 0, max_len)
            if last_punct != -1 and last_punct > max_len - 100:
                return last_punct + 1
        
        # If no punctuation found, try to truncate at space
        last_space = text.rfind(' ', 0, max_len)
        if last_space != -1:
            return last_space
        
        # Fallback to direct truncation
        return max_len
    
    def extract_with_importance(
        self, 
        html: str, 
        important_tags: Optional[list[str]] = None
    ) -> str:
        """
        Extract text while prioritizing important tag content
        
        Args:
            html: HTML content
            important_tags: List of important HTML tags (uses config if None)
            
        Returns:
            Extracted text
        """
        if not html:
            return ""
        
        if important_tags is None:
            important_tags = IMPORTANT_TAGS
        
        # First extract content from important tags
        important_content = []
        
        for tag in important_tags:
            # Match tags and their content
            pattern = f'<{tag}[^>]*>(.*?)</{tag}>'
            matches = re.findall(pattern, html, flags=re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Clean content
                cleaned = re.sub(r'<[^>]+>', ' ', match)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    important_content.append(cleaned)
        
        # If important content found, return it
        if important_content:
            result = ' '.join(important_content)
            # Apply cleaning rules
            result = self._clean_text(result)
            
            # Check minimum relevance length
            if len(result) < MIN_RELEVANT_LENGTH:
                # Fall back to full extraction if too short
                return self.extract(html)
            
            if len(result) <= self.max_length:
                return result
            else:
                # Truncate if needed
                truncate_point = self._find_sentence_boundary(result, self.max_length)
                return result[:truncate_point].strip()
        
        # Fallback to full extraction
        return self.extract(html)
    
    def _clean_text(self, text: str) -> str:
        """Clean text of extra whitespace and noise patterns"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove noise patterns using config
        for pattern in REMOVAL_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        # Clean whitespace again
        text = re.sub(r'\s+', ' ', text).strip()
        return text


def extract_text_from_html(html: str, max_chars: int = 8000, use_importance: bool = True) -> str:
    """
    Convenience function: extract text from HTML
    
    Args:
        html: HTML content
        max_chars: Maximum characters
        use_importance: Whether to use importance-based extraction
        
    Returns:
        Extracted text
    """
    extractor = TextExtractor(max_length=max_chars)
    if use_importance:
        return extractor.extract_with_importance(html)
    else:
        return extractor.extract(html)