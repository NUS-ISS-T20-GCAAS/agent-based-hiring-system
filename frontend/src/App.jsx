import React, { useState, useEffect, useRef } from 'react';
import { Activity, BarChart3, Users, Clock } from 'lucide-react';
import Dashboard from './components/Dashboard.jsx';
import Candidates from './components/Candidates.jsx';
import AgentActivity from './components/AgentActivity.jsx';
import CandidateDetailModal from './components/CandidateDetailModal.jsx';
import api from './services/api.js';
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
  const [jobRunState, setJobRunState] = useState({});
  
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);
  const selectedJobRef = useRef(null);

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
    selectedJobRef.current = selectedJob;
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
            const { entity_id: jobId, message: activityMessage, timestamp } = message.data || {};
            if (jobId) {
              setJobRunState((prev) => {
                const current = prev[jobId] || {};
                let queuedUploads = current.queuedUploads || 0;
                if (typeof activityMessage === 'string' && activityMessage.startsWith('Queued upload failed') && queuedUploads > 0) {
                  queuedUploads -= 1;
                }

                return {
                  ...prev,
                  [jobId]: {
                    ...current,
                    queuedUploads,
                    lastActivityMessage: activityMessage || current.lastActivityMessage,
                    lastUpdatedAt: timestamp || new Date().toISOString(),
                  },
                };
              });
            }
          } else if (message.type === 'candidate_update') {
            const { job_id: jobId, status } = message.data || {};
            if (jobId) {
              setJobRunState((prev) => {
                const current = prev[jobId];
                if (!current) return prev;

                let queuedUploads = current.queuedUploads || 0;
                if (status === 'processing' && queuedUploads > 0) {
                  queuedUploads -= 1;
                }

                return {
                  ...prev,
                  [jobId]: {
                    ...current,
                    queuedUploads,
                    lastEventStatus: status || current.lastEventStatus,
                    lastUpdatedAt: new Date().toISOString(),
                  },
                };
              });
            }
            fetchCandidates(jobId);
            fetchStats(jobId);
            fetchJobs();
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

  const fetchCandidates = async (jobId = selectedJob) => {
    if (!jobId) return;
    
    try {
      const data = await api.getCandidates(jobId);
      if (jobId === selectedJobRef.current) {
        setCandidates(data);
        const processingCount = data.filter(
          (candidate) => candidate.status?.toLowerCase() === 'processing'
        ).length;
        if (data.length > 0 && processingCount === 0) {
          setJobRunState((prev) => {
            const current = prev[jobId];
            if (!current || (current.queuedUploads || 0) === 0) {
              return prev;
            }

            return {
              ...prev,
              [jobId]: {
                ...current,
                queuedUploads: 0,
                lastActivityMessage: current.lastActivityMessage || 'Processing completed',
                lastEventStatus: 'completed',
                lastUpdatedAt: new Date().toISOString(),
              },
            };
          });
        }
      }
    } catch (error) {
      console.error('Error fetching candidates:', error);
    }
  };

  const fetchStats = async (jobId = selectedJob) => {
    if (!jobId) return;
    
    try {
      const data = await api.getStats(jobId);
      if (jobId === selectedJobRef.current) {
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Event handlers
  const handleCreateJob = async (jobData) => {
    try {
      await api.createJob(jobData);
      
      await fetchJobs();
      setSelectedJob(jobData.job_id);
      return jobData.job_id;
    } catch (error) {
      console.error('Error creating job:', error);
      alert('Failed to create job: ' + error.message);
      throw error;
    }
  };

  const handleUploadFiles = async (files) => {
    if (!files || files.length === 0 || !selectedJob) return;
    
    setProcessing(true);
    
    try {
      const filesArray = Array.from(files);
      const result = await api.uploadResumes(filesArray, selectedJob);
      setJobRunState((prev) => ({
        ...prev,
        [selectedJob]: {
          queuedUploads: (prev[selectedJob]?.queuedUploads || 0) + (result?.queued || 0),
          lastQueuedAt: new Date().toISOString(),
          lastSubmittedFiles: result?.results?.map((item) => item.file).filter(Boolean) || [],
          lastActivityMessage: `Queued ${result?.queued || 0} upload${(result?.queued || 0) === 1 ? '' : 's'} for processing`,
        },
      }));
      await Promise.all([fetchCandidates(), fetchStats()]);
      setActiveTab('candidates');

      if ((result?.failed || 0) > 0) {
        alert(`Queued ${result.queued || 0} file(s). ${result.failed} file(s) failed validation.`);
      }
    } catch (error) {
      console.error('Error uploading files:', error);
      alert('Upload failed: ' + error.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleRankCandidates = async () => {
    if (!selectedJob) return;
    
    try {
      await api.rankCandidates(selectedJob);
      await fetchCandidates();
    } catch (error) {
      console.error('Error ranking candidates:', error);
      alert('Ranking failed: ' + error.message);
    }
  };

  const handleViewDetails = (candidateId) => {
    setSelectedCandidate(candidateId);
  };

  const handleDeleteCandidate = async (candidate) => {
    if (!candidate?.id) return;

    const candidateName = candidate.name || 'this candidate';
    const confirmed = window.confirm(`Delete ${candidateName}? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      await api.deleteCandidate(candidate.id);
      if (selectedCandidate === candidate.id) {
        setSelectedCandidate(null);
      }
      await Promise.all([fetchCandidates(), fetchStats(), fetchJobs()]);
    } catch (error) {
      console.error('Error deleting candidate:', error);
      alert('Delete failed: ' + error.message);
    }
  };

  const handleCloseModal = () => {
    setSelectedCandidate(null);
  };

  const handleClearActivity = () => {
    setAgentActivity([]);
  };

  const selectedJobRunState = selectedJob ? (jobRunState[selectedJob] || null) : null;
  const processingCandidatesCount = candidates.filter(
    (candidate) => candidate.status?.toLowerCase() === 'processing'
  ).length;
  const queuedUploadsCount = selectedJobRunState?.queuedUploads || 0;
  const selectedJobIsRunning = queuedUploadsCount > 0 || processingCandidatesCount > 0;

  useEffect(() => {
    if (!selectedJob || !selectedJobIsRunning) {
      return undefined;
    }

    const intervalId = setInterval(() => {
      fetchCandidates(selectedJob);
      fetchStats(selectedJob);
      fetchJobs();
    }, 2000);

    return () => clearInterval(intervalId);
  }, [selectedJob, selectedJobIsRunning]);

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
            processing={processing || selectedJobIsRunning}
            fileInputRef={fileInputRef}
          />
        )}

        {activeTab === 'candidates' && (
          <Candidates
            candidates={candidates}
            onViewDetails={handleViewDetails}
            onRefresh={fetchCandidates}
            onRankAll={handleRankCandidates}
            onDeleteCandidate={handleDeleteCandidate}
            queuedUploadsCount={queuedUploadsCount}
            processingCandidatesCount={processingCandidatesCount}
            isRunning={selectedJobIsRunning}
            latestActivityMessage={selectedJobRunState?.lastActivityMessage || null}
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
          onDeleteCandidate={handleDeleteCandidate}
        />
      )}
    </div>
  );
}

export default App;
