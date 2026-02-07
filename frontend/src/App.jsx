import React, { useState, useEffect, useRef } from 'react';
import { Activity, BarChart3, Users, Clock } from 'lucide-react';
import Dashboard from './components/Dashboard';
import Candidates from './components/Candidates';
import AgentActivity from './components/AgentActivity';
import CandidateDetailModal from './components/CandidateDetailModal';
import api from './services/api';
import './App.css';

// WebSocket URL
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

function App() {
  // State management
  const [activeTab, setActiveTab] = useState('dashboard');
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [agentActivity, setAgentActivity] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [stats, setStats] = useState({
    total_candidates: 0,
    shortlisted: 0,
    rejected: 0,
    avg_score: 0,
    pass_rate: 0
  });
  const [isConnected, setIsConnected] = useState(false);
  
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);

  // Initialize on mount
  useEffect(() => {
    connectWebSocket();
    fetchJobs();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Fetch candidates and stats when job changes
  useEffect(() => {
    if (selectedJob) {
      fetchCandidates();
      fetchStats();
    }
  }, [selectedJob]);

  // WebSocket connection
  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'agent_activity') {
            setAgentActivity(prev => [message.data, ...prev.slice(0, 49)]);
          } else if (message.type === 'candidate_update') {
            fetchCandidates();
            fetchStats();
          }
        } catch (err) {
          console.error('WebSocket message error:', err);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      setIsConnected(false);
      setTimeout(connectWebSocket, 3000);
    }
  };

  // API calls
  const fetchJobs = async () => {
    try {
      const data = await api.getJobs();
      setJobs(data);
      
      if (data.length > 0 && !selectedJob) {
        setSelectedJob(data[0].job_id);
      }
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const fetchCandidates = async () => {
    if (!selectedJob) return;
    
    try {
      const data = await api.getCandidates(selectedJob);
      setCandidates(data);
    } catch (error) {
      console.error('Error fetching candidates:', error);
    }
  };

  const fetchStats = async () => {
    if (!selectedJob) return;
    
    try {
      const data = await api.getStats(selectedJob);
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Event handlers
  const handleCreateJob = async () => {
    try {
      await api.createJob({
        title: 'Senior Python Developer',
        required_skills: ['Python', 'SQL', 'AWS'],
        preferred_skills: ['Machine Learning', 'Leadership'],
        min_years_experience: 5,
        education_level: "Bachelor's",
        description: 'Senior developer position requiring strong Python skills and cloud experience'
      });
      
      await fetchJobs();
    } catch (error) {
      console.error('Error creating job:', error);
      alert('Failed to create job: ' + error.message);
    }
  };

  const handleUploadFiles = async (files) => {
    if (!files || files.length === 0 || !selectedJob) return;
    
    setProcessing(true);
    
    try {
      const filesArray = Array.from(files);
      await api.uploadResumes(filesArray, selectedJob);
      
      // Wait a bit for processing to complete
      setTimeout(async () => {
        await fetchCandidates();
        await fetchStats();
        setProcessing(false);
        setActiveTab('candidates');
      }, 3000);
      
    } catch (error) {
      console.error('Error uploading files:', error);
      alert('Upload failed: ' + error.message);
      setProcessing(false);
    }
  };

  const handleRankCandidates = async () => {
    if (!selectedJob) return;
    
    try {
      await api.rankCandidates(selectedJob);
      
      setTimeout(async () => {
        await fetchCandidates();
      }, 1000);
    } catch (error) {
      console.error('Error ranking candidates:', error);
      alert('Ranking failed: ' + error.message);
    }
  };

  const handleViewDetails = (candidateId) => {
    setSelectedCandidate(candidateId);
  };

  const handleCloseModal = () => {
    setSelectedCandidate(null);
  };

  const handleClearActivity = () => {
    setAgentActivity([]);
  };

  // Tab navigation
  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'candidates', label: 'Candidates', icon: Users },
    { id: 'agents', label: 'Agent Activity', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  Multi-Agent Hiring System
                </h1>
                <p className="text-sm text-slate-600">
                  AI-Powered Resume Screening & Candidate Evaluation
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                isConnected ? 'bg-green-50' : 'bg-red-50'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`} />
                <span className={`text-sm font-medium ${
                  isConnected ? 'text-green-900' : 'text-red-900'
                }`}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {processing && (
                <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-lg">
                  <Clock className="w-4 h-4 text-blue-600 animate-spin" />
                  <span className="text-sm font-medium text-blue-900">Processing...</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'dashboard' && (
          <Dashboard
            stats={stats}
            jobs={jobs}
            selectedJob={selectedJob}
            onJobSelect={setSelectedJob}
            onCreateJob={handleCreateJob}
            onUploadFiles={handleUploadFiles}
            processing={processing}
            fileInputRef={fileInputRef}
          />
        )}

        {activeTab === 'candidates' && (
          <Candidates
            candidates={candidates}
            onViewDetails={handleViewDetails}
            onRefresh={fetchCandidates}
            onRankAll={handleRankCandidates}
          />
        )}

        {activeTab === 'agents' && (
          <AgentActivity
            activity={agentActivity}
            onClear={handleClearActivity}
          />
        )}
      </main>

      {/* Candidate Detail Modal */}
      {selectedCandidate && (
        <CandidateDetailModal
          candidateId={selectedCandidate}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}

export default App;