"""
Dual Pipeline Overlay for Factual-Emotional Separation in the Coherence Mapper
Fair Witness Truth Detection System

This module implements a sophisticated dual-pipeline architecture that separates
factual claims from emotional/subjective content, processes them through different
pipelines, and re-synthesizes results as objective facts with emotional overlays.
"""

import numpy as np
import networkx as nx
from scipy.spatial.distance import squareform
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from scipy.signal import coherence
from typing import List, Dict, Tuple, Optional, Any
import logging
import warnings
import json
import re

# Sentiment Analysis imports
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedClaim:
    """Enhanced claim structure with factual-emotional separation"""
    
    def __init__(self, text: str, doc_id: int, source_type: str = "unknown"):
        if not text or not text.strip():
            raise ValueError("Claim text cannot be empty")
        if not isinstance(doc_id, int) or doc_id < 0:
            raise ValueError("Doc ID must be a non-negative integer")
        
        self.text = text.strip()
        self.doc_id = doc_id
        self.source_type = source_type or "unknown"
        self.index = None
        self.cluster_id = None
        self.divergence_score = 0.0
        self.confidence_score = 0.0
        
        # Dual pipeline attributes
        self.is_factual = None
        self.sentiment_score = {}
        self.emotional_descriptors = []
        self.parent_claim_id = None  # For linking split claims
        self.factual_text = ""
        self.emotional_text = ""
        self.processing_pipeline = None  # "factual" or "emotional"

    def __repr__(self):
        return f"EnhancedClaim(text='{self.text[:50]}...', factual={self.is_factual}, pipeline={self.processing_pipeline})"

class EmotionalVariant:
    """Emotional variant structure for non-factual pipeline"""
    
    def __init__(self, emotion_type: str, claims: List[EnhancedClaim], intensity: float = 0.0):
        self.emotion_type = emotion_type
        self.claims = claims or []
        self.intensity = intensity
        self.prevalence = 0.0
        self.descriptors = []
        self.linked_factual_loci = []
        
    def calculate_prevalence(self, total_claims: int) -> float:
        """Calculate prevalence as percentage of total claims"""
        if total_claims == 0:
            return 0.0
        self.prevalence = len(self.claims) / total_claims
        return self.prevalence

class FactualLocus:
    """Factual truth locus from the Higgs substrate pipeline"""
    
    def __init__(self, locus_id: int, factual_claims: List[EnhancedClaim]):
        self.id = locus_id
        self.factual_claims = factual_claims
        self.truth_value = ""
        self.support_mass = 0.0
        self.coherence_score = 0.0
        self.emotional_overlays = []  # List of linked emotional variants
        self.source_diversity = 0
        
    def add_emotional_overlay(self, emotional_variant: EmotionalVariant):
        """Add emotional overlay to this factual locus"""
        self.emotional_overlays.append(emotional_variant)
        emotional_variant.linked_factual_loci.append(self.id)

