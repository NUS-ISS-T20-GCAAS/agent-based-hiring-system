import React from 'react';
import { Eye, RefreshCw, TrendingUp, FileText } from 'lucide-react';
import { getStatusColor, getRecommendationColor, formatPercent } from '../utils/helpers.js';

const Candidates = ({ candidates, onViewDetails, onRefresh, onRankAll }) => {
  if (candidates.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-slate-900">Candidate Rankings</h2>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
          <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No candidates yet</h3>
          <p className="text-slate-600 mb-4">Upload resumes from the Dashboard to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Candidate Rankings</h2>
          <p className="text-sm text-slate-600 mt-1">
            {candidates.length} candidate{candidates.length !== 1 ? 's' : ''} sorted by composite score
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onRankAll}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
          >
            <TrendingUp className="w-4 h-4" />
            Re-rank All
          </button>
          <button
            onClick={onRefresh}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5 text-slate-600" />
          </button>
        </div>
      </div>

      {/* Candidates List */}
      <div className="space-y-4">
        {candidates.map((candidate, index) => (
          <div 
            key={candidate.id} 
            className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow fade-in"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-4">
                {/* Rank Badge */}
                <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full text-white font-bold text-lg flex-shrink-0">
                  #{index + 1}
                </div>
                
                {/* Candidate Info */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900">{candidate.name}</h3>
                  <p className="text-sm text-slate-600">{candidate.email}</p>
                  
                  {/* Status Badges */}
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusColor(candidate.status)}`}>
                      {candidate.status?.toUpperCase()}
                    </span>
                    <span className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getRecommendationColor(candidate.recommendation)}`}>
                      {candidate.recommendation}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* View Details Button */}
              <button
                onClick={() => onViewDetails(candidate.id)}
                className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium text-slate-700 transition-colors"
              >
                <Eye className="w-4 h-4" />
                View Details
              </button>
            </div>

            {/* Score Bars */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              {/* Qualification Score */}
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs font-medium text-slate-600 mb-1">Qualification Score</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(candidate.scores?.qualification || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold text-slate-900 min-w-[3rem] text-right">
                    {formatPercent(candidate.scores?.qualification || 0)}
                  </span>
                </div>
              </div>

              {/* Skills Proficiency */}
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs font-medium text-slate-600 mb-1">Skills Proficiency</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(candidate.scores?.skills || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold text-slate-900 min-w-[3rem] text-right">
                    {formatPercent(candidate.scores?.skills || 0)}
                  </span>
                </div>
              </div>

              {/* Composite Score */}
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs font-medium text-slate-600 mb-1">Composite Score</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${(candidate.scores?.composite || 0) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold text-slate-900 min-w-[3rem] text-right">
                    {formatPercent(candidate.scores?.composite || 0)}
                  </span>
                </div>
              </div>
            </div>

            {/* Skills Tags */}
            <div>
              <p className="text-xs font-medium text-slate-600 mb-2">Skills</p>
              <div className="flex flex-wrap gap-2">
                {candidate.skills?.length > 0 ? (
                  candidate.skills.map(skill => (
                    <span 
                      key={skill} 
                      className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium border border-blue-200"
                    >
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-slate-500 italic">No skills listed</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Candidates;