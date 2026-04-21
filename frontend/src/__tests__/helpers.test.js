import { describe, it, expect } from 'vitest';
import {
  isValidEmail,
  formatPercent,
  truncate,
  titleCase,
  formatFileSize,
  getStatusColor,
  getRecommendationColor,
  formatDecisionType,
} from '../utils/helpers';

describe('isValidEmail', () => {
  it('accepts valid email addresses', () => {
    expect(isValidEmail('user@example.com')).toBe(true);
    expect(isValidEmail('name.surname@domain.co')).toBe(true);
  });

  it('rejects invalid email addresses', () => {
    expect(isValidEmail('not-an-email')).toBe(false);
    expect(isValidEmail('')).toBe(false);
    expect(isValidEmail('@missing.user')).toBe(false);
    expect(isValidEmail('missing@.domain')).toBe(false);
  });
});

describe('formatPercent', () => {
  it('formats decimal values as percentages', () => {
    expect(formatPercent(0.85)).toBe('85%');
    expect(formatPercent(1)).toBe('100%');
    expect(formatPercent(0)).toBe('0%');
  });

  it('handles null and undefined', () => {
    expect(formatPercent(null)).toBe('0%');
    expect(formatPercent(undefined)).toBe('0%');
  });

  it('respects decimal places', () => {
    expect(formatPercent(0.8567, 1)).toBe('85.7%');
    expect(formatPercent(0.8567, 2)).toBe('85.67%');
  });
});

describe('truncate', () => {
  it('returns short text unchanged', () => {
    expect(truncate('hello', 10)).toBe('hello');
  });

  it('truncates long text with ellipsis', () => {
    expect(truncate('a very long string', 10)).toBe('a very lon...');
  });

  it('handles empty and null input', () => {
    expect(truncate('')).toBe('');
    expect(truncate(null)).toBe('');
  });
});

describe('titleCase', () => {
  it('converts snake_case to Title Case', () => {
    expect(titleCase('resume_intake')).toBe('Resume Intake');
  });

  it('converts kebab-case to Title Case', () => {
    expect(titleCase('skill-assessment')).toBe('Skill Assessment');
  });

  it('handles empty input', () => {
    expect(titleCase('')).toBe('');
    expect(titleCase(null)).toBe('');
  });
});

describe('formatFileSize', () => {
  it('formats bytes correctly', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1048576)).toBe('1 MB');
  });
});

describe('getStatusColor', () => {
  it('returns correct color classes for known statuses', () => {
    expect(getStatusColor('received')).toContain('blue');
    expect(getStatusColor('processing')).toContain('yellow');
    expect(getStatusColor('screened')).toContain('green');
    expect(getStatusColor('rejected')).toContain('red');
  });

  it('returns default gray for unknown statuses', () => {
    expect(getStatusColor('unknown')).toContain('gray');
  });
});

describe('getRecommendationColor', () => {
  it('returns correct color classes for recommendations', () => {
    expect(getRecommendationColor('SHORTLIST')).toContain('green');
    expect(getRecommendationColor('REJECT')).toContain('red');
    expect(getRecommendationColor('CONSIDER')).toContain('yellow');
  });

  it('returns PENDING color for unknown values', () => {
    expect(getRecommendationColor('UNKNOWN')).toContain('gray');
  });
});

describe('formatDecisionType', () => {
  it('maps known decision types to labels', () => {
    expect(formatDecisionType('resume_intake_result')).toBe('Resume Intake');
    expect(formatDecisionType('skill_assessment_result')).toBe('Skill Assessment');
    expect(formatDecisionType('audit_bias_check_result')).toBe('Audit Review');
  });

  it('falls back to title case for unknown types', () => {
    expect(formatDecisionType('some_custom_type')).toBe('Some Custom Type');
  });
});