class DualPipelineDetector:
    """Enhanced truth detector with dual pipeline architecture"""
    
    def __init__(self, min_cluster_size: int = 1, distance_threshold: float = 0.7):
        self.min_cluster_size = min_cluster_size
        self.distance_threshold = distance_threshold
        self.vectorizer = None
        self.embeddings = None
        
        # Sentiment analysis components
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Dual pipeline components
        self.factual_pipeline = None
        self.emotional_pipeline = None
        
        # Fair Witness components
        self.factual_loci = []
        self.emotional_variants = []
        self.fair_witness_narrative = ""
        
        logger.info("Dual Pipeline Detector initialized with Fair Witness architecture")

    def preprocess_claims(self, claims: List[EnhancedClaim]) -> Tuple[List[EnhancedClaim], List[EnhancedClaim]]:
        """
        Preprocessing: Claim Separation Mechanism
        
        Separates claims into factual and non-factual streams based on:
        - Sentiment analysis (VADER)
        - Linguistic cues (modals, subjectives)
        - Dependency parsing patterns
        """
        logger.info(f"Starting claim separation for {len(claims)} claims")
        
        factual_claims = []
        non_factual_claims = []
        
        for claim in claims:
            try:
                # Sentiment analysis with VADER
                vader_scores = self.vader_analyzer.polarity_scores(claim.text)
                
                # TextBlob for additional sentiment analysis
                blob = TextBlob(claim.text)
                
                # Store sentiment scores
                claim.sentiment_score = {
                    'vader_compound': vader_scores['compound'],
                    'vader_pos': vader_scores['pos'],
                    'vader_neg': vader_scores['neg'],
                    'vader_neu': vader_scores['neu'],
                    'textblob_polarity': blob.sentiment.polarity,
                    'textblob_subjectivity': blob.sentiment.subjectivity
                }
                
                # Extract emotional descriptors
                claim.emotional_descriptors = self._extract_emotional_descriptors(claim.text)
                
                # Decision logic for factual vs non-factual
                is_factual = self._classify_claim_type(claim)
                claim.is_factual = is_factual
                
                if is_factual:
                    # Extract factual components
                    claim.factual_text = self._extract_factual_content(claim.text)
                    claim.processing_pipeline = "factual"
                    factual_claims.append(claim)
                    logger.debug(f"Factual claim: {claim.text[:50]}...")
                else:
                    # Extract emotional components
                    claim.emotional_text = self._extract_emotional_content(claim.text)
                    claim.processing_pipeline = "emotional"
                    non_factual_claims.append(claim)
                    logger.debug(f"Emotional claim: {claim.text[:50]}...")
                    
            except Exception as e:
                logger.warning(f"Error processing claim '{claim.text[:50]}...': {str(e)}")
                # Default to factual on error
                claim.is_factual = True
                claim.processing_pipeline = "factual"
                factual_claims.append(claim)
        
        logger.info(f"Claim separation completed: {len(factual_claims)} factual, {len(non_factual_claims)} emotional")
        return factual_claims, non_factual_claims

    def _extract_emotional_descriptors(self, text: str) -> List[str]:
        """Extract emotional keywords and phrases"""
        emotional_patterns = [
            r'\b(terrif\w+|fear\w+|scare\w+|frighten\w+)\b',
            r'\b(confus\w+|unclear|uncertain|doubt\w+)\b',
            r'\b(excit\w+|thrill\w+|amaz\w+|wonder\w+)\b',
            r'\b(anger\w+|mad|furious|outrag\w+)\b',
            r'\b(sad\w+|depress\w+|miserable|devastat\w+)\b',
            r'\b(happy|joy\w+|delight\w+|pleased)\b',
            r'\b(disgusting|revolting|appalling|shocking)\b',
            r'\b(beautiful|gorgeous|stunning|magnificent)\b'
        ]
        
        descriptors = []
        text_lower = text.lower()
        
        for pattern in emotional_patterns:
            matches = re.findall(pattern, text_lower)
            descriptors.extend(matches)
        
        return list(set(descriptors))

    def _classify_claim_type(self, claim: EnhancedClaim) -> bool:
        """
        Classify claim as factual or non-factual based on multiple criteria
        
        Returns True if factual, False if emotional/subjective
        """
        text = claim.text.lower()
        
        # Factual indicators
        factual_indicators = [
            # Objective entities and actions
            r'\b(at|on|in)\s+\d+',  # Time/date references
            r'\b(degrees?|celsius|fahrenheit)\b',  # Measurements
            r'\b(located|situated|positioned)\b',  # Locations
            r'\b(occurs?|happened|took place)\b',  # Events
            r'\b(according to|reported by|stated)\b',  # Attribution
            r'\b(data|statistics|research|study)\b',  # Evidence
        ]
        
        # Non-factual indicators
        subjective_indicators = [
            r'\b(i feel|i think|i believe|i suppose)\b',  # First person opinions
            r'\b(seems?|appears?|looks like)\b',  # Perceptual qualifiers
            r'\b(might|could|may|probably|perhaps)\b',  # Modal uncertainty
            r'\b(terrible|wonderful|amazing|awful)\b',  # Evaluative adjectives
            r'\b(love|hate|adore|despise)\b',  # Emotional verbs
        ]
        
        # Count indicators
        factual_count = sum(1 for pattern in factual_indicators if re.search(pattern, text))
        subjective_count = sum(1 for pattern in subjective_indicators if re.search(pattern, text))
        
        # Sentiment thresholds
        sentiment_score = claim.sentiment_score
        high_subjectivity = sentiment_score.get('textblob_subjectivity', 0) > 0.5
        strong_emotion = abs(sentiment_score.get('vader_compound', 0)) > 0.3
        
        # Decision logic
        if factual_count > subjective_count and not (high_subjectivity and strong_emotion):
            return True
        elif subjective_count > factual_count or (high_subjectivity and strong_emotion):
            return False
        else:
            # Use source type as tie-breaker
            factual_sources = ['science', 'medical', 'academic', 'government', 'expert']
            return claim.source_type in factual_sources

    def _extract_factual_content(self, text: str) -> str:
        """Extract factual components from mixed text"""
        # Simple implementation - remove emotional modifiers
        factual_text = text
        
        # Remove emotional modifiers
        emotion_patterns = [
            r'\b(terrifyingly|amazingly|shockingly|surprisingly)\s+',
            r'\b(i feel that|i think that|i believe that)\s+',
            r'\b(it seems that|it appears that)\s+',
        ]
        
        for pattern in emotion_patterns:
            factual_text = re.sub(pattern, '', factual_text, flags=re.IGNORECASE)
        
        return factual_text.strip()

    def _extract_emotional_content(self, text: str) -> str:
        """Extract emotional components from mixed text"""
        # Simple implementation - focus on emotional elements
        emotional_elements = []
        
        # Extract emotional phrases
        emotion_patterns = [
            r'\b(terrifyingly|amazingly|shockingly|surprisingly)\s+\w+',
            r'\b(i feel|i think|i believe)\s+[^.!?]*',
            r'\b(seems?|appears?)\s+[^.!?]*',
            r'\b(terrible|wonderful|amazing|awful|frightening)\b',
        ]
        
        for pattern in emotion_patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            emotional_elements.extend(matches)
        
        return ' '.join(emotional_elements) if emotional_elements else text

    def process_factual_pipeline(self, factual_claims: List[EnhancedClaim]) -> List[FactualLocus]:
        """
        Factual Pipeline: Enhanced Higgs Substrate Processing
        
        Processes factual claims through the full coherence mapping system
        """
        logger.info(f"Processing {len(factual_claims)} factual claims through Higgs substrate pipeline")
        
        if not factual_claims:
            return []
        
        # Use existing embedding and clustering logic (enhanced for factual-only content)
        embeddings = self._embed_factual_claims(factual_claims)
        clusters = self._cluster_factual_embeddings(embeddings, factual_claims)
        
        # Convert clusters to factual loci
        factual_loci = []
        for i, cluster in enumerate(clusters):
            locus = FactualLocus(i, cluster.members)
            locus.truth_value = cluster.members[0].text if cluster.members else ""
            locus.support_mass = cluster.support
            locus.coherence_score = cluster.coherence_score
            locus.source_diversity = len(set(c.source_type for c in cluster.members))
            factual_loci.append(locus)
        
        logger.info(f"Generated {len(factual_loci)} factual loci")
        return factual_loci

    def process_emotional_pipeline(self, non_factual_claims: List[EnhancedClaim]) -> List[EmotionalVariant]:
        """
        Non-Factual Pipeline: KNN-based Emotional Clustering
        
        Processes emotional/subjective claims through lightweight KNN clustering
        """
        logger.info(f"Processing {len(non_factual_claims)} emotional claims through KNN pipeline")
        
        if not non_factual_claims:
            return []
        
        # Emotion-aware embedding
        embeddings = self._embed_emotional_claims(non_factual_claims)
        
        # KNN clustering for emotional content
        emotional_clusters = self._cluster_emotional_embeddings(embeddings, non_factual_claims)
        
        # Convert to emotional variants
        emotional_variants = []
        for emotion_type, claims in emotional_clusters.items():
            variant = EmotionalVariant(emotion_type, claims)
            variant.intensity = self._calculate_emotional_intensity(claims)
            variant.prevalence = variant.calculate_prevalence(len(non_factual_claims))
            variant.descriptors = self._aggregate_descriptors(claims)
            emotional_variants.append(variant)
        
        logger.info(f"Generated {len(emotional_variants)} emotional variants")
        return emotional_variants

    def _embed_factual_claims(self, claims: List[EnhancedClaim]) -> np.ndarray:
        """Enhanced embedding for factual claims"""
        if not claims:
            return np.array([])
        
        # Focus on factual content
        factual_texts = [claim.factual_text or claim.text for claim in claims]
        
        # Enhanced preprocessing for factual content
        processed_texts = []
        for text in factual_texts:
            # Remove emotional noise, focus on entities and actions
            processed = re.sub(r'\b(i feel|i think|seems?|appears?)\b', '', text.lower())
            processed = re.sub(r'\s+', ' ', processed).strip()
            processed_texts.append(processed)
        
        # TF-IDF with factual focus
        if len(claims) == 1:
            embeddings = np.array([[1.0] * 10])
        else:
            vectorizer = TfidfVectorizer(
                max_features=min(1000, len(claims) * 50),
                min_df=1,
                max_df=0.8,
                stop_words='english',
                ngram_range=(1, 2),
                token_pattern=r'\b[A-Za-z]{2,}\b'
            )
            embeddings = vectorizer.fit_transform(processed_texts).toarray()
        
        for i, claim in enumerate(claims):
            claim.index = i
        
        return embeddings

    def _embed_emotional_claims(self, claims: List[EnhancedClaim]) -> np.ndarray:
        """Emotion-aware embedding for non-factual claims"""
        if not claims:
            return np.array([])
        
        # Focus on emotional content
        emotional_texts = [claim.emotional_text or claim.text for claim in claims]
        
        # Add sentiment context
        enhanced_texts = []
        for i, text in enumerate(emotional_texts):
            claim = claims[i]
            sentiment_context = f"[{claim.sentiment_score.get('vader_compound', 0):.2f}]"
            enhanced_texts.append(f"{text} {sentiment_context}")
        
        # Emotion-focused TF-IDF
        if len(claims) == 1:
            embeddings = np.array([[1.0] * 8])
        else:
            vectorizer = TfidfVectorizer(
                max_features=min(500, len(claims) * 20),
                min_df=1,
                max_df=0.9,
                stop_words='english',
                ngram_range=(1, 2),
                token_pattern=r'\b[A-Za-z]{2,}\b'
            )
            embeddings = vectorizer.fit_transform(enhanced_texts).toarray()
        
        for i, claim in enumerate(claims):
            claim.index = i
        
        return embeddings

    def _cluster_factual_embeddings(self, embeddings: np.ndarray, claims: List[EnhancedClaim]) -> List:
        """Cluster factual embeddings using enhanced semantic similarity"""
        # Import the original clustering logic from truth_detector
        from truth_detector import Cluster
        
        if len(claims) == 0:
            return []
        
        # Use existing clustering logic but enhanced for factual content
        clusters = []
        assigned_claims = set()
        
        # Semantic groups for factual content
        factual_groups = {
            'scientific_facts': ['temperature', 'degrees', 'celsius', 'fahrenheit', 'measurement', 'study', 'research'],
            'location_facts': ['located', 'situated', 'positioned', 'coordinates', 'address', 'place'],
            'time_facts': ['occurred', 'happened', 'time', 'date', 'when', 'during'],
            'entity_facts': ['organization', 'company', 'person', 'government', 'institution'],
            'event_facts': ['collision', 'accident', 'meeting', 'conference', 'incident', 'event']
        }
        
        # Group claims by semantic similarity
        for group_name, keywords in factual_groups.items():
            group_claims = []
            for i, claim in enumerate(claims):
                if i in assigned_claims:
                    continue
                
                claim_text = claim.factual_text.lower()
                keyword_matches = sum(1 for keyword in keywords if keyword in claim_text)
                if keyword_matches >= 1:
                    group_claims.append(claim)
                    assigned_claims.add(i)
            
            if len(group_claims) >= 1:
                cluster = Cluster(len(clusters), group_claims)
                for claim in group_claims:
                    claim.cluster_id = cluster.id
                clusters.append(cluster)
        
        # Handle remaining claims
        for i, claim in enumerate(claims):
            if i not in assigned_claims:
                cluster = Cluster(len(clusters), [claim])
                claim.cluster_id = cluster.id
                clusters.append(cluster)
        
        # Calculate support and coherence for each cluster
        similarity_matrix = cosine_similarity(embeddings)
        for cluster in clusters:
            cluster_indices = [c.index for c in cluster.members if c.index is not None]
            if cluster_indices:
                # Calculate support based on source diversity and coherence
                sources = set(c.source_type for c in cluster.members)
                base_support = len(cluster.members)
                diversity_bonus = 0.5 * len(sources)
                
                # Coherence calculation
                if len(cluster_indices) > 1:
                    cluster_similarities = similarity_matrix[np.ix_(cluster_indices, cluster_indices)]
                    coherence_score = np.mean(cluster_similarities)
                else:
                    coherence_score = 1.0
                
                cluster.support = base_support * (1 + diversity_bonus) * coherence_score
                cluster.coherence_score = coherence_score
        
        return clusters

    def _cluster_emotional_embeddings(self, embeddings: np.ndarray, claims: List[EnhancedClaim]) -> Dict[str, List[EnhancedClaim]]:
        """KNN-based clustering for emotional content"""
        if len(claims) == 0:
            return {}
        
        # Define emotion categories
        emotion_categories = {
            'fear': ['terrif', 'scare', 'frighten', 'fear', 'afraid'],
            'confusion': ['confus', 'unclear', 'uncertain', 'doubt'],
            'excitement': ['excit', 'thrill', 'amaz', 'wonder'],
            'anger': ['anger', 'mad', 'furious', 'outrag'],
            'sadness': ['sad', 'depress', 'miserable', 'devastat'],
            'joy': ['happy', 'joy', 'delight', 'pleased'],
            'disgust': ['disgust', 'revolt', 'appal', 'shock'],
            'admiration': ['beautiful', 'gorgeous', 'stunning', 'magnificent']
        }
        
        emotional_clusters = {}
        
        # Categorize claims by dominant emotion
        for claim in claims:
            claim_text = claim.emotional_text.lower()
            best_category = 'neutral'
            max_score = 0
            
            for category, keywords in emotion_categories.items():
                score = sum(1 for keyword in keywords if keyword in claim_text)
                if score > max_score:
                    max_score = score
                    best_category = category
            
            # Also consider VADER sentiment
            vader_compound = claim.sentiment_score.get('vader_compound', 0)
            if abs(vader_compound) > 0.5:
                if vader_compound > 0:
                    best_category = 'joy' if best_category == 'neutral' else best_category
                else:
                    best_category = 'fear' if best_category == 'neutral' else best_category
            
            if best_category not in emotional_clusters:
                emotional_clusters[best_category] = []
            emotional_clusters[best_category].append(claim)
        
        return emotional_clusters

    def _calculate_emotional_intensity(self, claims: List[EnhancedClaim]) -> float:
        """Calculate average emotional intensity for a group of claims"""
        if not claims:
            return 0.0
        
        intensities = []
        for claim in claims:
            # Combine VADER compound score with TextBlob subjectivity
            vader_intensity = abs(claim.sentiment_score.get('vader_compound', 0))
            textblob_intensity = claim.sentiment_score.get('textblob_subjectivity', 0)
            
            # Weighted average
            combined_intensity = (vader_intensity * 0.7) + (textblob_intensity * 0.3)
            intensities.append(combined_intensity)
        
        return np.mean(intensities) * 10  # Scale to 0-10

    def _aggregate_descriptors(self, claims: List[EnhancedClaim]) -> List[str]:
        """Aggregate emotional descriptors from a group of claims"""
        all_descriptors = []
        for claim in claims:
            all_descriptors.extend(claim.emotional_descriptors)
        
        # Count frequencies and return most common
        descriptor_counts = {}
        for descriptor in all_descriptors:
            descriptor_counts[descriptor] = descriptor_counts.get(descriptor, 0) + 1
        
        # Return top descriptors
        sorted_descriptors = sorted(descriptor_counts.items(), key=lambda x: x[1], reverse=True)
        return [desc for desc, count in sorted_descriptors[:5]]

    def link_emotional_overlays(self, factual_loci: List[FactualLocus], emotional_variants: List[EmotionalVariant]):
        """Link emotional variants to factual loci using embedding proximity"""
        logger.info("Linking emotional overlays to factual loci")
        
        if not factual_loci or not emotional_variants:
            return
        
        # Create embeddings for linking
        factual_texts = [locus.truth_value for locus in factual_loci]
        emotional_texts = [variant.emotion_type + " " + " ".join(variant.descriptors) for variant in emotional_variants]
        
        if not factual_texts or not emotional_texts:
            return
        
        # Simple embedding for linking
        try:
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            all_texts = factual_texts + emotional_texts
            embeddings = vectorizer.fit_transform(all_texts).toarray()
            
            factual_embeddings = embeddings[:len(factual_loci)]
            emotional_embeddings = embeddings[len(factual_loci):]
            
            # Find nearest factual loci for each emotional variant
            for i, variant in enumerate(emotional_variants):
                emotional_emb = emotional_embeddings[i].reshape(1, -1)
                similarities = cosine_similarity(emotional_emb, factual_embeddings)[0]
                
                # Link to most similar factual loci (top 2)
                top_indices = np.argsort(similarities)[-2:]
                for idx in top_indices:
                    if similarities[idx] > 0.1:  # Minimum similarity threshold
                        factual_loci[idx].add_emotional_overlay(variant)
                        
        except Exception as e:
            logger.warning(f"Error linking emotional overlays: {str(e)}")

    def synthesize_fair_witness_narrative(self, factual_loci: List[FactualLocus], emotional_variants: List[EmotionalVariant]) -> str:
        """
        Generate Fair Witness narrative: objective facts with emotional overlays
        """
        logger.info("Synthesizing Fair Witness narrative")
        
        narrative_parts = []
        
        # Header
        narrative_parts.append("=== FAIR WITNESS TRUTH SYNTHESIS ===\n")
        
        # Factual narrative base
        narrative_parts.append("**FACTUAL NARRATIVE (Objective Observations):**\n")
        
        high_support_loci = [locus for locus in factual_loci if locus.support_mass > 1.0]
        if high_support_loci:
            for i, locus in enumerate(high_support_loci[:5], 1):
                narrative_parts.append(f"{i}. {locus.truth_value}")
                narrative_parts.append(f"   └─ Support: {locus.support_mass:.2f}, Coherence: {locus.coherence_score:.3f}, Sources: {locus.source_diversity}")
                
                # Add emotional overlays
                if locus.emotional_overlays:
                    narrative_parts.append("   └─ Emotional Overlays:")
                    for overlay in locus.emotional_overlays:
                        narrative_parts.append(f"      • {overlay.emotion_type.title()}: {overlay.intensity:.1f}/10 intensity, {overlay.prevalence:.1%} prevalence")
                        if overlay.descriptors:
                            narrative_parts.append(f"        Descriptors: {', '.join(overlay.descriptors)}")
                narrative_parts.append("")
        else:
            narrative_parts.append("No high-confidence factual patterns detected.\n")
        
        # Emotional summary
        narrative_parts.append("**EMOTIONAL LANDSCAPE (Perceptual Overlays):**\n")
        
        if emotional_variants:
            for variant in emotional_variants:
                narrative_parts.append(f"• {variant.emotion_type.title()}: {variant.intensity:.1f}/10 intensity, {variant.prevalence:.1%} of sources")
                if variant.descriptors:
                    narrative_parts.append(f"  Descriptors: {', '.join(variant.descriptors)}")
                narrative_parts.append(f"  Claims: {len(variant.claims)}")
        else:
            narrative_parts.append("No significant emotional patterns detected.\n")
        
        # Fair Witness disclaimer
        narrative_parts.append("\n**FAIR WITNESS DISCLAIMER:**")
        narrative_parts.append("This analysis presents factual claims with quantified emotional overlays.")
        narrative_parts.append("Emotional data is reported as observed patterns, not endorsed perspectives.")
        narrative_parts.append("The Fair Witness observes without interpretation or bias.")
        
        return "\n".join(narrative_parts)

    def analyze_claims_dual_pipeline(self, claims: List[EnhancedClaim]) -> Dict[str, Any]:
        """
        Main analysis pipeline with dual processing architecture
        """
        try:
            logger.info(f"Starting dual pipeline analysis on {len(claims)} claims")
            
            if not claims:
                return self._empty_analysis_result("No claims provided")
            
            # Step 1: Preprocessing - Claim Separation
            factual_claims, non_factual_claims = self.preprocess_claims(claims)
            
            # Step 2: Dual Pipeline Processing
            factual_loci = self.process_factual_pipeline(factual_claims)
            emotional_variants = self.process_emotional_pipeline(non_factual_claims)
            
            # Step 3: Link Emotional Overlays
            self.link_emotional_overlays(factual_loci, emotional_variants)
            
            # Step 4: Generate Fair Witness Narrative
            fair_witness_narrative = self.synthesize_fair_witness_narrative(factual_loci, emotional_variants)
            
            # Step 5: Compile Results
            results = {
                'total_claims': len(claims),
                'factual_claims': len(factual_claims),
                'emotional_claims': len(non_factual_claims),
                'factual_loci': len(factual_loci),
                'emotional_variants': len(emotional_variants),
                'fair_witness_narrative': fair_witness_narrative,
                'processing_details': {
                    'factual_pipeline': self._serialize_factual_loci(factual_loci),
                    'emotional_pipeline': self._serialize_emotional_variants(emotional_variants),
                    'claim_separation': self._serialize_claim_separation(factual_claims, non_factual_claims)
                },
                'dual_pipeline_summary': self._generate_dual_pipeline_summary(factual_loci, emotional_variants, len(claims))
            }
            
            logger.info("Dual pipeline analysis completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Critical error in dual pipeline analysis: {str(e)}")
            return self._empty_analysis_result(f"Analysis failed: {str(e)}")

    def _empty_analysis_result(self, error_message: str) -> Dict[str, Any]:
        """Return empty analysis result with error message"""
        return {
            'error': error_message,
            'total_claims': 0,
            'factual_claims': 0,
            'emotional_claims': 0,
            'factual_loci': 0,
            'emotional_variants': 0,
            'fair_witness_narrative': 'Analysis failed',
            'processing_details': {},
            'dual_pipeline_summary': error_message
        }

    def _serialize_factual_loci(self, factual_loci: List[FactualLocus]) -> List[Dict]:
        """Serialize factual loci for JSON response"""
        return [
            {
                'id': locus.id,
                'truth_value': locus.truth_value,
                'support_mass': float(locus.support_mass),
                'coherence_score': float(locus.coherence_score),
                'source_diversity': int(locus.source_diversity),
                'claim_count': len(locus.factual_claims),
                'emotional_overlays': [
                    {
                        'emotion_type': overlay.emotion_type,
                        'intensity': float(overlay.intensity),
                        'prevalence': float(overlay.prevalence),
                        'descriptors': overlay.descriptors
                    }
                    for overlay in locus.emotional_overlays
                ]
            }
            for locus in factual_loci
        ]

    def _serialize_emotional_variants(self, emotional_variants: List[EmotionalVariant]) -> List[Dict]:
        """Serialize emotional variants for JSON response"""
        return [
            {
                'emotion_type': variant.emotion_type,
                'intensity': float(variant.intensity),
                'prevalence': float(variant.prevalence),
                'descriptors': variant.descriptors,
                'claim_count': len(variant.claims),
                'linked_factual_loci': variant.linked_factual_loci
            }
            for variant in emotional_variants
        ]

    def _serialize_claim_separation(self, factual_claims: List[EnhancedClaim], non_factual_claims: List[EnhancedClaim]) -> Dict:
        """Serialize claim separation details"""
        return {
            'separation_summary': {
                'total_factual': len(factual_claims),
                'total_emotional': len(non_factual_claims),
                'factual_percentage': len(factual_claims) / (len(factual_claims) + len(non_factual_claims)) * 100 if (factual_claims or non_factual_claims) else 0,
                'emotional_percentage': len(non_factual_claims) / (len(factual_claims) + len(non_factual_claims)) * 100 if (factual_claims or non_factual_claims) else 0
            },
            'factual_samples': [
                {
                    'text': claim.text[:100] + "..." if len(claim.text) > 100 else claim.text,
                    'source_type': claim.source_type,
                    'factual_text': claim.factual_text[:100] + "..." if len(claim.factual_text) > 100 else claim.factual_text,
                    'sentiment_score': claim.sentiment_score
                }
                for claim in factual_claims[:3]
            ],
            'emotional_samples': [
                {
                    'text': claim.text[:100] + "..." if len(claim.text) > 100 else claim.text,
                    'source_type': claim.source_type,
                    'emotional_text': claim.emotional_text[:100] + "..." if len(claim.emotional_text) > 100 else claim.emotional_text,
                    'sentiment_score': claim.sentiment_score,
                    'emotional_descriptors': claim.emotional_descriptors
                }
                for claim in non_factual_claims[:3]
            ]
        }

    def _generate_dual_pipeline_summary(self, factual_loci: List[FactualLocus], emotional_variants: List[EmotionalVariant], total_claims: int) -> str:
        """Generate comprehensive dual pipeline summary"""
        summary_parts = []
        
        summary_parts.append("=== DUAL PIPELINE ANALYSIS SUMMARY ===\n")
        
        # Processing overview
        summary_parts.append("**PROCESSING OVERVIEW:**")
        summary_parts.append(f"- Total Claims: {total_claims}")
        summary_parts.append(f"- Factual Pipeline: {len(factual_loci)} truth loci generated")
        summary_parts.append(f"- Emotional Pipeline: {len(emotional_variants)} emotional variants detected")
        summary_parts.append("")
        
        # Factual findings
        if factual_loci:
            summary_parts.append("**FACTUAL FINDINGS (Higgs Substrate Analysis):**")
            high_support = [locus for locus in factual_loci if locus.support_mass > 1.0]
            for locus in high_support[:5]:
                summary_parts.append(f"- {locus.truth_value}")
                summary_parts.append(f"  Support: {locus.support_mass:.2f}, Coherence: {locus.coherence_score:.3f}")
            summary_parts.append("")
        
        # Emotional findings
        if emotional_variants:
            summary_parts.append("**EMOTIONAL FINDINGS (KNN Analysis):**")
            sorted_variants = sorted(emotional_variants, key=lambda x: x.intensity, reverse=True)
            for variant in sorted_variants[:5]:
                summary_parts.append(f"- {variant.emotion_type.title()}: {variant.intensity:.1f}/10 intensity, {variant.prevalence:.1%} prevalence")
                if variant.descriptors:
                    summary_parts.append(f"  Descriptors: {', '.join(variant.descriptors)}")
            summary_parts.append("")
        
        # Fair Witness observations
        summary_parts.append("**FAIR WITNESS OBSERVATIONS:**")
        summary_parts.append("- Factual claims processed through rigorous coherence analysis")
        summary_parts.append("- Emotional content objectively quantified and categorized")
        summary_parts.append("- No interpretive bias applied to emotional overlays")
        summary_parts.append("- Results presented as observed patterns, not endorsed truths")
        
        return "\n".join(summary_parts)

