import React from 'react';
import { AlertCircle, Trash2 } from 'lucide-react';
import { formatTime } from '../utils/helpers';

const AgentActivity = ({ activity, onClear }) => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Real-Time Agent Activity</h2>
          <p className="text-sm text-slate-600 mt-1">
            Live updates from all agents in the system
          </p>
        </div>
        {activity.length > 0 && (
          <button
            onClick={onClear}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium text-slate-700 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Clear Log
          </button>
        )}
      </div>

      {/* Activity Log */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        {activity.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 mb-2">No activity yet</h3>
            <p className="text-slate-600">
              Agent activity will appear here when processing resumes
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {activity.map((item, index) => (
              <div 
                key={index} 
                className="flex items-start gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors fade-in"
              >
                {/* Status Indicator */}
                <div className="flex-shrink-0 w-2 h-2 bg-green-500 rounded-full mt-2 animate-pulse" />
                
                {/* Activity Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="font-semibold text-slate-900 capitalize">
                      {item.agent}
                    </span>
                    <span className="text-xs text-slate-500 bg-slate-200 px-2 py-0.5 rounded">
                      {formatTime(item.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm text-slate-700 break-words">{item.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Activity Statistics */}
      {activity.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-bold text-slate-900 mb-4">Activity Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-slate-50 rounded-lg">
              <p className="text-2xl font-bold text-slate-900">{activity.length}</p>
              <p className="text-sm text-slate-600 mt-1">Total Events</p>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">
                {activity.filter(a => a.agent === 'intake').length}
              </p>
              <p className="text-sm text-slate-600 mt-1">Intake Events</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">
                {activity.filter(a => a.agent === 'screening').length}
              </p>
              <p className="text-sm text-slate-600 mt-1">Screening Events</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <p className="text-2xl font-bold text-purple-600">
                {activity.filter(a => a.agent === 'skills').length}
              </p>
              <p className="text-sm text-slate-600 mt-1">Skills Events</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentActivity;