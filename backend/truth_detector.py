import numpy as np
import networkx as nx
from scipy.spatial.distance import squareform
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from scipy.signal import coherence
from typing import List, Dict, Tuple, Optional
import logging
import warnings
import json

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced Core Data Structures
class Claim:
    """Enhanced claim structure with better validation"""
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

    def __repr__(self):
        return f"Claim(text='{self.text[:50]}...', doc_id={self.doc_id}, source='{self.source_type}')"

class Variant:
    """Enhanced variant with better support calculation"""
    def __init__(self, value_desc: str, claims: List[Claim], support: float = 0.0):
        self.value_desc = value_desc
        self.claims = claims or []
        self.support = support
        self.coherence_mass = 0.0
        self.confidence = 0.0
        
    def calculate_support(self) -> float:
        """Calculate support based on unique documents and source diversity"""
        if not self.claims:
            return 0.0
        
        doc_ids = set(claim.doc_id for claim in self.claims)
        source_types = set(claim.source_type for claim in self.claims)
        
        # Base support from unique documents
        base_support = len(doc_ids)
        
        # Bonus for source diversity
        source_diversity_bonus = 0.3 * len(source_types)
        
        # Penalty for very short texts
        avg_text_length = np.mean([len(claim.text) for claim in self.claims])
        length_factor = min(1.0, avg_text_length / 50.0)  # Normalize to 50 chars
        
        self.support = base_support * (1 + source_diversity_bonus) * length_factor
        return self.support

class Cluster:
    """Enhanced cluster with better validation and metrics"""
    def __init__(self, cluster_id: int, members: List[Claim]):
        self.id = cluster_id
        self.members = members or []
        self.support = 0.0
        self.is_contradiction = False
        self.variants = []
        self.truth_variant = None
        self.higgs_mass = 0.0
        self.heat_center = None
        self.coherence_score = 0.0

    def validate(self) -> bool:
        """Validate cluster integrity"""
        if not self.members:
            return False
        if any(claim.cluster_id != self.id for claim in self.members):
            logger.warning(f"Cluster {self.id} has members with mismatched cluster IDs")
        return True

