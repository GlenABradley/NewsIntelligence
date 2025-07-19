"""
News Intelligence Platform - Enhanced Dual Pipeline for News Analysis
Adapted from Truth Detector dual pipeline system for news-specific requirements
"""
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

# Import sentiment analysis libraries
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import re

from models.news_models import NewsArticle, StoryCluster, FactualClaim, EmotionalClaim, NewsAnalysis

logger = logging.getLogger(__name__)

class NewsIntelligencePipeline:
    """
    Enhanced dual pipeline specifically designed for news analysis
    Separates factual reporting from emotional/editorial content across multiple sources
    """
    
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.factual_threshold = 0.3  # Sentiment neutrality threshold
        self.emotion_categories = [
            "fear", "anger", "joy", "sadness", "confusion", 
            "excitement", "disgust", "admiration", "concern", "optimism"
        ]
        
    async def analyze_story_cluster(self, cluster: StoryCluster) -> NewsAnalysis:
        """
        Complete dual pipeline analysis of a news story cluster
        
        Args:
            cluster: Story cluster containing multiple articles about same event
            
        Returns:
            NewsAnalysis with factual consensus and emotional spectrum
        """
        logger.info(f"Analyzing story cluster: {cluster.cluster_id} with {len(cluster.articles)} articles")
        
        start_time = datetime.utcnow()
        
        # Step 1: Extract and separate claims from all articles
        all_factual_claims = []
        all_emotional_claims = []
        
        for article in cluster.articles:
            factual, emotional = await self._process_single_article(article)
            all_factual_claims.extend(factual)
            all_emotional_claims.extend(emotional)
        
        # Step 2: Build factual consensus across sources
        consensus_facts = await self._build_factual_consensus(all_factual_claims)
        
        # Step 3: Map emotional spectrum across perspectives
        emotional_spectrum = await self._map_emotional_spectrum(all_emotional_claims, cluster.articles)
        
        # Step 4: Generate Fair Witness synthesis for news
        objective_summary, emotional_overlay = await self._generate_news_synthesis(
            consensus_facts, emotional_spectrum, cluster
        )
        
        # Step 5: Calculate analysis metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        analysis = NewsAnalysis(
            cluster_id=cluster.cluster_id,
            factual_claims=consensus_facts,
            emotional_claims=emotional_spectrum,
            total_sources=len(cluster.articles),
            factual_consensus_score=self._calculate_consensus_score(consensus_facts),
            emotional_spectrum_coverage=self._calculate_emotional_coverage(emotional_spectrum),
            perspective_breakdown=self._analyze_perspective_breakdown(cluster.articles),
            objective_summary=objective_summary,
            emotional_overlay=emotional_overlay,
            source_reliability_notes=self._generate_reliability_notes(cluster.articles),
            processing_time_seconds=processing_time,
            processing_metadata=self._generate_processing_metadata(cluster, all_factual_claims, all_emotional_claims)
        )
        
        logger.info(f"Analysis complete: {len(consensus_facts)} factual claims, {len(emotional_spectrum)} emotional claims")
        return analysis
    
    async def _process_single_article(self, article: NewsArticle) -> Tuple[List[FactualClaim], List[EmotionalClaim]]:
        """Process a single article through dual pipeline"""
        
        # Split content into sentences for analysis
        sentences = self._split_into_sentences(article.content)
        
        factual_claims = []
        emotional_claims = []
        
        for sentence in sentences:
            if len(sentence.strip()) < 10:  # Skip very short sentences
                continue
                
            # Analyze sentiment to determine pipeline routing
            sentiment_scores = self._analyze_sentiment(sentence)
            
            if self._is_factual_content(sentiment_scores, sentence):
                factual_claim = await self._process_factual_claim(sentence, article, sentiment_scores)
                if factual_claim:
                    factual_claims.append(factual_claim)
            else:
                emotional_claim = await self._process_emotional_claim(sentence, article, sentiment_scores)
                if emotional_claim:
                    emotional_claims.append(emotional_claim)
        
        return factual_claims, emotional_claims
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """Split content into sentences for analysis"""
        # Simple sentence splitting - can be enhanced with spaCy
        sentences = re.split(r'[.!?]+', content)
        return [s.strip() for s in sentences if s.strip()]
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using multiple methods"""
        # VADER sentiment
        vader_scores = self.vader_analyzer.polarity_scores(text)
        
        # TextBlob sentiment
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity
        
        return {
            "vader_compound": vader_scores["compound"],
            "vader_pos": vader_scores["pos"],
            "vader_neu": vader_scores["neu"],
            "vader_neg": vader_scores["neg"],
            "textblob_polarity": textblob_polarity,
            "textblob_subjectivity": textblob_subjectivity
        }
    
    def _is_factual_content(self, sentiment_scores: Dict[str, float], sentence: str) -> bool:
        """Determine if content should go through factual pipeline"""
        
        # High neutrality and low subjectivity suggest factual content
        is_neutral = abs(sentiment_scores["vader_compound"]) < self.factual_threshold
        is_objective = sentiment_scores["textblob_subjectivity"] < 0.5
        
        # Look for factual indicators
        factual_indicators = [
            "according to", "reported", "announced", "confirmed", "stated",
            "data shows", "statistics", "official", "spokesperson", "study found"
        ]
        
        has_factual_indicators = any(indicator in sentence.lower() for indicator in factual_indicators)
        
        # Look for emotional indicators
        emotional_indicators = [
            "outraged", "delighted", "shocking", "devastating", "amazing",
            "terrible", "wonderful", "appalling", "fantastic", "horrific"
        ]
        
        has_emotional_indicators = any(indicator in sentence.lower() for indicator in emotional_indicators)
        
        # Decide pipeline
        if has_emotional_indicators:
            return False
        elif has_factual_indicators or (is_neutral and is_objective):
            return True
        else:
            return is_neutral and is_objective
    
    async def _process_factual_claim(self, sentence: str, article: NewsArticle, sentiment_scores: Dict) -> Optional[FactualClaim]:
        """Process sentence through factual pipeline"""
        
        # Extract entities and verify factual nature
        if not self._contains_factual_content(sentence):
            return None
            
        claim = FactualClaim(
            claim_text=sentence.strip(),
            confidence_score=self._calculate_factual_confidence(sentence, sentiment_scores),
            supporting_sources=[article.source],
            contradiction_sources=[],
            consensus_level=1.0,  # Will be updated in consensus building
            entity_mentions=self._extract_entities(sentence)
        )
        
        return claim
    
    async def _process_emotional_claim(self, sentence: str, article: NewsArticle, sentiment_scores: Dict) -> Optional[EmotionalClaim]:
        """Process sentence through emotional pipeline"""
        
        emotion_type = self._classify_emotion(sentence, sentiment_scores)
        intensity = self._calculate_emotional_intensity(sentiment_scores)
        
        if intensity < 0.3:  # Skip low-intensity emotional content
            return None
            
        claim = EmotionalClaim(
            claim_text=sentence.strip(),
            emotion_type=emotion_type,
            intensity=intensity * 10,  # Scale to 0-10
            perspective=article.source_perspective,
            source=article.source
        )
        
        return claim
    
    def _contains_factual_content(self, sentence: str) -> bool:
        """Check if sentence contains factual information"""
        factual_patterns = [
            r'\d+(?:\.\d+)?%',  # Percentages
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Dollar amounts
            r'\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?',  # Times
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # Dates
            r'\d+(?:,\d{3})*\s+(?:people|deaths|cases|votes)',  # Numbers with units
        ]
        
        for pattern in factual_patterns:
            if re.search(pattern, sentence):
                return True
                
        return len(sentence.split()) > 5  # Minimum length for factual claims
    
    def _calculate_factual_confidence(self, sentence: str, sentiment_scores: Dict) -> float:
        """Calculate confidence that this is a factual claim"""
        confidence = 0.5
        
        # Higher confidence for neutral sentiment
        confidence += (1.0 - abs(sentiment_scores["vader_compound"])) * 0.3
        
        # Higher confidence for objective language
        confidence += (1.0 - sentiment_scores["textblob_subjectivity"]) * 0.2
        
        # Higher confidence for specific factual markers
        if any(marker in sentence.lower() for marker in ["according to", "reported", "data"]):
            confidence += 0.2
            
        return min(confidence, 1.0)
    
    def _extract_entities(self, sentence: str) -> List[str]:
        """Simple entity extraction - can be enhanced with spaCy"""
        # Basic entity patterns
        entities = []
        
        # Find capitalized words (potential proper nouns)
        words = sentence.split()
        for word in words:
            if word[0].isupper() and len(word) > 2 and word.isalpha():
                entities.append(word)
        
        return entities[:5]  # Limit to top 5
    
    def _classify_emotion(self, sentence: str, sentiment_scores: Dict) -> str:
        """Classify the primary emotion in the sentence"""
        
        # Simple emotion classification based on keywords and sentiment
        emotion_keywords = {
            "fear": ["afraid", "scared", "terrified", "worried", "concerned", "anxious"],
            "anger": ["angry", "furious", "outraged", "mad", "irritated", "annoyed"],
            "joy": ["happy", "delighted", "pleased", "excited", "thrilled", "elated"],
            "sadness": ["sad", "disappointed", "depressed", "grief", "sorrow", "tragic"],
            "confusion": ["confused", "uncertain", "unclear", "puzzled", "bewildered"],
            "excitement": ["exciting", "thrilling", "amazing", "incredible", "fantastic"],
            "disgust": ["disgusting", "revolting", "appalling", "horrible", "awful"],
            "admiration": ["admirable", "impressive", "remarkable", "outstanding", "excellent"],
            "concern": ["concerning", "troubling", "worrying", "alarming", "disturbing"],
            "optimism": ["hopeful", "optimistic", "promising", "positive", "encouraging"]
        }
        
        sentence_lower = sentence.lower()
        
        # Check for emotion keywords
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in sentence_lower for keyword in keywords):
                return emotion
        
        # Fallback to sentiment polarity
        compound = sentiment_scores["vader_compound"]
        if compound > 0.5:
            return "joy"
        elif compound < -0.5:
            return "anger" if sentiment_scores["vader_neg"] > 0.3 else "sadness"
        else:
            return "concern"
    
    def _calculate_emotional_intensity(self, sentiment_scores: Dict) -> float:
        """Calculate emotional intensity from sentiment scores"""
        # Use compound score magnitude and subjectivity
        intensity = abs(sentiment_scores["vader_compound"]) * sentiment_scores["textblob_subjectivity"]
        return min(intensity, 1.0)
    
    async def _build_factual_consensus(self, factual_claims: List[FactualClaim]) -> List[FactualClaim]:
        """Build consensus on factual claims across multiple sources"""
        
        if not factual_claims:
            return []
        
        # Group similar claims
        claim_groups = self._group_similar_claims(factual_claims)
        
        consensus_claims = []
        for group in claim_groups:
            if len(group) >= 2:  # Require at least 2 sources for consensus
                consensus_claim = self._merge_consensus_claims(group)
                consensus_claims.append(consensus_claim)
        
        return consensus_claims
    
    def _group_similar_claims(self, claims: List[FactualClaim]) -> List[List[FactualClaim]]:
        """Group similar factual claims together"""
        groups = []
        used_claims = set()
        
        for i, claim in enumerate(claims):
            if i in used_claims:
                continue
                
            group = [claim]
            used_claims.add(i)
            
            for j, other_claim in enumerate(claims[i+1:], i+1):
                if j in used_claims:
                    continue
                    
                if self._claims_are_similar(claim, other_claim):
                    group.append(other_claim)
                    used_claims.add(j)
            
            groups.append(group)
        
        return groups
    
    def _claims_are_similar(self, claim1: FactualClaim, claim2: FactualClaim) -> bool:
        """Check if two factual claims are about the same fact"""
        # Simple similarity check - can be enhanced with your semantic algorithms
        words1 = set(claim1.claim_text.lower().split())
        words2 = set(claim2.claim_text.lower().split())
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return False
            
        overlap = len(words1.intersection(words2))
        similarity = overlap / min(len(words1), len(words2))
        
        return similarity > 0.6
    
    def _merge_consensus_claims(self, claim_group: List[FactualClaim]) -> FactualClaim:
        """Merge multiple claims into a consensus claim"""
        
        # Use the claim with highest confidence as base
        base_claim = max(claim_group, key=lambda c: c.confidence_score)
        
        # Collect all supporting sources
        all_sources = []
        for claim in claim_group:
            all_sources.extend(claim.supporting_sources)
        
        # Calculate consensus level
        consensus_level = len(set(all_sources)) / max(len(all_sources), 1)
        
        merged_claim = FactualClaim(
            claim_text=base_claim.claim_text,
            confidence_score=sum(c.confidence_score for c in claim_group) / len(claim_group),
            supporting_sources=list(set(all_sources)),
            contradiction_sources=[],
            consensus_level=consensus_level,
            entity_mentions=list(set(sum([c.entity_mentions for c in claim_group], [])))
        )
        
        return merged_claim
    
    async def _map_emotional_spectrum(self, emotional_claims: List[EmotionalClaim], articles: List[NewsArticle]) -> List[EmotionalClaim]:
        """Map emotional claims across different source perspectives"""
        
        # Group emotional claims by perspective
        perspective_emotions = {}
        for claim in emotional_claims:
            perspective = claim.perspective
            if perspective not in perspective_emotions:
                perspective_emotions[perspective] = []
            perspective_emotions[perspective].append(claim)
        
        # Return top emotional claims from each perspective
        balanced_claims = []
        for perspective, claims in perspective_emotions.items():
            # Sort by intensity and take top claims
            sorted_claims = sorted(claims, key=lambda c: c.intensity, reverse=True)
            balanced_claims.extend(sorted_claims[:5])  # Top 5 per perspective
        
        return balanced_claims
    
    async def _generate_news_synthesis(self, factual_claims: List[FactualClaim], 
                                     emotional_claims: List[EmotionalClaim], 
                                     cluster: StoryCluster) -> Tuple[str, Dict]:
        """Generate Fair Witness synthesis for news story"""
        
        # Build objective summary from factual consensus
        objective_parts = []
        objective_parts.append(f"**{cluster.main_event}**\n")
        
        if factual_claims:
            objective_parts.append("**Verified Facts:**")
            for claim in sorted(factual_claims, key=lambda c: c.consensus_level, reverse=True)[:10]:
                sources_count = len(claim.supporting_sources)
                consensus_text = f"({sources_count} sources, {claim.consensus_level:.1%} consensus)"
                objective_parts.append(f"• {claim.claim_text} {consensus_text}")
        
        objective_summary = "\n".join(objective_parts)
        
        # Build emotional overlay
        emotional_overlay = {
            "perspective_emotions": self._group_emotions_by_perspective(emotional_claims),
            "dominant_emotions": self._identify_dominant_emotions(emotional_claims),
            "emotional_intensity_range": self._calculate_intensity_range(emotional_claims),
            "perspective_coverage": list(set(claim.perspective for claim in emotional_claims))
        }
        
        return objective_summary, emotional_overlay
    
    def _group_emotions_by_perspective(self, emotional_claims: List[EmotionalClaim]) -> Dict:
        """Group emotions by source perspective"""
        perspective_emotions = {}
        
        for claim in emotional_claims:
            perspective = claim.perspective
            if perspective not in perspective_emotions:
                perspective_emotions[perspective] = []
            
            perspective_emotions[perspective].append({
                "emotion": claim.emotion_type,
                "intensity": claim.intensity,
                "example": claim.claim_text[:100] + "..." if len(claim.claim_text) > 100 else claim.claim_text
            })
        
        return perspective_emotions
    
    def _identify_dominant_emotions(self, emotional_claims: List[EmotionalClaim]) -> List[Dict]:
        """Identify the most prevalent emotions across all sources"""
        emotion_counts = {}
        emotion_intensities = {}
        
        for claim in emotional_claims:
            emotion = claim.emotion_type
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            if emotion not in emotion_intensities:
                emotion_intensities[emotion] = []
            emotion_intensities[emotion].append(claim.intensity)
        
        dominant_emotions = []
        for emotion, count in emotion_counts.items():
            avg_intensity = sum(emotion_intensities[emotion]) / len(emotion_intensities[emotion])
            dominant_emotions.append({
                "emotion": emotion,
                "frequency": count,
                "average_intensity": avg_intensity,
                "prevalence": count / len(emotional_claims) * 100
            })
        
        return sorted(dominant_emotions, key=lambda x: x["prevalence"], reverse=True)[:5]
    
    def _calculate_intensity_range(self, emotional_claims: List[EmotionalClaim]) -> Dict:
        """Calculate emotional intensity statistics"""
        if not emotional_claims:
            return {"min": 0, "max": 0, "average": 0}
            
        intensities = [claim.intensity for claim in emotional_claims]
        return {
            "min": min(intensities),
            "max": max(intensities),
            "average": sum(intensities) / len(intensities)
        }
    
    def _calculate_consensus_score(self, factual_claims: List[FactualClaim]) -> float:
        """Calculate overall factual consensus score"""
        if not factual_claims:
            return 0.0
            
        consensus_scores = [claim.consensus_level for claim in factual_claims]
        return sum(consensus_scores) / len(consensus_scores)
    
    def _calculate_emotional_coverage(self, emotional_claims: List[EmotionalClaim]) -> Dict[str, float]:
        """Calculate emotional spectrum coverage"""
        if not emotional_claims:
            return {}
            
        emotion_counts = {}
        for claim in emotional_claims:
            emotion_counts[claim.emotion_type] = emotion_counts.get(claim.emotion_type, 0) + 1
        
        total_claims = len(emotional_claims)
        return {
            emotion: (count / total_claims) * 100
            for emotion, count in emotion_counts.items()
        }
    
    def _analyze_perspective_breakdown(self, articles: List[NewsArticle]) -> Dict[str, int]:
        """Analyze source perspective distribution"""
        perspective_counts = {}
        for article in articles:
            perspective = article.source_perspective
            perspective_counts[perspective] = perspective_counts.get(perspective, 0) + 1
        
        return perspective_counts
    
    def _generate_reliability_notes(self, articles: List[NewsArticle]) -> str:
        """Generate notes about source reliability and coverage"""
        source_counts = {}
        for article in articles:
            source_counts[article.source] = source_counts.get(article.source, 0) + 1
        
        notes_parts = []
        notes_parts.append(f"Coverage based on {len(articles)} articles from {len(source_counts)} sources.")
        
        if len(source_counts) >= 5:
            notes_parts.append("High source diversity provides strong perspective coverage.")
        elif len(source_counts) >= 3:
            notes_parts.append("Moderate source diversity provides adequate perspective coverage.")
        else:
            notes_parts.append("Limited source diversity - additional perspectives recommended.")
        
        return " ".join(notes_parts)
    
    def _generate_processing_metadata(self, cluster: StoryCluster, 
                                    factual_claims: List[FactualClaim], 
                                    emotional_claims: List[EmotionalClaim]) -> Dict:
        """Generate metadata about the processing"""
        return {
            "total_articles_analyzed": len(cluster.articles),
            "total_factual_claims_extracted": len(factual_claims),
            "total_emotional_claims_extracted": len(emotional_claims),
            "source_diversity_score": cluster.source_diversity_score,
            "perspective_coverage": cluster.perspective_coverage,
            "processing_timestamp": datetime.utcnow().isoformat(),
            "pipeline_version": "news_intelligence_v1.0"
        }