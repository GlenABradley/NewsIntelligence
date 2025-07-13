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
    
    def __init__(self, min_cluster_size: int = 1, distance_threshold: float = 0.5):
        self.min_cluster_size = min_cluster_size
        self.distance_threshold = distance_threshold
        self.vectorizer = None
        self.embeddings = None
        
    def embed_claims(self, claims: List[Claim]) -> np.ndarray:
        """Enhanced embedding with better preprocessing and error handling"""
        if not claims:
            logger.warning("No claims provided for embedding")
            return np.array([])
        
        try:
            # Enhanced text preprocessing
            enhanced_texts = []
            for claim in claims:
                # Add source type context
                text = f"[{claim.source_type}] {claim.text}" if claim.source_type != "unknown" else claim.text
                enhanced_texts.append(text)
            
            # Initialize TF-IDF with better parameters
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                min_df=1,
                max_df=0.9,
                stop_words='english',
                ngram_range=(1, 2)
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
        """Enhanced clustering with adaptive thresholding"""
        if len(claims) == 0:
            return []
        
        try:
            # Adaptive distance threshold based on data diversity
            unique_sources = len(set(claim.source_type for claim in claims))
            adaptive_threshold = self.distance_threshold + (0.1 * unique_sources / len(claims))
            
            clustering = AgglomerativeClustering(
                n_clusters=None,
                metric='cosine',
                linkage='average',
                distance_threshold=adaptive_threshold
            )
            
            labels = clustering.fit_predict(embeddings)
            
            # Create clusters
            cluster_dict = {}
            for i, label in enumerate(labels):
                if label not in cluster_dict:
                    cluster_dict[label] = Cluster(label, [])
                cluster_dict[label].members.append(claims[i])
                claims[i].cluster_id = label
            
            clusters = list(cluster_dict.values())
            
            # Validate clusters
            valid_clusters = [cluster for cluster in clusters if cluster.validate()]
            
            logger.info(f"Created {len(valid_clusters)} valid clusters from {len(claims)} claims")
            return valid_clusters
            
        except Exception as e:
            logger.error(f"Error in clustering: {str(e)}")
            raise ValueError(f"Failed to cluster embeddings: {str(e)}")

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
                
                # Sub-clustering to find variants
                sub_clustering = AgglomerativeClustering(
                    n_clusters=None,
                    metric='cosine',
                    linkage='average',
                    distance_threshold=0.3
                )
                
                sub_labels = sub_clustering.fit_predict(cluster_emb)
                
                # Group variants
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
                
                # Check for contradictions
                if len(variants) > 1:
                    cluster.is_contradiction = True
                    cluster.variants = []
                    
                    for variant_data in variants.values():
                        variant = Variant(
                            variant_data['value_desc'],
                            variant_data['claims']
                        )
                        variant.calculate_support()
                        cluster.variants.append(variant)
                    
                    # Find truth variant (highest support)
                    if cluster.variants:
                        cluster.truth_variant = max(cluster.variants, key=lambda x: x.support)
                        
                    logger.info(f"Cluster {cluster.id} contains {len(cluster.variants)} contradictory variants")
                    
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