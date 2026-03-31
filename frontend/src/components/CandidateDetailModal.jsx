import React, { useEffect, useState } from 'react';
import { X, CheckCircle, Loader, AlertTriangle, Trash2 } from 'lucide-react';
import api from '../services/api.js';
import {
  formatTime,
  formatPercent,
  formatDecisionType,
  getDecisionTheme,
  parseDecisionReasoning,
  titleCase,
} from '../utils/helpers.js';

const CandidateDetailModal = ({ candidateId, onClose, onDeleteCandidate }) => {
  const [candidate, setCandidate] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatEscalationSource = (source) => {
    const labels = {
      screening: 'Screening',
      audit: 'Audit',
      screening_and_audit: 'Screening and Audit',
      none: 'No escalation',
    };

    return labels[source] || 'Review';
  };

  const isCandidateProfileLoading = (value) => (value || '').trim().toLowerCase() === 'unknown candidate';

  const formatAgentLabel = (agentId, decisionType) => {
    const labels = {
      'resume-intake-agent': 'Resume Intake Agent',
      'screening-agent': 'Screening Agent',
      'audit-agent': 'Audit Agent',
      'ranking-agent': 'Ranking Agent',
    };

    if (labels[agentId]) {
      return labels[agentId];
    }

    if (agentId && !String(agentId).includes('-')) {
      return titleCase(agentId);
    }

    return formatDecisionType(decisionType);
  };

  const shouldShowAgentLabel = (agentId, decisionType) => {
    const agentLabel = formatAgentLabel(agentId, decisionType).replace(/\s+agent$/i, '').trim().toLowerCase();
    const decisionLabel = formatDecisionType(decisionType).trim().toLowerCase();

    return Boolean(agentLabel) && agentLabel !== decisionLabel;
  };

  useEffect(() => {
    if (candidateId) {
      fetchCandidateDetails();
    }
  }, [candidateId]);

  const fetchCandidateDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [candidateData, decisionsData] = await Promise.all([
        api.getCandidate(candidateId),
        api.getCandidateDecisions(candidateId)
      ]);
      
      setCandidate(candidateData);
      setDecisions(decisionsData);
    } catch (err) {
      console.error('Error fetching candidate details:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!candidate || isDeleting) return;

    setIsDeleting(true);
    try {
      await onDeleteCandidate(candidate);
    } finally {
      setIsDeleting(false);
    }
  };

  if (!candidateId) return null;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-center justify-between z-10">
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader className="w-5 h-5 animate-spin text-slate-400" />
              <span className="text-slate-600">Loading...</span>
            </div>
          ) : candidate ? (
            <div>
              {isCandidateProfileLoading(candidate.name) ? (
                <div className="space-y-2">
                  <div className="h-8 w-56 animate-pulse rounded bg-slate-200" />
                  <div className="h-4 w-36 animate-pulse rounded bg-slate-100" />
                  <p className="text-sm font-medium text-blue-600">Building candidate profile...</p>
                </div>
              ) : (
                <>
                  <h2 className="text-2xl font-bold text-slate-900">{candidate.name}</h2>
                  <p className="text-slate-600">{candidate.email}</p>
                </>
              )}
            </div>
          ) : (
            <div className="text-slate-600">Candidate Details</div>
          )}
          
          <div className="flex items-center gap-2">
            {candidate && !loading && (
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isDeleting ? (
                  <Loader className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
                {isDeleting ? 'Deleting...' : 'Delete Candidate'}
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X className="w-6 h-6 text-slate-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600 mb-2">Error loading candidate details</p>
              <p className="text-sm text-slate-600">{error}</p>
              <button
                onClick={fetchCandidateDetails}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : candidate ? (
            <>
              {/* Candidate Snapshot */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Candidate Snapshot</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Current Status</p>
                    <p className="mt-2 text-base font-semibold text-slate-900 capitalize">{candidate.status}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Recommendation: <span className="font-medium text-slate-900">{titleCase(candidate.recommendation || 'pending')}</span>
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Review Workflow</p>
                    <p className="mt-2 text-base font-semibold text-slate-900">
                      {candidate.needs_human_review ? 'Escalated for review' : 'No review required'}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      Source: <span className="font-medium text-slate-900">{formatEscalationSource(candidate.escalation_source)}</span>
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Candidate Profile</p>
                    <p className="mt-2 text-base font-semibold text-slate-900">{candidate.skills?.length || 0} skill{candidate.skills?.length === 1 ? '' : 's'} identified</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Email: <span className="font-medium text-slate-900">{candidate.email || 'Not available'}</span>
                    </p>
                  </div>
                  <div className={`rounded-xl border p-4 ${
                    candidate.ranking?.position != null
                      ? 'border-violet-200 bg-violet-50'
                      : 'border-slate-200 bg-slate-50'
                  }`}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Manual Ranking</p>
                    <p className="mt-2 text-base font-semibold text-slate-900">
                      {candidate.ranking?.position != null ? `Ranked #${candidate.ranking.position}` : 'Not manually ranked'}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      {candidate.ranking?.score != null
                        ? `Ranking score ${formatPercent(candidate.ranking.score)}`
                        : 'Currently ordered by screening score'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Performance Scores */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Performance Scores</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-3xl font-bold text-blue-600">
                      {formatPercent(candidate.scores?.qualification || 0)}
                    </p>
                    <p className="text-sm text-slate-600 mt-1">Qualification</p>
                  </div>
                  <div className="text-center p-4 bg-purple-50 rounded-lg border border-purple-200">
                    <p className="text-3xl font-bold text-purple-600">
                      {formatPercent(candidate.scores?.skills || 0)}
                    </p>
                    <p className="text-sm text-slate-600 mt-1">Skills</p>
                  </div>
                  <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg border border-purple-200">
                    <p className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                      {formatPercent(candidate.scores?.composite || 0)}
                    </p>
                    <p className="text-sm text-slate-600 mt-1">Composite</p>
                  </div>
                </div>
              </div>

              {/* Skills */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {candidate.skills && candidate.skills.length > 0 ? (
                    candidate.skills.map(skill => (
                      <span 
                        key={skill} 
                        className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium border border-blue-200"
                      >
                        {skill}
                      </span>
                    ))
                  ) : (
                    <p className="text-slate-500 italic">No skills listed</p>
                  )}
                </div>
              </div>

              {/* Manual Ranking */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Manual Ranking</h3>
                <div className={`rounded-xl border p-4 ${
                  candidate.ranking?.position != null
                    ? 'border-violet-200 bg-violet-50'
                    : 'border-slate-200 bg-slate-50'
                }`}>
                  {candidate.ranking?.position != null ? (
                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-violet-900">
                        Ranked #{candidate.ranking.position}
                      </p>
                      <p className="text-sm text-violet-800">
                        Manual reranking keeps screening and audit decisions unchanged.
                      </p>
                      {candidate.ranking.method && (
                        <p className="text-sm text-violet-800">
                          Method: {candidate.ranking.method.replaceAll('_', ' ')}
                        </p>
                      )}
                      {candidate.ranking.score != null && (
                        <p className="text-sm text-violet-800">
                          Ranking score: {formatPercent(candidate.ranking.score)}
                        </p>
                      )}
                      {candidate.ranking.ranked_at && (
                        <p className="text-sm text-violet-800">
                          Ranked at: {formatTime(candidate.ranking.ranked_at)}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-sm font-semibold text-slate-900">
                        No manual ranking applied
                      </p>
                      <p className="text-sm text-slate-600">
                        This candidate is currently ordered by screening score only.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Review Status */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Review Status</h3>
                <div className={`rounded-xl border p-4 ${
                  candidate.needs_human_review
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-emerald-200 bg-emerald-50'
                }`}>
                  <div className="flex items-start gap-3">
                    {candidate.needs_human_review ? (
                      <AlertTriangle className="mt-0.5 w-5 h-5 text-amber-700 flex-shrink-0" />
                    ) : (
                      <CheckCircle className="mt-0.5 w-5 h-5 text-emerald-700 flex-shrink-0" />
                    )}
                    <div className="space-y-2">
                      <p className={`text-sm font-semibold ${
                        candidate.needs_human_review ? 'text-amber-900' : 'text-emerald-900'
                      }`}>
                        {candidate.needs_human_review ? 'Human review required' : 'No human review required'}
                      </p>
                      <p className={`text-sm ${
                        candidate.needs_human_review ? 'text-amber-800' : 'text-emerald-800'
                      }`}>
                        Status: {candidate.review_status?.replace('_', ' ')}
                      </p>
                      <p className={`text-sm ${
                        candidate.needs_human_review ? 'text-amber-800' : 'text-emerald-800'
                      }`}>
                        Source: {formatEscalationSource(candidate.escalation_source)}
                      </p>
                      {candidate.review_reasons?.length > 0 && (
                        <div>
                          <p className={`text-sm font-medium ${
                            candidate.needs_human_review ? 'text-amber-900' : 'text-emerald-900'
                          }`}>
                            Review reasons
                          </p>
                          <ul className={`mt-2 list-disc pl-5 text-sm space-y-1 ${
                            candidate.needs_human_review ? 'text-amber-800' : 'text-emerald-800'
                          }`}>
                            {candidate.review_reasons.map(reason => (
                              <li key={reason}>{reason}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Decision Trail */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Agent Decision Trail</h3>
                {decisions && decisions.length > 0 ? (
                  <div className="space-y-3">
                    {decisions.map((decision, index) => {
                      const theme = getDecisionTheme(decision.decision_type);
                      const parsed = parseDecisionReasoning(decision.reasoning);

                      return (
                        <div
                          key={decision.decision_id || index}
                          className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm border-l-4 ${theme.border}`}
                        >
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div className="space-y-3">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${theme.badge}`}>
                                  {formatDecisionType(decision.decision_type)}
                                </span>
                                {shouldShowAgentLabel(decision.agent_id, decision.decision_type) && (
                                  <span className="text-sm font-semibold text-slate-900">
                                    {formatAgentLabel(decision.agent_id, decision.decision_type)}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm leading-6 text-slate-700">
                                {parsed.summary}
                              </p>
                            </div>
                            <div className="flex items-center gap-3 md:flex-col md:items-end">
                              <span className="text-xs text-slate-500">
                                {formatTime(decision.timestamp)}
                              </span>
                              <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${theme.chip}`}>
                                Confidence {formatPercent(decision.confidence)}
                              </span>
                            </div>
                          </div>

                          {parsed.highlights.length > 0 && (
                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                              {parsed.highlights.map((highlight) => (
                                <div
                                  key={`${decision.decision_id || index}-${highlight.label}`}
                                  className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                                >
                                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    {highlight.label}
                                  </p>
                                  {highlight.kind === 'list' ? (
                                    <div className="mt-2 flex flex-wrap gap-2">
                                      {highlight.items.length > 0 ? (
                                        highlight.items.map((item) => (
                                          <span
                                            key={item}
                                            className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${theme.chip}`}
                                          >
                                            {item}
                                          </span>
                                        ))
                                      ) : (
                                        <span className="text-sm text-slate-500">None listed</span>
                                      )}
                                    </div>
                                  ) : (
                                    <p className="mt-2 text-sm leading-6 text-slate-700">
                                      {highlight.value}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}

                          {parsed.analysis && (
                            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Analysis
                              </p>
                              <p className="mt-2 text-sm leading-6 text-slate-700">
                                {parsed.analysis}
                              </p>
                            </div>
                          )}

                          <div className="mt-4 flex items-center gap-3">
                            <CheckCircle className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            <div className="flex-1 bg-slate-200 rounded-full h-2">
                              <div
                                className="h-2 rounded-full bg-slate-900 transition-all duration-500"
                                style={{ width: `${(decision.confidence || 0) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs font-semibold text-slate-700 min-w-[3rem] text-right">
                              {formatPercent(decision.confidence)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 bg-slate-50 rounded-lg">
                    <p className="text-slate-600">No decision trail available</p>
                  </div>
                )}
              </div>

              {/* Contact Info */}
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-4">Contact Information</h3>
                <div className="bg-slate-50 rounded-lg p-4 space-y-2">
                  <div>
                    <span className="text-sm font-medium text-slate-600">Email: </span>
                    <span className="text-sm text-slate-900">{candidate.email}</span>
                  </div>
                  {candidate.phone && (
                    <div>
                      <span className="text-sm font-medium text-slate-600">Phone: </span>
                      <span className="text-sm text-slate-900">{candidate.phone}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-sm font-medium text-slate-600">Status: </span>
                    <span className="text-sm text-slate-900 capitalize">{candidate.status}</span>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-slate-600">Recommendation: </span>
                    <span className={`text-sm font-semibold ${
                      candidate.recommendation === 'SHORTLIST' ? 'text-green-600' :
                      candidate.recommendation === 'CONSIDER' ? 'text-yellow-600' :
                      candidate.recommendation === 'REJECT' ? 'text-red-600' :
                      'text-gray-600'
                    }`}>
                      {candidate.recommendation || 'PENDING'}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-slate-600">Review status: </span>
                    <span className="text-sm text-slate-900">{titleCase(candidate.review_status || 'not_required')}</span>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default CandidateDetailModal;
