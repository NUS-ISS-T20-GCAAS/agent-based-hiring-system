import React from 'react';
import { Eye, RefreshCw, TrendingUp, FileText, AlertTriangle, Trash2, Loader } from 'lucide-react';
import { getStatusColor, getRecommendationColor, formatPercent, titleCase } from '../utils/helpers.js';

const Candidates = ({
  candidates,
  onViewDetails,
  onRefresh,
  onRankAll,
  onDeleteCandidate,
  queuedUploadsCount,
  processingCandidatesCount,
  isRunning,
  latestActivityMessage,
}) => {
  const isCandidateProfileLoading = (candidate) => (candidate?.name || '').trim().toLowerCase() === 'unknown candidate';
  const hasManualRanking = candidates.some((candidate) => candidate.ranking?.position != null);

  const formatEscalationSource = (source) => {
    const labels = {
      screening: 'Screening',
      audit: 'Audit',
      screening_and_audit: 'Screening + Audit',
      none: 'No Escalation',
    };

    return labels[source] || 'Review';
  };

  const getRankLabel = (candidate, index) => {
    if (candidate.ranking?.position != null) {
      return `#${candidate.ranking.position}`;
    }
    return `#${index + 1}`;
  };

  const statusMatchesRecommendation = (candidate) => {
    const status = String(candidate.status || '').trim().toLowerCase();
    const recommendation = String(candidate.recommendation || '').trim().toUpperCase();

    return (
      (status === 'shortlisted' && recommendation === 'SHORTLIST') ||
      (status === 'rejected' && recommendation === 'REJECT')
    );
  };

  if (candidates.length === 0 && !isRunning) {
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
      {isRunning && (
        <div className="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 to-cyan-50 p-5 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-white p-3 shadow-sm">
              <Loader className="w-5 h-5 text-blue-600 animate-spin" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-slate-900">Job Processing In Progress</h3>
              <p className="mt-1 text-sm text-slate-700">
                {queuedUploadsCount > 0 && processingCandidatesCount > 0
                  ? `${queuedUploadsCount} upload${queuedUploadsCount === 1 ? '' : 's'} queued and ${processingCandidatesCount} candidate${processingCandidatesCount === 1 ? '' : 's'} currently processing.`
                  : queuedUploadsCount > 0
                    ? `${queuedUploadsCount} upload${queuedUploadsCount === 1 ? '' : 's'} queued. Candidate records will appear here shortly.`
                    : `${processingCandidatesCount} candidate${processingCandidatesCount === 1 ? '' : 's'} currently processing through the workflow.`}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                This page updates automatically as intake, screening, and audit complete.
              </p>
              {latestActivityMessage && (
                <p className="mt-3 rounded-lg bg-white/80 px-3 py-2 text-sm text-slate-700 border border-blue-100">
                  Latest update: {latestActivityMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Candidate Rankings</h2>
          <p className="text-sm text-slate-600 mt-1">
            {hasManualRanking
              ? `${candidates.length} candidate${candidates.length !== 1 ? 's' : ''} ordered by manual ranking`
              : `${candidates.length} candidate${candidates.length !== 1 ? 's' : ''} sorted by screening score`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onRankAll}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
          >
            <TrendingUp className="w-4 h-4" />
            Apply Manual Ranking
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

      {candidates.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-blue-100 p-12 text-center">
          <Loader className="w-16 h-16 text-blue-400 mx-auto mb-4 animate-spin" />
          <h3 className="text-lg font-semibold text-slate-900 mb-2">Waiting for candidate records</h3>
          <p className="text-slate-600">
            Uploaded resumes have been accepted and are being processed in the background.
          </p>
        </div>
      ) : (
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
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full text-white font-bold text-lg">
                    {getRankLabel(candidate, index)}
                  </div>
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    {candidate.ranking?.position != null ? 'Manual Rank' : 'Score Order'}
                  </span>
                </div>
                
                {/* Candidate Info */}
                <div>
                  {isCandidateProfileLoading(candidate) ? (
                    <div className="space-y-2">
                      <div className="h-6 w-44 animate-pulse rounded bg-slate-200" />
                      <div className="h-4 w-32 animate-pulse rounded bg-slate-100" />
                      <p className="text-xs font-medium uppercase tracking-wide text-blue-600">
                        Building candidate profile...
                      </p>
                    </div>
                  ) : (
                    <>
                      <h3 className="text-lg font-bold text-slate-900">{candidate.name}</h3>
                      <p className="text-sm text-slate-600">{candidate.email}</p>
                    </>
                  )}
                  
                  {/* Status Badges */}
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusColor(candidate.status)}`}>
                      {titleCase(candidate.status || 'processing')}
                    </span>
                    {!statusMatchesRecommendation(candidate) && (
                      <span className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getRecommendationColor(candidate.recommendation)}`}>
                        {titleCase(candidate.recommendation || 'pending')}
                      </span>
                    )}
                    {candidate.needs_human_review && (
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold border border-amber-300 bg-amber-50 text-amber-800">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Review Required
                      </span>
                    )}
                  </div>
                  {candidate.ranking?.position != null && (
                    <p className="mt-2 text-sm text-slate-600">
                      Manual ranking #{candidate.ranking.position}
                      {candidate.ranking.method ? ` via ${candidate.ranking.method.replaceAll('_', ' ')}` : ''}
                      {candidate.ranking.score != null ? ` with score ${formatPercent(candidate.ranking.score)}` : ''}
                    </p>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onViewDetails(candidate.id)}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium text-slate-700 transition-colors"
                >
                  <Eye className="w-4 h-4" />
                  View Details
                </button>
                <button
                  onClick={() => onDeleteCandidate(candidate)}
                  className="flex items-center gap-2 px-4 py-2 bg-red-50 hover:bg-red-100 rounded-lg text-sm font-medium text-red-700 transition-colors border border-red-200"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
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
              {candidate.needs_human_review && (
                <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
                    <AlertTriangle className="w-4 h-4" />
                    Escalated for human review
                  </div>
                  <p className="mt-1 text-sm text-amber-800">
                    Source: {formatEscalationSource(candidate.escalation_source)}
                  </p>
                  {candidate.review_reasons?.length > 0 && (
                    <p className="mt-1 text-sm text-amber-800">
                      {candidate.review_reasons[0]}
                    </p>
                  )}
                </div>
              )}

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
      )}
    </div>
  );
};

export default Candidates;
