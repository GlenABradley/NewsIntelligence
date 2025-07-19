import React, { useState, useEffect } from 'react';
import { newsApi } from '../services/newsApi';

const Dashboard = ({ apiStatus }) => {
  const [stats, setStats] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [recentActivity, setRecentActivity] = useState([]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch processing status
      const processingStatus = await newsApi.getProcessingStatus();
      setProcessing(processingStatus.is_processing);
      
      // Fetch recent articles (last 6 hours for demo)
      const recentArticles = await newsApi.getRecentArticles(6, 10);
      setRecentActivity(recentArticles.articles || []);
      
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  const triggerManualProcessing = async () => {
    try {
      const result = await newsApi.triggerProcessing();
      alert(`Processing started! Job ID: ${result.job_id}`);
      fetchDashboardData(); // Refresh data
    } catch (error) {
      alert(`Failed to start processing: ${error.message}`);
    }
  };

  const testFeedPolling = async () => {
    try {
      const result = await newsApi.pollFeeds();
      alert(`Feed polling complete! Collected ${result.articles_collected} articles from ${result.sources.length} sources.`);
    } catch (error) {
      alert(`Feed polling failed: ${error.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Dashboard</h2>
        
        {/* Status Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-blue-600">System Status</h3>
            <p className="text-2xl font-bold text-blue-900">{apiStatus?.status || 'Unknown'}</p>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-green-600">Feed Sources</h3>
            <p className="text-2xl font-bold text-green-900">10 Active</p>
          </div>
          
          <div className="bg-yellow-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-yellow-600">Processing</h3>
            <p className="text-2xl font-bold text-yellow-900">
              {processing ? 'Running' : 'Idle'}
            </p>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-purple-600">Daily Schedule</h3>
            <p className="text-2xl font-bold text-purple-900">12:00 PM EST</p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={triggerManualProcessing}
            disabled={processing}
            className={`p-4 rounded-lg border-2 border-dashed text-center transition-colors ${
              processing 
                ? 'border-gray-300 text-gray-400 cursor-not-allowed' 
                : 'border-blue-300 text-blue-600 hover:border-blue-400 hover:bg-blue-50'
            }`}
          >
            <div className="text-lg font-semibold">
              {processing ? 'Processing...' : 'Trigger Manual Processing'}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {processing ? 'Please wait for current processing to complete' : 'Start full news analysis cycle'}
            </div>
          </button>

          <button
            onClick={testFeedPolling}
            className="p-4 rounded-lg border-2 border-dashed border-green-300 text-green-600 hover:border-green-400 hover:bg-green-50 text-center transition-colors"
          >
            <div className="text-lg font-semibold">Test Feed Polling</div>
            <div className="text-sm text-gray-500 mt-1">Poll all RSS feeds now</div>
          </button>

          <div className="p-4 rounded-lg border-2 border-dashed border-gray-300 text-gray-600 text-center">
            <div className="text-lg font-semibold">View Reports</div>
            <div className="text-sm text-gray-500 mt-1">Access generated reports</div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent News Activity</h3>
        
        {recentActivity.length > 0 ? (
          <div className="space-y-3">
            {recentActivity.map((article, index) => (
              <div key={index} className="border-l-4 border-blue-400 pl-4 py-2">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{article.title}</h4>
                    <div className="text-sm text-gray-500 mt-1">
                      <span className="font-medium">{article.source}</span>
                      <span className="mx-2">•</span>
                      <span>{article.perspective}</span>
                      <span className="mx-2">•</span>
                      <span>{new Date(article.published_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                  <div className="ml-4 text-right">
                    <div className="text-sm text-gray-500">Impact Score</div>
                    <div className="font-bold text-blue-600">
                      {article.impact_score ? article.impact_score.toFixed(1) : 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>No recent activity to display</p>
            <p className="text-sm mt-1">Try triggering manual processing or feed polling</p>
          </div>
        )}
      </div>

      {/* System Information */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Information</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Features Status</h4>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Feed Polling</span>
                <span className="text-green-600 font-medium">✓ Active</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Story Clustering</span>
                <span className="text-yellow-600 font-medium">⚠ Placeholder Ready</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Impact Assessment</span>
                <span className="text-yellow-600 font-medium">⚠ Placeholder Ready</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Dual Pipeline</span>
                <span className="text-green-600 font-medium">✓ Active</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Report Generation</span>
                <span className="text-green-600 font-medium">✓ Active</span>
              </div>
            </div>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Configuration</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Timezone</span>
                <span className="text-gray-900">America/New_York</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Daily Processing</span>
                <span className="text-gray-900">12:00 PM EST</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Top Stories Count</span>
                <span className="text-gray-900">25</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Max Articles/Story</span>
                <span className="text-gray-900">50</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;