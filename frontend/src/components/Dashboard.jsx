import React from 'react';
import { Upload, Users, CheckCircle, XCircle, TrendingUp, Plus, RefreshCw } from 'lucide-react';
import StatsCard from './StatsCard';
import { formatPercent } from '../utils/helpers';

const Dashboard = ({ 
  stats, 
  jobs, 
  selectedJob, 
  onJobSelect, 
  onCreateJob, 
  onUploadFiles, 
  processing,
  fileInputRef 
}) => {
  const agents = [
    { id: 'intake', name: 'Resume Intake', icon: Upload },
    { id: 'screening', name: 'Qualification Screening', icon: CheckCircle },
    { id: 'skills', name: 'Skills Assessment', icon: TrendingUp },
    { id: 'ranking', name: 'Ranking & Recommendation', icon: Users }
  ];

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUploadFiles(files);
    }
  };

  return (
    <div className="space-y-6">
      {/* Job Selection Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900">Select Job Position</h3>
          <button
            onClick={onCreateJob}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Sample Job
          </button>
        </div>
        
        {jobs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {jobs.map(job => (
              <div
                key={job.job_id}
                onClick={() => onJobSelect(job.job_id)}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedJob === job.job_id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-900 mb-1">{job.title}</h4>
                    <p className="text-sm text-slate-600 mb-2">
                      {job.candidates_count || 0} candidate{job.candidates_count !== 1 ? 's' : ''}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {job.required_skills?.slice(0, 3).map(skill => (
                        <span 
                          key={skill} 
                          className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium"
                        >
                          {skill}
                        </span>
                      ))}
                      {job.required_skills?.length > 3 && (
                        <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs">
                          +{job.required_skills.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                  {selectedJob === job.job_id && (
                    <div className="ml-2">
                      <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 bg-slate-50 rounded-lg">
            <p className="text-slate-600 mb-4">No jobs available. Create a sample job to get started.</p>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatsCard
          title="Total Candidates"
          value={stats.total_candidates}
          icon={Users}
          color="blue"
        />
        <StatsCard
          title="Shortlisted"
          value={stats.shortlisted}
          icon={CheckCircle}
          color="green"
        />
        <StatsCard
          title="Rejected"
          value={stats.rejected}
          icon={XCircle}
          color="red"
        />
        <StatsCard
          title="Avg Score"
          value={formatPercent(stats.avg_score)}
          icon={TrendingUp}
          color="purple"
        />
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <div className="text-center max-w-xl mx-auto">
          <div className="inline-flex p-4 bg-blue-50 rounded-full mb-4">
            <Upload className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Upload Resumes</h2>
          <p className="text-slate-600 mb-6">
            Our multi-agent system will automatically screen, assess, and rank candidates
          </p>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={processing || !selectedJob}
            className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
          >
            {processing ? 'Processing...' : 'Select Files to Upload'}
          </button>
          
          <p className="text-sm text-slate-500 mt-4">
            {selectedJob 
              ? 'Supports PDF, DOCX, and TXT files (max 10MB each)' 
              : 'Please select a job first'
            }
          </p>
        </div>
      </div>

      {/* Agent Status */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900">Agent Status</h3>
          <button
            onClick={() => window.location.reload()}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-slate-600" />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map(agent => (
            <div 
              key={agent.id} 
              className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200"
            >
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <agent.icon className="w-6 h-6 text-slate-700" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-slate-900">{agent.name}</p>
                <p className="text-sm text-slate-600">
                  {processing ? 'Active' : 'Ready'}
                </p>
              </div>
              <div className={`w-3 h-3 rounded-full ${
                processing ? 'bg-green-500 animate-pulse' : 'bg-slate-300'
              }`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;