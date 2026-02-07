/**
 * API Service Layer
 * Handles all HTTP requests to the backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // ========== JOB ENDPOINTS ==========

  /**
   * Get all jobs
   */
  async getJobs() {
    return this.request('/api/jobs');
  }

  /**
   * Get single job by ID
   */
  async getJob(jobId) {
    return this.request(`/api/jobs/${jobId}`);
  }

  /**
   * Create new job
   */
  async createJob(jobData) {
    return this.request('/api/jobs', {
      method: 'POST',
      body: JSON.stringify(jobData),
    });
  }

  // ========== CANDIDATE ENDPOINTS ==========

  /**
   * Get all candidates (optionally filtered by job)
   */
  async getCandidates(jobId = null) {
    const endpoint = jobId ? `/api/candidates?job_id=${jobId}` : '/api/candidates';
    return this.request(endpoint);
  }

  /**
   * Get single candidate by ID
   */
  async getCandidate(candidateId) {
    return this.request(`/api/candidates/${candidateId}`);
  }

  /**
   * Upload single resume
   */
  async uploadResume(file, jobId) {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseUrl}/api/candidates/upload?job_id=${jobId}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }

  /**
   * Batch upload multiple resumes
   */
  async uploadResumes(files, jobId) {
    const formData = new FormData();
    
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    const url = `${this.baseUrl}/api/candidates/batch-upload?job_id=${jobId}`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Batch upload failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Batch upload error:', error);
      throw error;
    }
  }

  /**
   * Get candidate decision trail
   */
  async getCandidateDecisions(candidateId) {
    return this.request(`/api/candidates/${candidateId}/decisions`);
  }

  /**
   * Delete candidate
   */
  async deleteCandidate(candidateId) {
    return this.request(`/api/candidates/${candidateId}`, {
      method: 'DELETE',
    });
  }

  // ========== RANKING ENDPOINTS ==========

  /**
   * Trigger ranking for all candidates in a job
   */
  async rankCandidates(jobId) {
    return this.request(`/api/jobs/${jobId}/rank`, {
      method: 'POST',
    });
  }

  // ========== STATISTICS ENDPOINTS ==========

  /**
   * Get statistics (optionally for specific job)
   */
  async getStats(jobId = null) {
    const endpoint = jobId ? `/api/stats?job_id=${jobId}` : '/api/stats';
    return this.request(endpoint);
  }

  /**
   * Get bias check report
   */
  async getBiasCheck(jobId) {
    return this.request(`/api/audit/bias-check?job_id=${jobId}`);
  }

  // ========== AGENT ENDPOINTS ==========

  /**
   * Get agent status
   */
  async getAgentStatus() {
    return this.request('/api/agents/status');
  }
}

// Export singleton instance
export default new ApiService();