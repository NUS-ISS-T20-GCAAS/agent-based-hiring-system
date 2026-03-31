import React, { useState } from 'react';
import { Upload, Users, CheckCircle, XCircle, TrendingUp, Plus, RefreshCw } from 'lucide-react';
import StatsCard from './StatsCard.jsx';
import { formatPercent } from '../utils/helpers.js';

const EMPTY_JOB_FORM = {
  title: '',
  jobId: '',
  jobDescription: '',
  requiredSkills: '',
  preferredSkills: '',
  minYearsExperience: '',
  educationLevel: '',
};

const parseSkillInput = (value) =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

const slugifyValue = (value) => {
  const slug = value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

  return slug || 'job';
};

const Dashboard = ({ 
  stats, 
  jobs, 
  selectedJob, 
  onJobSelect, 
  onCreateJob, 
  onUploadFiles, 
  processing,
  fileInputRef 
}) => {
  const agents = [
    { id: 'intake', name: 'Resume Intake', icon: Upload },
    { id: 'screening', name: 'Qualification Screening', icon: CheckCircle },
    { id: 'skills', name: 'Skills Assessment', icon: TrendingUp },
    { id: 'ranking', name: 'Ranking & Recommendation', icon: Users }
  ];
  const [jobForm, setJobForm] = useState(EMPTY_JOB_FORM);
  const [isSubmittingJob, setIsSubmittingJob] = useState(false);
  const [isJobModalOpen, setIsJobModalOpen] = useState(false);

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUploadFiles(files);
    }
  };

  const handleJobFieldChange = (field) => (event) => {
    const value = event.target.value;
    setJobForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleJobSubmit = async (event) => {
    event.preventDefault();

    const title = jobForm.title.trim();
    const jobDescription = jobForm.jobDescription.trim();

    if (!title || !jobDescription) {
      window.alert('Please provide both a job title and job description.');
      return;
    }

    const customJobId = jobForm.jobId.trim();
    const jobId = customJobId
      ? slugifyValue(customJobId)
      : `${slugifyValue(title)}-${Date.now()}`;

    const minYearsExperience = jobForm.minYearsExperience.trim();

    setIsSubmittingJob(true);
    try {
      await onCreateJob({
        job_id: jobId,
        title,
        job_description: jobDescription,
        required_skills: parseSkillInput(jobForm.requiredSkills),
        preferred_skills: parseSkillInput(jobForm.preferredSkills),
        min_years_experience: minYearsExperience ? Number(minYearsExperience) : null,
        education_level: jobForm.educationLevel.trim() || null,
      });
      setJobForm(EMPTY_JOB_FORM);
      setIsJobModalOpen(false);
    } finally {
      setIsSubmittingJob(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Job Selection Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Select Job Position</h3>
            <p className="mt-1 text-sm text-slate-600">
              Create a real hiring role, then select it before uploading resumes.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setIsJobModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Create Job
          </button>
        </div>

        <div>
          <div className="mb-4">
            <h4 className="text-base font-semibold text-slate-900">Available Jobs</h4>
            <p className="mt-1 text-sm text-slate-600">
              Select a job to upload resumes into that role.
            </p>
          </div>

          {jobs.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {jobs.map(job => (
                <div
                  key={job.job_id}
                  onClick={() => onJobSelect(job.job_id)}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedJob === job.job_id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-semibold text-slate-900 mb-1">{job.title}</h4>
                      <p className="text-xs text-slate-500 mb-2">{job.job_id}</p>
                      <p className="text-sm text-slate-600 mb-2">
                        {job.candidates_count || 0} candidate{job.candidates_count !== 1 ? 's' : ''}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {job.required_skills?.slice(0, 3).map(skill => (
                          <span 
                            key={skill} 
                            className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium"
                          >
                            {skill}
                          </span>
                        ))}
                        {job.required_skills?.length > 3 && (
                          <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs">
                            +{job.required_skills.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                    {selectedJob === job.job_id && (
                      <div className="ml-2">
                        <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 bg-slate-50 rounded-lg">
              <p className="text-slate-600 mb-4">No jobs available yet. Create your first job to get started.</p>
            </div>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatsCard
          title="Total Candidates"
          value={stats.total_candidates}
          icon={Users}
          color="blue"
        />
        <StatsCard
          title="Shortlisted"
          value={stats.shortlisted}
          icon={CheckCircle}
          color="green"
        />
        <StatsCard
          title="Rejected"
          value={stats.rejected}
          icon={XCircle}
          color="red"
        />
        <StatsCard
          title="Avg Score"
          value={formatPercent(stats.avg_score)}
          icon={TrendingUp}
          color="purple"
        />
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <div className="text-center max-w-xl mx-auto">
          <div className="inline-flex p-4 bg-blue-50 rounded-full mb-4">
            <Upload className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Upload Resumes</h2>
          <p className="text-slate-600 mb-6">
            Our multi-agent system will automatically intake, screen, and audit candidates before any manual reranking
          </p>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
          
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={processing || !selectedJob}
            className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
          >
            {processing ? 'Processing...' : 'Select Files to Upload'}
          </button>
          
          <p className="text-sm text-slate-500 mt-4">
            {selectedJob 
              ? 'Supports PDF, DOCX, and TXT files (max 10MB each)' 
              : 'Please select a job first'
            }
          </p>
        </div>
      </div>

      {/* Agent Status */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900">Agent Status</h3>
          <button
            onClick={() => window.location.reload()}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4 text-slate-600" />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map(agent => (
            <div 
              key={agent.id} 
              className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200"
            >
              <div className="p-3 bg-white rounded-lg shadow-sm">
                <agent.icon className="w-6 h-6 text-slate-700" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-slate-900">{agent.name}</p>
                <p className="text-sm text-slate-600">
                  {processing ? 'Active' : 'Ready'}
                </p>
              </div>
              <div className={`w-3 h-3 rounded-full ${
                processing ? 'bg-green-500 animate-pulse' : 'bg-slate-300'
              }`} />
            </div>
          ))}
        </div>
      </div>

      {isJobModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-8">
          <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Create Job</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Add a real role with the details needed for resume screening.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsJobModalOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
              >
                Close
              </button>
            </div>

            <form onSubmit={handleJobSubmit} className="space-y-4 px-6 py-5">
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Job Title
                </label>
                <input
                  type="text"
                  value={jobForm.title}
                  onChange={handleJobFieldChange('title')}
                  placeholder="Senior Backend Engineer"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Job ID
                  <span className="ml-2 text-xs font-normal text-slate-500">(optional)</span>
                </label>
                <input
                  type="text"
                  value={jobForm.jobId}
                  onChange={handleJobFieldChange('jobId')}
                  placeholder="senior-backend-engineer"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
                <p className="mt-1 text-xs text-slate-500">
                  Leave blank to auto-generate a unique ID from the job title.
                </p>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Job Description
                </label>
                <textarea
                  value={jobForm.jobDescription}
                  onChange={handleJobFieldChange('jobDescription')}
                  rows={6}
                  placeholder="Describe the role, responsibilities, and what a strong candidate should bring."
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Required Skills
                </label>
                <input
                  type="text"
                  value={jobForm.requiredSkills}
                  onChange={handleJobFieldChange('requiredSkills')}
                  placeholder="Python, FastAPI, SQL"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Preferred Skills
                </label>
                <input
                  type="text"
                  value={jobForm.preferredSkills}
                  onChange={handleJobFieldChange('preferredSkills')}
                  placeholder="Docker, AWS, CI/CD"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">
                    Min Years Experience
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={jobForm.minYearsExperience}
                    onChange={handleJobFieldChange('minYearsExperience')}
                    placeholder="3"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">
                    Education Level
                  </label>
                  <input
                    type="text"
                    value={jobForm.educationLevel}
                    onChange={handleJobFieldChange('educationLevel')}
                    placeholder="Bachelor's Degree"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsJobModalOpen(false)}
                  className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingJob}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Plus className="w-4 h-4" />
                  {isSubmittingJob ? 'Creating Job...' : 'Create Job'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
