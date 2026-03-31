import React, { useEffect, useState } from 'react';
import { X, CheckCircle, Loader, AlertTriangle, Trash2 } from 'lucide-react';
import api from '../services/api.js';
import { formatTime, formatPercent } from '../utils/helpers.js';

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
              <h2 className="text-2xl font-bold text-slate-900">{candidate.name}</h2>
              <p className="text-slate-600">{candidate.email}</p>
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
                    {decisions.map((decision, index) => (
                      <div 
                        key={decision.decision_id || index} 
                        className="bg-slate-50 rounded-lg p-4 border-l-4 border-blue-500"
                      >
                        {/* Decision Header */}
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0" />
                            <span className="font-semibold text-slate-900">
                              {decision.agent_id}
                            </span>
                          </div>
                          <span className="text-xs text-slate-500">
                            {formatTime(decision.timestamp)}
                          </span>
                        </div>
                        
                        {/* Decision Content */}
                        <div className="ml-7">
                          <p className="text-sm font-medium text-blue-600 mb-1">
                            {decision.decision_type}
                          </p>
                          <p className="text-sm text-slate-700 mb-2">
                            {decision.reasoning}
                          </p>
                          
                          {/* Confidence Bar */}
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">Confidence:</span>
                            <div className="flex-1 max-w-xs bg-slate-200 rounded-full h-1.5">
                              <div
                                className="bg-blue-600 h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${decision.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-xs font-semibold text-slate-700">
                              {formatPercent(decision.confidence)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
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
