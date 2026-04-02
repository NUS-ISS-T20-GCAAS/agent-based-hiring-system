import React, { useEffect, useRef } from 'react';
import { AlertCircle, Trash2 } from 'lucide-react';
import { formatDateTime, formatPercent, titleCase } from '../utils/helpers.js';

const AGENT_STYLES = {
  coordinator: {
    accent: 'border-blue-300 bg-blue-50 text-blue-900',
    pill: 'bg-blue-100 text-blue-800 border-blue-200',
  },
  'resume-intake': {
    accent: 'border-sky-300 bg-sky-50 text-sky-900',
    pill: 'bg-sky-100 text-sky-800 border-sky-200',
  },
  'skill-assessment': {
    accent: 'border-cyan-300 bg-cyan-50 text-cyan-900',
    pill: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  },
  screening: {
    accent: 'border-indigo-300 bg-indigo-50 text-indigo-900',
    pill: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  },
  audit: {
    accent: 'border-emerald-300 bg-emerald-50 text-emerald-900',
    pill: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  },
  ranking: {
    accent: 'border-violet-300 bg-violet-50 text-violet-900',
    pill: 'bg-violet-100 text-violet-800 border-violet-200',
  },
};

const formatAgentName = (value) => titleCase(value || 'unknown');

const formatPreviewLabel = (key) =>
  titleCase(String(key).replace(/_/g, ' '));

const formatPreviewValue = (value) => {
  if (Array.isArray(value)) {
    return value.join(', ');
  }

  if (typeof value === 'number' && value >= 0 && value <= 1) {
    return formatPercent(value);
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (value && typeof value === 'object') {
    return Object.entries(value)
      .map(([key, item]) => `${formatPreviewLabel(key)}: ${formatPreviewValue(item)}`)
      .join(' • ');
  }

  return value == null ? 'N/A' : String(value);
};

const shortId = (value) => {
  if (!value) return null;
  const text = String(value);
  if (text.length <= 12) return text;
  return `${text.slice(0, 8)}...${text.slice(-4)}`;
};

const AgentActivity = ({ activity, handoffs, loading, selectedJob, onClear }) => {
  const traceContainerRef = useRef(null);
  const trace = Array.isArray(handoffs) ? handoffs : [];
  const jobActivity = Array.isArray(activity)
    ? activity.filter((item) => !selectedJob || item.entity_id === selectedJob)
    : [];
  const systemEvents = jobActivity.filter((item) => item.event_kind !== 'handoff');

  useEffect(() => {
    if (!traceContainerRef.current) {
      return;
    }

    traceContainerRef.current.scrollTop = traceContainerRef.current.scrollHeight;
  }, [trace.length, selectedJob]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Agent Handoff Trace</h2>
          <p className="mt-1 text-sm text-slate-600">
            {selectedJob
              ? `Coordinator-mediated conversation for job ${selectedJob}`
              : 'Select a job to inspect how the coordinator routes work between agents'}
          </p>
        </div>
        {systemEvents.length > 0 && (
          <button
            onClick={onClear}
            className="flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200"
          >
            <Trash2 className="h-4 w-4" />
            Clear Live Feed
          </button>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {!selectedJob ? (
          <div className="py-12 text-center">
            <AlertCircle className="mx-auto mb-4 h-16 w-16 text-slate-300" />
            <h3 className="mb-2 text-lg font-semibold text-slate-900">No job selected</h3>
            <p className="text-slate-600">
              Choose a job from the dashboard or candidates view to inspect the handoff conversation.
            </p>
          </div>
        ) : loading ? (
          <div className="py-12 text-center text-slate-600">
            Loading handoff trace for {selectedJob}...
          </div>
        ) : trace.length === 0 ? (
          <div className="py-12 text-center">
            <AlertCircle className="mx-auto mb-4 h-16 w-16 text-slate-300" />
            <h3 className="mb-2 text-lg font-semibold text-slate-900">No trace yet</h3>
            <p className="text-slate-600">
              Handoffs will appear here once the selected job starts moving through the workflow.
            </p>
          </div>
        ) : (
          <div
            ref={traceContainerRef}
            className="max-h-[70vh] space-y-4 overflow-y-auto rounded-2xl bg-slate-50 p-4"
          >
            {trace.map((item) => {
              const speaker = item.from_agent;
              const speakerStyle = AGENT_STYLES[speaker] || {
                accent: 'border-slate-300 bg-slate-50 text-slate-900',
                pill: 'bg-slate-100 text-slate-800 border-slate-200',
              };
              const previewEntries = Object.entries(item.payload_preview || {}).slice(0, 4);

              return (
                <div
                  key={item.event_id || `${item.timestamp}-${item.direction}-${item.stage}`}
                  className={`flex ${item.direction === 'request' ? 'justify-start' : 'justify-end'}`}
                >
                  <div className={`w-full max-w-3xl rounded-2xl border p-5 shadow-sm ${speakerStyle.accent}`}>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${speakerStyle.pill}`}>
                        {formatAgentName(item.from_agent)}
                      </span>
                      <span className="text-sm text-slate-500">to</span>
                      <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                        {formatAgentName(item.to_agent)}
                      </span>
                      <span className="ml-auto text-xs text-slate-500">
                        {formatDateTime(item.timestamp)}
                      </span>
                    </div>

                    <p className="mt-3 text-sm leading-6">{item.message}</p>

                    {previewEntries.length > 0 && (
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        {previewEntries.map(([key, value]) => (
                          <div
                            key={`${item.event_id || item.timestamp}-${key}`}
                            className="rounded-xl border border-white/70 bg-white/80 p-3"
                          >
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                              {formatPreviewLabel(key)}
                            </p>
                            <p className="mt-2 text-sm leading-6 text-slate-800">
                              {formatPreviewValue(value)}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                      <span className="rounded-full bg-white/80 px-3 py-1 font-medium">
                        Stage: {formatAgentName(item.stage)}
                      </span>
                      {item.artifact_type && (
                        <span className="rounded-full bg-white/80 px-3 py-1 font-medium">
                          Artifact: {titleCase(item.artifact_type.replace(/_/g, ' '))}
                        </span>
                      )}
                      {typeof item.confidence === 'number' && (
                        <span className="rounded-full bg-white/80 px-3 py-1 font-medium">
                          Confidence: {formatPercent(item.confidence)}
                        </span>
                      )}
                      {item.candidate_id && (
                        <span className="rounded-full bg-white/80 px-3 py-1 font-medium">
                          Candidate: {shortId(item.candidate_id)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Live System Events</h3>
            <p className="mt-1 text-sm text-slate-600">
              Status updates for the selected job that sit outside the chat-style handoff trace
            </p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
            {systemEvents.length} event{systemEvents.length === 1 ? '' : 's'}
          </span>
        </div>

        {systemEvents.length === 0 ? (
          <div className="py-8 text-center text-slate-600">
            No live status events yet for this job.
          </div>
        ) : (
          <div className="space-y-3">
            {systemEvents.slice(0, 12).map((item, index) => (
              <div
                key={item.event_id || `${item.timestamp}-${index}`}
                className="flex items-start gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4"
              >
                <div className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-green-500" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-900">
                      {formatAgentName(item.agent)}
                    </span>
                    <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-500">
                      {formatDateTime(item.timestamp)}
                    </span>
                  </div>
                  <p className="mt-1 break-words text-sm text-slate-700">{item.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentActivity;
