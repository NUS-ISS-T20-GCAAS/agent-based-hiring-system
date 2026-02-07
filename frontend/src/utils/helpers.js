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