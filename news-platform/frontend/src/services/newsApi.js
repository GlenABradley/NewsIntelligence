import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unknown error occurred';
    throw new Error(message);
  }
);

export const newsApi = {
  // System status
  async getStatus() {
    return api.get('/api/news/');
  },

  async getHealth() {
    return api.get('/health');
  },

  // News processing
  async pollFeeds() {
    return api.post('/api/news/poll-feeds');
  },

  async clusterArticles(timeframeHours = 24) {
    return api.post(`/api/news/cluster-articles?timeframe_hours=${timeframeHours}`);
  },

  async assessImpact(timeframeHours = 24, topN = 25) {
    return api.post(`/api/news/assess-impact?timeframe_hours=${timeframeHours}&top_n=${topN}`);
  },

  async triggerProcessing() {
    return api.post('/api/news/trigger-processing');
  },

  async cancelProcessing() {
    return api.post('/api/news/cancel-processing');
  },

  async getProcessingStatus() {
    return api.get('/api/news/processing-status');
  },

  // Configuration
  async getFeedsConfig() {
    return api.get('/api/news/feeds-config');
  },

  async testExtraction(url) {
    return api.get(`/api/news/test-extraction?url=${encodeURIComponent(url)}`);
  },

  async getRecentArticles(hours = 24, limit = 50, source = null) {
    let url = `/api/news/recent-articles?hours=${hours}&limit=${limit}`;
    if (source) {
      url += `&source=${encodeURIComponent(source)}`;
    }
    return api.get(url);
  },
};

export const reportsApi = {
  // Report management
  async getReportsStatus() {
    return api.get('/api/reports/');
  },

  async getDailyReports(date) {
    return api.get(`/api/reports/daily/${date}`);
  },

  async downloadReport(date, storyId, fileType) {
    return api.get(`/api/reports/download/${date}/${storyId}/${fileType}`, {
      responseType: 'blob',
    });
  },

  async getDailySummary(date) {
    return api.get(`/api/reports/summary/${date}`, {
      responseType: 'blob',
    });
  },

  async listReportDates(limit = 30) {
    return api.get(`/api/reports/list-dates?limit=${limit}`);
  },

  async previewStoryReport(date, storyId) {
    return api.get(`/api/reports/story-preview/${date}/${storyId}`);
  },

  async searchReports(query, startDate = null, endDate = null, limit = 20) {
    let url = `/api/reports/search?query=${encodeURIComponent(query)}&limit=${limit}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    return api.get(url);
  },

  async getReportStats() {
    return api.get('/api/reports/stats');
  },
};

export default { newsApi, reportsApi };