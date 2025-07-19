import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Components
import Dashboard from './components/Dashboard';
import NewsFeed from './components/NewsFeed';
import ReportManager from './components/ReportManager';
import ProcessingStatus from './components/ProcessingStatus';

// Services
import { newsApi } from './services/newsApi';

function App() {
  const [apiStatus, setApiStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchApiStatus();
  }, []);

  const fetchApiStatus = async () => {
    try {
      const status = await newsApi.getStatus();
      setApiStatus(status);
    } catch (error) {
      console.error('Failed to fetch API status:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading News Intelligence Platform...</p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div className="flex items-center">
                <h1 className="text-2xl font-bold text-gray-900">
                  📰 News Intelligence Platform
                </h1>
                <span className="ml-3 px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                  {apiStatus?.status || 'Unknown'}
                </span>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className="text-sm text-gray-500">
                  Next Processing: {apiStatus?.processing?.next_scheduled_run ? 
                    new Date(apiStatus.processing.next_scheduled_run).toLocaleTimeString() : 
                    'Not scheduled'
                  }
                </div>
                
                {apiStatus?.processing?.is_processing && (
                  <div className="flex items-center text-sm text-blue-600">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                    Processing...
                  </div>
                )}
              </div>
            </div>
            
            {/* Navigation */}
            <nav className="flex space-x-8 pb-4">
              <a href="/dashboard" className="text-blue-600 hover:text-blue-800 font-medium">Dashboard</a>
              <a href="/feeds" className="text-gray-600 hover:text-gray-800">Live Feeds</a>
              <a href="/reports" className="text-gray-600 hover:text-gray-800">Reports</a>
              <a href="/processing" className="text-gray-600 hover:text-gray-800">Processing</a>
            </nav>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard apiStatus={apiStatus} />} />
            <Route path="/feeds" element={<NewsFeed />} />
            <Route path="/reports" element={<ReportManager />} />
            <Route path="/processing" element={<ProcessingStatus />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;