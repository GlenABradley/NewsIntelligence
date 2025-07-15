import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TruthDetector = () => {
  const [claims, setClaims] = useState([{ text: "", source_type: "unknown" }]);
  const [urls, setUrls] = useState([{ url: "", source_type: "news" }]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("input");
  const [inputMode, setInputMode] = useState("text"); // "text" or "url"
  const [analysisMode, setAnalysisMode] = useState("dual_pipeline"); // "dual_pipeline" or "original"

  const addClaim = () => {
    setClaims([...claims, { text: "", source_type: "unknown" }]);
  };

  const addUrl = () => {
    setUrls([...urls, { url: "", source_type: "news" }]);
  };

  const removeUrl = (index) => {
    if (urls.length > 1) {
      setUrls(urls.filter((_, i) => i !== index));
    }
  };

  const updateUrl = (index, field, value) => {
    const newUrls = [...urls];
    newUrls[index][field] = value;
    setUrls(newUrls);
  };

  const analyzeUrls = async () => {
    setLoading(true);
    setError(null);
    try {
      const validUrls = urls.filter(url => url.url.trim() !== "");
      if (validUrls.length === 0) {
        setError("Please add at least one URL");
        setLoading(false);
        return;
      }

      const endpoint = analysisMode === "dual_pipeline" ? "analyze-urls-dual-pipeline" : "analyze-urls";
      const response = await axios.post(`${API}/${endpoint}`, {
        urls: validUrls
      });
      
      setResults(response.data);
      setActiveTab("results");
    } catch (err) {
      console.error("URL analysis error:", err);
      setError(err.response?.data?.detail || err.message || "Failed to analyze URLs");
    } finally {
      setLoading(false);
    }
  };

  const extractUrlPreview = async (url) => {
    try {
      const response = await axios.post(`${API}/extract-url`, {
        url: url,
        source_type: "news"
      });
      return response.data;
    } catch (err) {
      console.error("URL extraction error:", err);
      return null;
    }
  };

  const removeClaim = (index) => {
    if (claims.length > 1) {
      setClaims(claims.filter((_, i) => i !== index));
    }
  };

  const updateClaim = (index, field, value) => {
    const newClaims = [...claims];
    newClaims[index][field] = value;
    setClaims(newClaims);
  };

  const runDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = analysisMode === "dual_pipeline" ? "dual-pipeline-demo" : "truth-demo";
      const response = await axios.post(`${API}/${endpoint}`);
      setResults(response.data.results);
      setActiveTab("results");
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to run demo");
    } finally {
      setLoading(false);
    }
  };

  const analyzeClaims = async () => {
    setLoading(true);
    setError(null);
    try {
      const validClaims = claims.filter(claim => claim.text.trim() !== "");
      if (validClaims.length === 0) {
        setError("Please add at least one claim");
        setLoading(false);
        return;
      }

      // Allow single claims with a warning
      if (validClaims.length === 1) {
        console.log("Single claim analysis - limited functionality");
      }

      const endpoint = analysisMode === "dual_pipeline" ? "dual-pipeline-analyze" : "truth-analyze";
      const response = await axios.post(`${API}/${endpoint}`, {
        claims: validClaims
      });
      
      setResults(response.data);
      setActiveTab("results");
    } catch (err) {
      console.error("Analysis error:", err);
      setError(err.response?.data?.detail || err.message || "Failed to analyze claims");
    } finally {
      setLoading(false);
    }
  };

  const sourceTypes = [
    "unknown", "science", "medical", "news", "social_media", "expert", 
    "government", "academic", "conspiracy", "opinion", "witness", "historical"
  ];

  const DualPipelineResultsView = ({ results }) => {
    if (!results) return null;

    const { 
      total_claims, 
      factual_claims, 
      emotional_claims, 
      factual_loci, 
      emotional_variants, 
      fair_witness_narrative, 
      dual_pipeline_summary, 
      processing_details 
    } = results;

    return (
      <div className="space-y-6">
        {/* Dual Pipeline Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{total_claims}</div>
            <div className="text-sm text-gray-600">Total Claims</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{factual_claims}</div>
            <div className="text-sm text-gray-600">Factual Claims</div>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">{emotional_claims}</div>
            <div className="text-sm text-gray-600">Emotional Claims</div>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">{factual_loci}</div>
            <div className="text-sm text-gray-600">Factual Loci</div>
          </div>
          <div className="bg-pink-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-pink-600">{emotional_variants}</div>
            <div className="text-sm text-gray-600">Emotional Variants</div>
          </div>
        </div>

        {/* Fair Witness Narrative */}
        <div className="bg-gray-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4 flex items-center">
            <span className="mr-2">👁️</span>
            Fair Witness Narrative
          </h3>
          <pre className="whitespace-pre-wrap text-sm font-mono bg-white p-4 rounded border">{fair_witness_narrative}</pre>
        </div>

        {/* Dual Pipeline Summary */}
        <div className="bg-blue-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4 text-blue-800">Dual Pipeline Summary</h3>
          <pre className="whitespace-pre-wrap text-sm bg-white p-4 rounded border">{dual_pipeline_summary}</pre>
        </div>

        {/* Processing Details */}
        {processing_details && (
          <div className="bg-gray-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold mb-4">Processing Details</h3>
            
            {/* Claim Separation Details */}
            {processing_details.claim_separation && (
              <div className="mb-6">
                <h4 className="text-md font-medium mb-3 text-green-700">Claim Separation Analysis</h4>
                <div className="bg-white p-4 rounded border">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <span className="text-sm font-medium">Factual Percentage: </span>
                      <span className="text-green-600 font-bold">
                        {processing_details.claim_separation.separation_summary?.factual_percentage?.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-sm font-medium">Emotional Percentage: </span>
                      <span className="text-purple-600 font-bold">
                        {processing_details.claim_separation.separation_summary?.emotional_percentage?.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                  
                  {/* Factual Samples */}
                  {processing_details.claim_separation.factual_samples && (
                    <div className="mb-4">
                      <h5 className="text-sm font-medium mb-2 text-green-700">Factual Claim Samples:</h5>
                      <div className="space-y-2">
                        {processing_details.claim_separation.factual_samples.map((sample, index) => (
                          <div key={index} className="bg-green-50 p-3 rounded border-l-4 border-green-500">
                            <div className="text-sm font-medium">{sample.text}</div>
                            <div className="text-xs text-gray-600 mt-1">
                              Source: {sample.source_type} | 
                              Factual Text: {sample.factual_text} | 
                              Sentiment: {sample.sentiment_score?.vader_compound?.toFixed(3)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Emotional Samples */}
                  {processing_details.claim_separation.emotional_samples && (
                    <div>
                      <h5 className="text-sm font-medium mb-2 text-purple-700">Emotional Claim Samples:</h5>
                      <div className="space-y-2">
                        {processing_details.claim_separation.emotional_samples.map((sample, index) => (
                          <div key={index} className="bg-purple-50 p-3 rounded border-l-4 border-purple-500">
                            <div className="text-sm font-medium">{sample.text}</div>
                            <div className="text-xs text-gray-600 mt-1">
                              Source: {sample.source_type} | 
                              Emotional Text: {sample.emotional_text} | 
                              Sentiment: {sample.sentiment_score?.vader_compound?.toFixed(3)} | 
                              Descriptors: {sample.emotional_descriptors?.join(', ') || 'None'}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Factual Pipeline Details */}
            {processing_details.factual_pipeline && (
              <div className="mb-6">
                <h4 className="text-md font-medium mb-3 text-green-700">Factual Pipeline (Higgs Substrate)</h4>
                <div className="bg-white p-4 rounded border">
                  <div className="space-y-3">
                    {processing_details.factual_pipeline.map((locus, index) => (
                      <div key={index} className="bg-green-50 p-3 rounded border-l-4 border-green-500">
                        <div className="text-sm font-medium">{locus.truth_value}</div>
                        <div className="text-xs text-gray-600 mt-1">
                          Support Mass: {locus.support_mass?.toFixed(2)} | 
                          Coherence: {locus.coherence_score?.toFixed(3)} | 
                          Sources: {locus.source_diversity} | 
                          Claims: {locus.claim_count}
                        </div>
                        
                        {/* Emotional Overlays */}
                        {locus.emotional_overlays && locus.emotional_overlays.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs font-medium text-purple-700 mb-1">Emotional Overlays:</div>
                            <div className="space-y-1">
                              {locus.emotional_overlays.map((overlay, oIndex) => (
                                <div key={oIndex} className="bg-purple-100 p-2 rounded text-xs">
                                  <span className="font-medium">{overlay.emotion_type}</span>: 
                                  Intensity {overlay.intensity?.toFixed(1)}/10, 
                                  Prevalence {(overlay.prevalence * 100)?.toFixed(1)}%
                                  {overlay.descriptors && overlay.descriptors.length > 0 && (
                                    <span className="text-gray-600"> ({overlay.descriptors.join(', ')})</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Emotional Pipeline Details */}
            {processing_details.emotional_pipeline && (
              <div>
                <h4 className="text-md font-medium mb-3 text-purple-700">Emotional Pipeline (KNN Clustering)</h4>
                <div className="bg-white p-4 rounded border">
                  <div className="space-y-3">
                    {processing_details.emotional_pipeline.map((variant, index) => (
                      <div key={index} className="bg-purple-50 p-3 rounded border-l-4 border-purple-500">
                        <div className="text-sm font-medium capitalize">{variant.emotion_type} Variant</div>
                        <div className="text-xs text-gray-600 mt-1">
                          Intensity: {variant.intensity?.toFixed(1)}/10 | 
                          Prevalence: {(variant.prevalence * 100)?.toFixed(1)}% | 
                          Claims: {variant.claim_count}
                        </div>
                        
                        {/* Emotional Descriptors */}
                        {variant.descriptors && variant.descriptors.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs font-medium text-purple-700 mb-1">Descriptors:</div>
                            <div className="flex flex-wrap gap-1">
                              {variant.descriptors.map((descriptor, dIndex) => (
                                <span key={dIndex} className="bg-purple-200 text-purple-800 px-2 py-1 rounded text-xs">
                                  {descriptor}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Linked Factual Loci */}
                        {variant.linked_factual_loci && variant.linked_factual_loci.length > 0 && (
                          <div className="mt-2">
                            <div className="text-xs font-medium text-green-700 mb-1">Linked to Factual Loci:</div>
                            <div className="text-xs text-gray-600">
                              {variant.linked_factual_loci.join(', ')}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const ResultsView = ({ results }) => {
    if (!results) return null;

    const { probable_truths, inconsistencies, narrative, summary, total_claims, total_clusters, contradictions } = results;

    return (
      <div className="space-y-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{total_claims}</div>
            <div className="text-sm text-gray-600">Total Claims</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{total_clusters}</div>
            <div className="text-sm text-gray-600">Clusters</div>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">{probable_truths.length}</div>
            <div className="text-sm text-gray-600">Probable Truths</div>
          </div>
          <div className="bg-red-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-red-600">{contradictions}</div>
            <div className="text-sm text-gray-600">Contradictions</div>
          </div>
        </div>

        {/* Narrative */}
        <div className="bg-gray-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Coherent Narrative</h3>
          <pre className="whitespace-pre-wrap text-sm">{narrative}</pre>
        </div>

        {/* Probable Truths */}
        {probable_truths.length > 0 && (
          <div className="bg-green-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold mb-4 text-green-800">High-Confidence Truths</h3>
            <div className="space-y-3">
              {probable_truths.map((truth, index) => (
                <div key={index} className="bg-white p-4 rounded border-l-4 border-green-500">
                  <div className="font-medium">{truth.claim}</div>
                  <div className="text-sm text-gray-600 mt-2">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 mr-2">
                      Support: {truth.support.toFixed(1)}
                    </span>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800 mr-2">
                      Coherence: {truth.coherence.toFixed(3)}
                    </span>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">
                      {truth.sources} sources
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Inconsistencies */}
        {inconsistencies && inconsistencies.length > 0 && (
          <div className="bg-red-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold mb-4 text-red-800">Detected Inconsistencies</h3>
            <div className="space-y-3">
              {inconsistencies.map((inconsistency, index) => (
                <div key={index} className="bg-white p-4 rounded border-l-4 border-red-500">
                  <div className="font-medium text-red-800 mb-2">Conflicting Claims</div>
                  <div className="space-y-2">
                    {inconsistency.variants && inconsistency.variants.map((variant, vIndex) => (
                      <div key={vIndex} className="text-sm">
                        <span className="font-medium">{variant.description}</span>
                        <span className="ml-2 text-gray-600">(Support: {variant.support ? variant.support.toFixed(1) : 'N/A'})</span>
                      </div>
                    ))}
                  </div>
                  {inconsistency.truth_variant && (
                    <div className="mt-2 text-sm text-green-700">
                      <strong>Most Supported:</strong> {inconsistency.truth_variant}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Full Summary */}
        <div className="bg-gray-50 p-6 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Detailed Analysis Summary</h3>
          <pre className="whitespace-pre-wrap text-sm">{summary}</pre>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Truth Detector</h1>
          <p className="text-lg text-gray-600">
            Analyze claims using advanced coherence mapping and contradiction detection
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 mb-6">
          <button
            onClick={() => setActiveTab("input")}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === "input"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
          >
            Input Claims
          </button>
          <button
            onClick={() => setActiveTab("results")}
            className={`px-4 py-2 rounded-lg font-medium ${
              activeTab === "results"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50"
            }`}
            disabled={!results}
          >
            Results
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="text-red-800">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          {activeTab === "input" && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-semibold">Add Content</h2>
                <div className="flex space-x-4">
                  <button
                    onClick={runDemo}
                    disabled={loading}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg hover:bg-purple-600 disabled:opacity-50"
                  >
                    {loading ? "Running..." : "Run Demo"}
                  </button>
                </div>
              </div>

              {/* Input Mode Toggle */}
              <div className="flex space-x-1 mb-6 bg-gray-100 p-1 rounded-lg">
                <button
                  onClick={() => setInputMode("text")}
                  className={`px-4 py-2 rounded-md font-medium transition-all ${
                    inputMode === "text"
                      ? "bg-blue-500 text-white shadow-md"
                      : "bg-transparent text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  📝 Text Input
                </button>
                <button
                  onClick={() => setInputMode("url")}
                  className={`px-4 py-2 rounded-md font-medium transition-all ${
                    inputMode === "url"
                      ? "bg-blue-500 text-white shadow-md"
                      : "bg-transparent text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  🔗 URL Input
                </button>
              </div>

              {/* Text Input Mode */}
              {inputMode === "text" && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Manual Text Input</h3>
                  {claims.map((claim, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <label className="text-sm font-medium text-gray-700">
                          Claim {index + 1}
                        </label>
                        {claims.length > 1 && (
                          <button
                            onClick={() => removeClaim(index)}
                            className="text-red-500 hover:text-red-700"
                          >
                            ×
                          </button>
                        )}
                      </div>
                      <textarea
                        value={claim.text}
                        onChange={(e) => updateClaim(index, "text", e.target.value)}
                        placeholder="Enter your claim here... (up to 7000 characters)"
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        rows="4"
                      />
                      <div className="mt-2 text-sm text-gray-500">
                        {claim.text.length}/7000 characters
                      </div>
                      <div className="mt-2">
                        <label className="text-sm font-medium text-gray-700 block mb-1">
                          Source Type
                        </label>
                        <select
                          value={claim.source_type}
                          onChange={(e) => updateClaim(index, "source_type", e.target.value)}
                          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          {sourceTypes.map(type => (
                            <option key={type} value={type}>
                              {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))}
                  
                  <div className="flex justify-between">
                    <button
                      onClick={addClaim}
                      className="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
                    >
                      Add Another Claim
                    </button>
                    <button
                      onClick={analyzeClaims}
                      disabled={loading}
                      className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                    >
                      {loading ? "Analyzing..." : "Analyze Claims"}
                    </button>
                  </div>
                </div>
              )}

              {/* URL Input Mode */}
              {inputMode === "url" && (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">URL-Based Input</h3>
                  <p className="text-sm text-gray-600">
                    Add URLs to automatically extract and analyze article content. Perfect for news articles, blog posts, and web content.
                  </p>
                  
                  {urls.map((urlInput, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <label className="text-sm font-medium text-gray-700">
                          URL {index + 1}
                        </label>
                        {urls.length > 1 && (
                          <button
                            onClick={() => removeUrl(index)}
                            className="text-red-500 hover:text-red-700"
                          >
                            ×
                          </button>
                        )}
                      </div>
                      <input
                        type="url"
                        value={urlInput.url}
                        onChange={(e) => updateUrl(index, "url", e.target.value)}
                        placeholder="https://example.com/article"
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <div className="mt-2">
                        <label className="text-sm font-medium text-gray-700 block mb-1">
                          Source Type
                        </label>
                        <select
                          value={urlInput.source_type}
                          onChange={(e) => updateUrl(index, "source_type", e.target.value)}
                          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          {sourceTypes.map(type => (
                            <option key={type} value={type}>
                              {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))}
                  
                  <div className="flex justify-between">
                    <button
                      onClick={addUrl}
                      className="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
                    >
                      Add Another URL
                    </button>
                    <button
                      onClick={analyzeUrls}
                      disabled={loading}
                      className="bg-green-500 text-white px-6 py-2 rounded-lg hover:bg-green-600 disabled:opacity-50"
                    >
                      {loading ? "Extracting & Analyzing..." : "Analyze URLs"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "results" && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold">Analysis Results</h2>
                <button
                  onClick={() => setActiveTab("input")}
                  className="bg-gray-500 text-white px-4 py-2 rounded-lg hover:bg-gray-600"
                >
                  Back to Input
                </button>
              </div>
              <ResultsView results={results} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const Home = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Truth Detector
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Advanced coherence mapping and contradiction detection system to find truth patterns in conflicting claims
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-8 mb-12">
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-xl font-semibold mb-4">How It Works</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• Input multiple claims from different sources</li>
                <li>• Advanced TF-IDF vectorization and clustering</li>
                <li>• Physics-inspired coherence analysis</li>
                <li>• Contradiction detection with variant analysis</li>
                <li>• Generate coherent narratives from chaos</li>
              </ul>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-lg">
              <h3 className="text-xl font-semibold mb-4">Key Features</h3>
              <ul className="space-y-2 text-gray-600">
                <li>• Higgs field substrate modeling</li>
                <li>• Source diversity weighting</li>
                <li>• Coherence heat mapping</li>
                <li>• Medial axis skeletonization</li>
                <li>• Empirical truth validation</li>
              </ul>
            </div>
          </div>

          <div className="text-center">
            <a
              href="/truth-detector"
              className="bg-blue-500 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-blue-600 transition-colors"
            >
              Start Truth Detection
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/truth-detector" element={<TruthDetector />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;