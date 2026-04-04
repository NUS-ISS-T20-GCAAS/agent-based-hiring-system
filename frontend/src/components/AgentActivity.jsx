import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
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

const getTraceEventKey = (item, index) =>
  item?.event_id || `${item?.timestamp || 'trace'}-${item?.direction || 'message'}-${item?.stage || 'stage'}-${index}`;

const getPendingTraceActor = (trace) => {
  if (!Array.isArray(trace) || trace.length === 0) {
    return {
      agent: 'coordinator',
      direction: 'request',
      message: 'Coordinator is waiting for the workflow to begin.',
    };
  }

  const lastEvent = trace[trace.length - 1];
  if (lastEvent.direction === 'request' && lastEvent.to_agent) {
    return {
      agent: lastEvent.to_agent,
      direction: 'response',
      message: `${formatAgentName(lastEvent.to_agent)} is working on the next response.`,
    };
  }

  return {
    agent: 'coordinator',
    direction: 'request',
    message: 'Coordinator is preparing the next handoff.',
  };
};

const isRightAlignedAgent = (agent) => agent && agent !== 'coordinator';

const TraceBubble = ({ children, className }) => {
  const bodyRef = useRef(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEntered, setIsEntered] = useState(false);
  const [isContentVisible, setIsContentVisible] = useState(false);
  const [measuredHeight, setMeasuredHeight] = useState(0);

  useLayoutEffect(() => {
    if (!bodyRef.current) {
      return;
    }

    setMeasuredHeight(bodyRef.current.scrollHeight);
  }, [children]);

  useEffect(() => {
    const expandTimerId = window.setTimeout(() => {
      setIsExpanded(true);
    }, 20);
    const enterTimerId = window.setTimeout(() => {
      setIsEntered(true);
    }, 240);
    const contentTimerId = window.setTimeout(() => {
      setIsContentVisible(true);
    }, 380);

    return () => {
      window.clearTimeout(expandTimerId);
      window.clearTimeout(enterTimerId);
      window.clearTimeout(contentTimerId);
    };
  }, []);

  return (
    <div
      className={`trace-bubble-wrap ${isExpanded ? 'trace-bubble-wrap-open' : 'trace-bubble-wrap-closed'}`}
      style={{ maxHeight: isExpanded ? `${Math.max(measuredHeight + 12, 72)}px` : '0px' }}
    >
      <div
        ref={bodyRef}
        className={`${className} ${isEntered ? 'trace-message-entered' : 'trace-message-entering'} ${
          isContentVisible ? 'trace-message-content-visible' : 'trace-message-content-hidden'
        }`}
      >
        {children}
      </div>
    </div>
  );
};

const AgentActivity = ({ activity, handoffs, isVisible, isRunning, selectedJob, onClear }) => {
  const traceContainerRef = useRef(null);
  const scrollTimerRef = useRef(null);
  const trace = Array.isArray(handoffs) ? handoffs : [];
  const jobActivity = Array.isArray(activity)
    ? activity.filter((item) => !selectedJob || item.entity_id === selectedJob)
    : [];
  const systemEvents = jobActivity.filter((item) => item.event_kind !== 'handoff');
  const pendingActor = getPendingTraceActor(trace);
  const pendingActorStyle = AGENT_STYLES[pendingActor.agent] || {
    accent: 'border-slate-300 bg-slate-50 text-slate-900',
    pill: 'bg-slate-100 text-slate-800 border-slate-200',
  };
  const shouldShowLiveTyping = Boolean(selectedJob) && isRunning;

  useEffect(() => {
    return () => {
      if (scrollTimerRef.current) {
        window.clearTimeout(scrollTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isVisible || !traceContainerRef.current) {
      return;
    }

    const container = traceContainerRef.current;
    const scrollToBottom = () => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      });
    };

    scrollToBottom();
    window.requestAnimationFrame(scrollToBottom);

    if (scrollTimerRef.current) {
      window.clearTimeout(scrollTimerRef.current);
    }

    scrollTimerRef.current = window.setTimeout(scrollToBottom, 420);
  }, [isVisible, selectedJob, trace.length, shouldShowLiveTyping]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Coordinator Orchestration Trace</h2>
          <p className="mt-1 text-sm text-slate-600">
            {selectedJob
              ? `How the coordinator planned and managed workflow execution for job ${selectedJob}`
              : 'Select a job to inspect how the coordinator planned the workflow and delegated work to agents'}
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
              Choose a job from the dashboard or candidates view to inspect the coordinator trace.
            </p>
          </div>
        ) : trace.length === 0 && !shouldShowLiveTyping ? (
          <div className="py-12 text-center">
            <AlertCircle className="mx-auto mb-4 h-16 w-16 text-slate-300" />
            <h3 className="mb-2 text-lg font-semibold text-slate-900">No trace yet</h3>
            <p className="text-slate-600">
              Live coordinator handoffs will appear here once the selected job starts moving through the workflow.
            </p>
          </div>
        ) : (
          <div
            ref={traceContainerRef}
            className={`trace-shell max-h-[70vh] space-y-4 overflow-y-auto rounded-2xl bg-slate-50 p-4 ${
              isVisible ? 'trace-shell-live' : ''
            }`}
          >
            {trace.map((item, index) => {
              const speaker = item.from_agent;
              const speakerStyle = AGENT_STYLES[speaker] || {
                accent: 'border-slate-300 bg-slate-50 text-slate-900',
                pill: 'bg-slate-100 text-slate-800 border-slate-200',
              };
              const previewEntries = Object.entries(item.payload_preview || {}).slice(0, 4);
              const isRightAligned = isRightAlignedAgent(speaker);

              return (
                <div
                  key={getTraceEventKey(item, index)}
                  className={`trace-row flex ${isRightAligned ? 'justify-end' : 'justify-start'}`}
                >
                  <TraceBubble
                    className={`trace-message max-w-[78%] min-w-[18rem] rounded-2xl border p-5 shadow-sm ${speakerStyle.accent} ${
                      isRightAligned ? 'trace-message-response' : 'trace-message-request'
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${speakerStyle.pill}`}>
                        {formatAgentName(item.from_agent)}
                      </span>
                      {item.to_agent && item.to_agent !== item.from_agent && (
                        <>
                          <span className="text-sm text-slate-500">to</span>
                          <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                            {formatAgentName(item.to_agent)}
                          </span>
                        </>
                      )}
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
                  </TraceBubble>
                </div>
              );
            })}

            {shouldShowLiveTyping && (
              <div className={`trace-row flex ${isRightAlignedAgent(pendingActor.agent) ? 'justify-end' : 'justify-start'}`}>
                <TraceBubble
                  className={`trace-message trace-message-typing max-w-[24rem] min-w-[16rem] rounded-2xl border px-4 py-3 shadow-sm ${pendingActorStyle.accent} ${
                    isRightAlignedAgent(pendingActor.agent) ? 'trace-message-response' : 'trace-message-request'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${pendingActorStyle.pill}`}>
                      {formatAgentName(pendingActor.agent)}
                    </span>
                    <span className="trace-typing-dots" aria-hidden="true">
                      <span />
                      <span />
                      <span />
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6">{pendingActor.message}</p>
                </TraceBubble>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Live System Events</h3>
            <p className="mt-1 text-sm text-slate-600">
              Status updates for the selected job that sit outside the coordinator-led orchestration trace
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