# Factory function for dual pipeline detector
def create_dual_pipeline_detector(min_cluster_size: int = 1, distance_threshold: float = 0.7) -> DualPipelineDetector:
    """Create a configured dual pipeline detector instance"""
    return DualPipelineDetector(min_cluster_size, distance_threshold)

# Convenience function for dual pipeline analysis
def analyze_claims_dual_pipeline(claims_data: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function to analyze claims with dual pipeline
    
    Args:
        claims_data: List of dictionaries with keys: 'text', 'doc_id', 'source_type'
    
    Returns:
        Dictionary with dual pipeline analysis results
    """
    try:
        # Convert to EnhancedClaim objects
        claims = []
        for i, claim_data in enumerate(claims_data):
            claim = EnhancedClaim(
                text=claim_data.get('text', ''),
                doc_id=claim_data.get('doc_id', i),
                source_type=claim_data.get('source_type', 'unknown')
            )
            claims.append(claim)
        
        # Analyze with dual pipeline
        detector = create_dual_pipeline_detector()
        results = detector.analyze_claims_dual_pipeline(claims)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in dual pipeline analysis: {str(e)}")
        return {
            'error': str(e),
            'total_claims': 0,
            'factual_claims': 0,
            'emotional_claims': 0,
            'fair_witness_narrative': 'Analysis failed',
            'dual_pipeline_summary': f'Analysis failed: {str(e)}'
        }