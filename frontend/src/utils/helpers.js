/**
 * Helper utility functions
 */

/**
 * Format date/time strings
 */
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const formatTime = (dateString) => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

export const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  
  return `${formatDate(dateString)} ${formatTime(dateString)}`;
};

/**
 * Format percentage scores
 */
export const formatPercent = (value, decimals = 0) => {
  if (value === null || value === undefined) return '0%';
  return `${(value * 100).toFixed(decimals)}%`;
};

export const titleCase = (value) => {
  if (!value) return '';

  return String(value)
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

export const formatDecisionType = (decisionType) => {
  const labels = {
    resume_intake_result: 'Resume Intake',
    skill_assessment_result: 'Skill Assessment',
    qualification_screening_result: 'Qualification Screening',
    audit_bias_check_result: 'Audit Review',
    candidate_ranking_result: 'Manual Ranking',
  };

  return labels[decisionType] || titleCase(decisionType);
};

export const getDecisionTheme = (decisionType) => {
  const themes = {
    resume_intake_result: {
      border: 'border-sky-500',
      badge: 'bg-sky-50 text-sky-700 border-sky-200',
      chip: 'bg-sky-50 text-sky-700 border-sky-200',
    },
    skill_assessment_result: {
      border: 'border-cyan-500',
      badge: 'bg-cyan-50 text-cyan-700 border-cyan-200',
      chip: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    },
    qualification_screening_result: {
      border: 'border-blue-500',
      badge: 'bg-blue-50 text-blue-700 border-blue-200',
      chip: 'bg-blue-50 text-blue-700 border-blue-200',
    },
    audit_bias_check_result: {
      border: 'border-emerald-500',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      chip: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    },
    candidate_ranking_result: {
      border: 'border-violet-500',
      badge: 'bg-violet-50 text-violet-700 border-violet-200',
      chip: 'bg-violet-50 text-violet-700 border-violet-200',
    },
  };

  return themes[decisionType] || {
    border: 'border-slate-400',
    badge: 'bg-slate-50 text-slate-700 border-slate-200',
    chip: 'bg-slate-50 text-slate-700 border-slate-200',
  };
};

const splitItems = (value) =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

export const parseDecisionReasoning = (reasoning) => {
  if (!reasoning) {
    return {
      summary: 'No reasoning provided.',
      highlights: [],
      analysis: null,
    };
  }

  const normalized = String(reasoning)
    .replace(/\s*\|\s*/g, '. ')
    .replace(/\s+/g, ' ')
    .trim();

  const sections = normalized
    .split(/(?<=[.])\s+(?=[A-Z])/)
    .map((section) => section.trim())
    .filter(Boolean);

  let summary = sections[0] || normalized;
  let analysis = null;
  const highlights = [];

  sections.slice(1).forEach((section) => {
    const cleanSection = section.replace(/\.$/, '').trim();
    const lowerSection = cleanSection.toLowerCase();

    if (lowerSection.startsWith('analysis:')) {
      analysis = cleanSection.slice(cleanSection.indexOf(':') + 1).trim();
      return;
    }

    const colonIndex = cleanSection.indexOf(':');
    if (colonIndex !== -1) {
      const label = cleanSection.slice(0, colonIndex).trim();
      const value = cleanSection.slice(colonIndex + 1).trim();
      const lowerLabel = label.toLowerCase();

      if (['matched skills', 'missing skills', 'bias flags', 'recommended next steps', 'review reasons', 'skills'].includes(lowerLabel)) {
        highlights.push({
          label,
          kind: 'list',
          items: splitItems(value.replace(/;\s*/g, ',')),
        });
        return;
      }

      highlights.push({
        label,
        kind: 'text',
        value,
      });
      return;
    }

    if (lowerSection.startsWith('human review')) {
      highlights.push({
        label: 'Review',
        kind: 'text',
        value: cleanSection,
      });
      return;
    }

    if (!analysis) {
      analysis = cleanSection;
    }
  });

  if (!analysis && sections.length === 1) {
    analysis = null;
  }

  if (summary.endsWith('.')) {
    summary = summary.slice(0, -1);
  }

  return {
    summary,
    highlights,
    analysis,
  };
};

/**
 * Get status color classes
 */
export const getStatusColor = (status) => {
  const colors = {
    received: 'bg-blue-100 text-blue-800 border-blue-200',
    processing: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    screened: 'bg-green-100 text-green-800 border-green-200',
    rejected: 'bg-red-100 text-red-800 border-red-200',
    shortlisted: 'bg-purple-100 text-purple-800 border-purple-200',
  };
  return colors[status?.toLowerCase()] || 'bg-gray-100 text-gray-800 border-gray-200';
};

/**
 * Get recommendation color classes
 */
export const getRecommendationColor = (recommendation) => {
  const colors = {
    SHORTLIST: 'text-green-700 bg-green-50 border-green-300',
    CONSIDER: 'text-yellow-700 bg-yellow-50 border-yellow-300',
    REJECT: 'text-red-700 bg-red-50 border-red-300',
    PENDING: 'text-gray-700 bg-gray-50 border-gray-300',
  };
  return colors[recommendation] || colors.PENDING;
};

/**
 * Truncate text with ellipsis
 */
export const truncate = (text, maxLength = 100) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};

/**
 * Validate email format
 */
export const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Format file size
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

/**
 * Debounce function
 */
export const debounce = (func, wait) => {
  let timeout;
  
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Download data as JSON file
 */
export const downloadJSON = (data, filename = 'data.json') => {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json'
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Download data as CSV file
 */
export const downloadCSV = (data, filename = 'data.csv') => {
  if (!data || data.length === 0) return;
  
  // Get headers from first object
  const headers = Object.keys(data[0]);
  
  // Create CSV content
  const csvContent = [
    headers.join(','),
    ...data.map(row => 
      headers.map(header => {
        const value = row[header];
        // Escape quotes and wrap in quotes if contains comma
        const stringValue = String(value || '');
        return stringValue.includes(',') 
          ? `"${stringValue.replace(/"/g, '""')}"` 
          : stringValue;
      }).join(',')
    )
  ].join('\n');
  
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Copy text to clipboard
 */
export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Failed to copy:', err);
    return false;
  }
};

/**
 * Calculate time ago
 */
export const timeAgo = (dateString) => {
  if (!dateString) return 'Unknown';
  
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  
  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60,
    second: 1
  };
  
  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return `${interval} ${unit}${interval === 1 ? '' : 's'} ago`;
    }
  }
  
  return 'just now';
};