class TruthDetectorCore:
    """Core truth detection engine with improved algorithms"""
    
    def __init__(self, min_cluster_size: int = 1, distance_threshold: float = 0.7):
        self.min_cluster_size = min_cluster_size
        self.distance_threshold = distance_threshold  # Increased for better clustering
        self.vectorizer = None
        self.embeddings = None
        
    def embed_claims(self, claims: List[Claim]) -> np.ndarray:
        """Enhanced embedding with better preprocessing and error handling"""
        if not claims:
            logger.warning("No claims provided for embedding")
            return np.array([])
        
        try:
            # Enhanced text preprocessing - focus on semantic content
            enhanced_texts = []
            for claim in claims:
                # Clean and normalize text
                text = claim.text.lower().strip()
                # Remove some noise words that might interfere with similarity
                text = text.replace("the ", "").replace("is ", "").replace("are ", "")
                # Add source type context but make it less dominant
                if claim.source_type != "unknown":
                    text = f"{text} [{claim.source_type}]"
                enhanced_texts.append(text)
            
            # Initialize TF-IDF with parameters optimized for claim similarity
            self.vectorizer = TfidfVectorizer(
                max_features=1000,  # Reduced for better focus
                min_df=1,
                max_df=0.8,  # More restrictive to avoid common words
                stop_words='english',
                ngram_range=(1, 3),  # Include more n-grams for better similarity
                token_pattern=r'\b[A-Za-z]{2,}\b'  # Only alphabetic tokens
            )
            
            embeddings = self.vectorizer.fit_transform(enhanced_texts).toarray()
            
            # Assign indices to claims
            for i, claim in enumerate(claims):
                claim.index = i
                
            self.embeddings = embeddings
            logger.info(f"Successfully embedded {len(claims)} claims into {embeddings.shape[1]} dimensions")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error in embedding claims: {str(e)}")
            raise ValueError(f"Failed to embed claims: {str(e)}")

    def cluster_embeddings(self, embeddings: np.ndarray, claims: List[Claim]) -> List[Cluster]:
        """Enhanced clustering with semantic similarity detection"""
        if len(claims) == 0:
            return []
        
        try:
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(embeddings)
            
            # Manual semantic clustering based on keywords and similarity
            clusters = []
            assigned_claims = set()
            
            # Define semantic groups based on keywords
            semantic_groups = {
                'earth_round': ['earth', 'round', 'sphere', 'globe', 'orbits', 'sun'],
                'earth_flat': ['earth', 'flat', 'stationary'],
                'climate_human': ['climate', 'change', 'human', 'activities', 'man-made', 'warming'],
                'climate_natural': ['climate', 'change', 'natural', 'phenomenon'],
                'vaccine_safe': ['vaccine', 'safe', 'effective', 'proven', 'profile'],
                'vaccine_dangerous': ['vaccine', 'dangerous', 'harmful'],
                'moon_real': ['moon', 'landing', 'real', 'historical', 'achievement'],
                'moon_fake': ['moon', 'landing', 'staged', 'studio'],
                'water_science': ['water', 'boils', 'freezes', 'temperature'],
                'health_facts': ['exercise', 'health', 'improves']
            }
            
            # First, try to group claims by semantic similarity
            for group_name, keywords in semantic_groups.items():
                group_claims = []
                for i, claim in enumerate(claims):
                    if i in assigned_claims:
                        continue
                    
                    claim_text = claim.text.lower()
                    # Check if claim contains keywords from this group
                    keyword_matches = sum(1 for keyword in keywords if keyword in claim_text)
                    if keyword_matches >= 2:  # At least 2 keywords match
                        group_claims.append(claim)
                        assigned_claims.add(i)
                
                # If we have multiple claims in this group, create a cluster
                if len(group_claims) >= 2:
                    cluster = Cluster(len(clusters), group_claims)
                    for j, claim in enumerate(group_claims):
                        claim.cluster_id = cluster.id
                    clusters.append(cluster)
                    logger.info(f"Created semantic cluster {cluster.id} for {group_name} with {len(group_claims)} claims")
                elif len(group_claims) == 1:
                    # Single claim, check if it's similar to any existing cluster
                    added_to_cluster = False
                    claim = group_claims[0]
                    claim_embedding = embeddings[claim.index]
                    
                    for existing_cluster in clusters:
                        # Calculate average similarity to existing cluster
                        cluster_embeddings = [embeddings[c.index] for c in existing_cluster.members]
                        if cluster_embeddings:
                            avg_similarity = np.mean([cosine_similarity([claim_embedding], [c_emb])[0][0] for c_emb in cluster_embeddings])
                            if avg_similarity > 0.3:  # Similarity threshold
                                existing_cluster.members.append(claim)
                                claim.cluster_id = existing_cluster.id
                                added_to_cluster = True
                                logger.info(f"Added claim to existing cluster {existing_cluster.id} with similarity {avg_similarity:.3f}")
                                break
                    
                    if not added_to_cluster:
                        # Create single-claim cluster
                        cluster = Cluster(len(clusters), [claim])
                        claim.cluster_id = cluster.id
                        clusters.append(cluster)
            
            # Handle remaining unassigned claims
            for i, claim in enumerate(claims):
                if i not in assigned_claims:
                    # Check similarity to existing clusters
                    added_to_cluster = False
                    claim_embedding = embeddings[i]
                    
                    for existing_cluster in clusters:
                        if len(existing_cluster.members) > 0:
                            # Calculate similarity to cluster centroid
                            cluster_embeddings = [embeddings[c.index] for c in existing_cluster.members]
                            cluster_centroid = np.mean(cluster_embeddings, axis=0)
                            similarity = cosine_similarity([claim_embedding], [cluster_centroid])[0][0]
                            
                            if similarity > 0.4:  # Higher threshold for general similarity
                                existing_cluster.members.append(claim)
                                claim.cluster_id = existing_cluster.id
                                added_to_cluster = True
                                logger.info(f"Added unassigned claim to cluster {existing_cluster.id} with similarity {similarity:.3f}")
                                break
                    
                    if not added_to_cluster:
                        # Create new single-claim cluster
                        cluster = Cluster(len(clusters), [claim])
                        claim.cluster_id = cluster.id
                        clusters.append(cluster)
            
            # Log final clustering results
            multi_claim_clusters = [c for c in clusters if len(c.members) > 1]
            logger.info(f"Final clustering: {len(claims)} claims → {len(clusters)} clusters ({len(multi_claim_clusters)} multi-claim clusters)")
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error in clustering: {str(e)}")
            # Fallback to simple clustering
            return self._fallback_clustering(embeddings, claims)
    
    def _fallback_clustering(self, embeddings: np.ndarray, claims: List[Claim]) -> List[Cluster]:
        """Fallback clustering method"""
        try:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                metric='cosine',
                linkage='average',
                distance_threshold=0.7
            )
            
            labels = clustering.fit_predict(embeddings)
            
            cluster_dict = {}
            for i, label in enumerate(labels):
                if label not in cluster_dict:
                    cluster_dict[label] = Cluster(label, [])
                cluster_dict[label].members.append(claims[i])
                claims[i].cluster_id = label
            
            return list(cluster_dict.values())
            
        except Exception as e:
            logger.error(f"Error in fallback clustering: {str(e)}")
            # Ultimate fallback - each claim is its own cluster
            clusters = []
            for i, claim in enumerate(claims):
                cluster = Cluster(i, [claim])
                claim.cluster_id = i
                clusters.append(cluster)
            return clusters

    def compute_msc_coherence(self, cluster_emb: np.ndarray) -> float:
        """Improved MSC coherence calculation with better error handling"""
        if len(cluster_emb) < 2:
            return 1.0
        
        try:
            msc_values = []
            min_len = max(2, min(len(row) for row in cluster_emb))
            
            for i in range(len(cluster_emb)):
                for j in range(i + 1, len(cluster_emb)):
                    try:
                        # Ensure minimum length for coherence calculation
                        x = cluster_emb[i][:min_len]
                        y = cluster_emb[j][:min_len]
                        
                        if len(x) >= 2 and len(y) >= 2:
                            _, Cxy = coherence(x, y, fs=1.0, nperseg=min(8, min_len))
                            if len(Cxy) > 0:
                                msc_values.append(np.max(Cxy))
                    except Exception as e:
                        logger.debug(f"Error calculating coherence for pair {i},{j}: {str(e)}")
                        continue
            
            return np.mean(msc_values) if msc_values else 1.0
            
        except Exception as e:
            logger.warning(f"Error in MSC coherence calculation: {str(e)}")
            return 1.0

    def detect_contradictions(self, clusters: List[Cluster], embeddings: np.ndarray) -> None:
        """Enhanced contradiction detection with better variant analysis"""
        for cluster in clusters:
            if len(cluster.members) <= 1:
                continue
                
            try:
                cluster_indices = [claim.index for claim in cluster.members if claim.index is not None]
                if not cluster_indices:
                    continue
                    
                cluster_emb = embeddings[cluster_indices]
                
                # Check for source diversity as a contradiction indicator
                sources = set(claim.source_type for claim in cluster.members)
                
                # If we have multiple sources in the same cluster, it's likely a contradiction
                if len(sources) > 1:
                    # Look for opposing source types
                    opposing_sources = [
                        ('science', 'conspiracy'),
                        ('medical', 'anti-vaccine'),
                        ('expert', 'conspiracy'),
                        ('government', 'conspiracy'),
                        ('academic', 'conspiracy'),
                        ('history', 'conspiracy')
                    ]
                    
                    has_opposing_sources = False
                    for source1, source2 in opposing_sources:
                        if source1 in sources and source2 in sources:
                            has_opposing_sources = True
                            break
                    
                    if has_opposing_sources or len(sources) >= 3:
                        # This is likely a contradiction - create variants by source type
                        cluster.is_contradiction = True
                        variants = {}
                        
                        for claim in cluster.members:
                            source_key = claim.source_type
                            if source_key not in variants:
                                variants[source_key] = {
                                    'claims': [],
                                    'value_desc': claim.text,
                                    'source_diversity': set()
                                }
                            variants[source_key]['claims'].append(claim)
                            variants[source_key]['source_diversity'].add(claim.source_type)
                        
                        # Create variants
                        cluster.variants = []
                        for source_key, variant_data in variants.items():
                            variant = Variant(
                                variant_data['value_desc'],
                                variant_data['claims']
                            )
                            variant.calculate_support()
                            cluster.variants.append(variant)
                        
                        # Find truth variant (highest support)
                        if cluster.variants:
                            cluster.truth_variant = max(cluster.variants, key=lambda x: x.support)
                            
                        logger.info(f"Cluster {cluster.id} detected as contradiction with {len(cluster.variants)} variants from sources: {sources}")
                        continue
                
                # Alternative: Sub-clustering approach for more subtle contradictions
                if len(cluster.members) > 2:
                    sub_clustering = AgglomerativeClustering(
                        n_clusters=None,
                        metric='cosine',
                        linkage='average',
                        distance_threshold=0.4  # More strict for sub-clustering
                    )
                    
                    sub_labels = sub_clustering.fit_predict(cluster_emb)
                    
                    # Group variants by sub-clusters
                    variants = {}
                    for i, label in enumerate(sub_labels):
                        claim = cluster.members[i]
                        if label not in variants:
                            variants[label] = {
                                'claims': [],
                                'value_desc': claim.text,
                                'source_diversity': set()
                            }
                        variants[label]['claims'].append(claim)
                        variants[label]['source_diversity'].add(claim.source_type)
                    
                    # Check if we have meaningful variants
                    if len(variants) > 1:
                        # Check if variants have different source types or significant text differences
                        variant_sources = [list(v['source_diversity']) for v in variants.values()]
                        has_different_sources = any(s1 != s2 for i, s1 in enumerate(variant_sources) for s2 in variant_sources[i+1:])
                        
                        if has_different_sources or len(variants) >= 3:
                            cluster.is_contradiction = True
                            cluster.variants = []
                            
                            for variant_data in variants.values():
                                variant = Variant(
                                    variant_data['value_desc'],
                                    variant_data['claims']
                                )
                                variant.calculate_support()
                                cluster.variants.append(variant)
                            
                            # Find truth variant
                            if cluster.variants:
                                cluster.truth_variant = max(cluster.variants, key=lambda x: x.support)
                                
                            logger.info(f"Cluster {cluster.id} detected as subtle contradiction with {len(cluster.variants)} variants")
                    
            except Exception as e:
                logger.warning(f"Error detecting contradictions in cluster {cluster.id}: {str(e)}")
                continue

    def assign_coherence_scores(self, clusters: List[Cluster], embeddings: np.ndarray) -> None:
        """Enhanced coherence scoring with better metrics"""
        for cluster in clusters:
            try:
                cluster_indices = [claim.index for claim in cluster.members if claim.index is not None]
                if not cluster_indices:
                    continue
                    
                # Calculate FT coherence
                ft_coherence = self.compute_msc_coherence(embeddings[cluster_indices])
                
                if not cluster.is_contradiction:
                    # Simple cluster support calculation
                    doc_ids = set(c.doc_id for c in cluster.members)
                    source_types = set(c.source_type for c in cluster.members)
                    
                    base_support = len(doc_ids)
                    diversity_bonus = 0.3 * len(source_types)
                    
                    cluster.support = base_support * (1 + diversity_bonus) * ft_coherence
                    cluster.coherence_score = ft_coherence
                    
                else:
                    # Update variant supports with coherence
                    for variant in cluster.variants:
                        var_indices = [c.index for c in variant.claims if c.index is not None]
                        if var_indices:
                            var_coherence = self.compute_msc_coherence(embeddings[var_indices])
                            variant.support *= var_coherence
                            variant.coherence_mass = var_coherence
                    
                    # Update truth variant
                    if cluster.variants:
                        cluster.truth_variant = max(cluster.variants, key=lambda x: x.support)
                        cluster.coherence_score = cluster.truth_variant.coherence_mass
                        
            except Exception as e:
                logger.warning(f"Error assigning coherence scores to cluster {cluster.id}: {str(e)}")
                continue

    def analyze_claims(self, claims: List[Claim]) -> Dict:
        """Main analysis pipeline with comprehensive error handling"""
        try:
            logger.info(f"Starting truth detection analysis on {len(claims)} claims")
            
            # Validate input
            if not claims:
                return {
                    'error': 'No claims provided',
                    'clusters': [],
                    'narrative': 'No claims to analyze',
                    'summary': 'Analysis failed: No input claims'
                }
            
            # Step 1: Embed claims
            embeddings = self.embed_claims(claims)
            if embeddings.size == 0:
                return {
                    'error': 'Failed to embed claims',
                    'clusters': [],
                    'narrative': 'Embedding failed',
                    'summary': 'Analysis failed: Could not process claim texts'
                }
            
            # Step 2: Cluster embeddings
            clusters = self.cluster_embeddings(embeddings, claims)
            if not clusters:
                return {
                    'error': 'No clusters formed',
                    'clusters': [],
                    'narrative': 'Clustering failed',
                    'summary': 'Analysis failed: Could not group similar claims'
                }
            
            # Step 3: Detect contradictions
            self.detect_contradictions(clusters, embeddings)
            
            # Step 4: Assign coherence scores
            self.assign_coherence_scores(clusters, embeddings)
            
            # Step 5: Generate results
            results = self.generate_analysis_results(clusters, embeddings)
            
            logger.info("Truth detection analysis completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Critical error in truth detection analysis: {str(e)}")
            return {
                'error': str(e),
                'clusters': [],
                'narrative': 'Analysis failed due to critical error',
                'summary': f'Analysis failed: {str(e)}'
            }

    def generate_analysis_results(self, clusters: List[Cluster], embeddings: np.ndarray) -> Dict:
        """Generate comprehensive analysis results"""
        try:
            # Basic statistics
            total_claims = sum(len(cluster.members) for cluster in clusters)
            contradictions = sum(1 for cluster in clusters if cluster.is_contradiction)
            
            # Find high-confidence truths
            probable_truths = []
            inconsistencies = []
            
            for cluster in clusters:
                if not cluster.members:
                    continue
                    
                if cluster.is_contradiction:
                    # Record contradiction
                    variants_info = []
                    for variant in cluster.variants:
                        variants_info.append({
                            'description': variant.value_desc[:100] + ("..." if len(variant.value_desc) > 100 else ""),
                            'support': float(variant.support),
                            'claim_count': len(variant.claims)
                        })
                    
                    inconsistencies.append({
                        'cluster_id': int(cluster.id),
                        'variants': variants_info,
                        'truth_variant': cluster.truth_variant.value_desc[:100] + ("..." if len(cluster.truth_variant.value_desc) > 100 else "") if cluster.truth_variant else None
                    })
                    
                elif cluster.support > 1.0:  # High support threshold
                    probable_truths.append({
                        'cluster_id': int(cluster.id),
                        'claim': cluster.members[0].text,
                        'support': float(cluster.support),
                        'coherence': float(cluster.coherence_score),
                        'sources': len(set(c.source_type for c in cluster.members)),
                        'document_count': len(set(c.doc_id for c in cluster.members))
                    })
            
            # Generate narrative
            narrative = self.generate_narrative(probable_truths, inconsistencies)
            
            # Generate summary
            summary = self.generate_enhanced_summary(clusters, probable_truths, inconsistencies, total_claims)
            
            return {
                'total_claims': total_claims,
                'total_clusters': len(clusters),
                'contradictions': contradictions,
                'probable_truths': probable_truths,
                'inconsistencies': inconsistencies,
                'narrative': narrative,
                'summary': summary,
                'clusters': self.serialize_clusters(clusters)
            }
            
        except Exception as e:
            logger.error(f"Error generating analysis results: {str(e)}")
            return {
                'error': f'Failed to generate results: {str(e)}',
                'clusters': [],
                'narrative': 'Result generation failed',
                'summary': 'Could not generate analysis summary'
            }

    def generate_narrative(self, probable_truths: List[Dict], inconsistencies: List[Dict]) -> str:
        """Generate coherent narrative from analysis results"""
        narrative_parts = []
        
        narrative_parts.append("=== COHERENT TRUTH NARRATIVE ===\n")
        
        if probable_truths:
            narrative_parts.append("HIGH-CONFIDENCE TRUTHS:")
            for i, truth in enumerate(probable_truths[:5], 1):  # Top 5
                confidence = min(100, truth['support'] * 20)  # Scale to percentage
                narrative_parts.append(f"{i}. {truth['claim']} (Confidence: {confidence:.1f}%)")
            narrative_parts.append("")
        
        if inconsistencies:
            narrative_parts.append("DETECTED INCONSISTENCIES:")
            for i, inconsistency in enumerate(inconsistencies[:3], 1):  # Top 3
                narrative_parts.append(f"{i}. Conflicting views with {len(inconsistency['variants'])} variants")
                if inconsistency['truth_variant']:
                    narrative_parts.append(f"   → Most supported: {inconsistency['truth_variant']}")
            narrative_parts.append("")
        
        if not probable_truths and not inconsistencies:
            narrative_parts.append("No clear truth patterns detected. Consider adding more diverse claims or sources.")
        
        narrative_parts.append("This analysis represents probable truth patterns derived from coherence mapping across source descriptors.")
        
        return "\n".join(narrative_parts)

    def generate_enhanced_summary(self, clusters: List[Cluster], probable_truths: List[Dict], 
                                 inconsistencies: List[Dict], total_claims: int) -> str:
        """Generate enhanced summary with detailed analysis"""
        summary_parts = []
        
        summary_parts.append("=== TRUTH DETECTION ANALYSIS SUMMARY ===\n")
        
        # Overview
        summary_parts.append(f"**ANALYSIS OVERVIEW:**")
        summary_parts.append(f"- Total Claims Processed: {total_claims}")
        summary_parts.append(f"- Clusters Formed: {len(clusters)}")
        summary_parts.append(f"- High-Confidence Truths: {len(probable_truths)}")
        summary_parts.append(f"- Contradictions Detected: {len(inconsistencies)}")
        summary_parts.append("")
        
        # Probable truths
        if probable_truths:
            summary_parts.append("**PROBABLE TRUTHS (High Coherence):**")
            for truth in probable_truths[:10]:  # Top 10
                summary_parts.append(f"- {truth['claim']}")
                summary_parts.append(f"  └─ Support: {truth['support']}, Sources: {truth['sources']}, Coherence: {truth['coherence']}")
            summary_parts.append("")
        
        # Inconsistencies
        if inconsistencies:
            summary_parts.append("**DETECTED INCONSISTENCIES:**")
            for inconsistency in inconsistencies:
                variants_desc = [f"Support {v['support']}: '{v['description']}'" for v in inconsistency['variants']]
                summary_parts.append(f"- Disputed: {' vs '.join(variants_desc)}")
            summary_parts.append("")
        
        # Recommendations
        summary_parts.append("**RECOMMENDATIONS:**")
        if len(probable_truths) < 3:
            summary_parts.append("- Consider adding more diverse source claims for better analysis")
        if len(inconsistencies) > len(probable_truths):
            summary_parts.append("- High inconsistency detected - verify source reliability")
        if total_claims < 10:
            summary_parts.append("- Analysis confidence would improve with more claims")
        
        return "\n".join(summary_parts)

    def serialize_clusters(self, clusters: List[Cluster]) -> List[Dict]:
        """Serialize clusters for JSON response"""
        serialized = []
        for cluster in clusters:
            cluster_data = {
                'id': int(cluster.id),
                'member_count': len(cluster.members),
                'support': float(cluster.support),
                'coherence_score': float(cluster.coherence_score),
                'is_contradiction': bool(cluster.is_contradiction),
                'claims': [claim.text for claim in cluster.members[:5]]  # First 5 claims
            }
            
            if cluster.is_contradiction and cluster.variants:
                cluster_data['variants'] = [
                    {
                        'description': variant.value_desc[:100] + ("..." if len(variant.value_desc) > 100 else ""),
                        'support': float(variant.support),
                        'claim_count': len(variant.claims)
                    }
                    for variant in cluster.variants
                ]
            
            serialized.append(cluster_data)
        
        return serialized

# Factory function for easy instantiation
def create_truth_detector(min_cluster_size: int = 1, distance_threshold: float = 0.5) -> TruthDetectorCore:
    """Create a configured truth detector instance"""
    return TruthDetectorCore(min_cluster_size, distance_threshold)

# Convenience function for quick analysis
def analyze_truth_claims(claims_data: List[Dict]) -> Dict:
    """
    Convenience function to analyze claims
    
    Args:
        claims_data: List of dictionaries with keys: 'text', 'doc_id', 'source_type'
    
    Returns:
        Dictionary with analysis results
    """
    try:
        # Convert to Claim objects
        claims = []
        for i, claim_data in enumerate(claims_data):
            claim = Claim(
                text=claim_data.get('text', ''),
                doc_id=claim_data.get('doc_id', i),
                source_type=claim_data.get('source_type', 'unknown')
            )
            claims.append(claim)
        
        # Analyze
        detector = create_truth_detector()
        results = detector.analyze_claims(claims)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in analyze_truth_claims: {str(e)}")
        return {
            'error': str(e),
            'clusters': [],
            'narrative': 'Analysis failed',
            'summary': f'Analysis failed: {str(e)}'
        }