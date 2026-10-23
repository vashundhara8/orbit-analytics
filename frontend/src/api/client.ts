import {
  CohortRetentionResponse,
  ChurnAccountsResponse,
  ChurnSummaryResponse,
  ExperimentAnalysisResponse,
  ExperimentRevenueAnalysisResponse,
  ExperimentSummaryItem,
  FunnelAnalysisResponse,
  HealthResponse,
  TokenResponse,
} from '../types/api';

const API_BASE = '/api/v1';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('orbit_access_token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('orbit_access_token', token);
  }

  getToken(): string | null {
    return this.token;
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('orbit_access_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Token expired or invalid
      this.clearToken();
      throw new Error('Authentication required or session expired.');
    }

    if (!response.ok) {
      let errorMsg = `API Error (${response.status})`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          if (typeof errorData.detail === 'string') {
            errorMsg = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            errorMsg = errorData.detail
              .map((d: { msg?: string }) => d.msg || 'Validation error')
              .join(', ');
          }
        } else if (errorData.message) {
          errorMsg = errorData.message;
        }
      } catch {
        const text = await response.text();
        if (text) errorMsg = text;
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async getDemoToken(tenantId = 'org_orbit_demo'): Promise<TokenResponse> {
    const res = await this.request<TokenResponse>(`/auth/demo-token?tenant_id=${tenantId}`);
    this.setToken(res.access_token);
    return res;
  }

  async getFunnel(
    channel?: string,
    startDate?: string,
    endDate?: string
  ): Promise<FunnelAnalysisResponse> {
    const params = new URLSearchParams();
    if (channel && channel !== 'All Channels') {
      params.append('acquisition_channel', channel);
    }
    if (startDate) {
      params.append('start_date', startDate);
    }
    if (endDate) {
      params.append('end_date', endDate);
    }

    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request<FunnelAnalysisResponse>(`/funnel${query}`);
  }

  async getCohorts(
    maxWeeks = 12,
    numCohorts = 15,
    minCohortSize = 500,
    startDate?: string,
    endDate?: string
  ): Promise<CohortRetentionResponse> {
    const params = new URLSearchParams({
      max_weeks: maxWeeks.toString(),
      num_cohorts: numCohorts.toString(),
      min_cohort_size: minCohortSize.toString(),
    });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return this.request<CohortRetentionResponse>(`/cohorts?${params.toString()}`);
  }

  async getExperiments(): Promise<ExperimentSummaryItem[]> {
    return this.request<ExperimentSummaryItem[]>('/experiments');
  }

  async getExperimentAnalysis(
    experimentName = 'onboarding_v2'
  ): Promise<ExperimentAnalysisResponse> {
    return this.request<ExperimentAnalysisResponse>(`/experiments/${experimentName}`);
  }

  async getExperimentRevenueAnalysis(
    experimentName = 'onboarding_v2'
  ): Promise<ExperimentRevenueAnalysisResponse> {
    return this.request<ExperimentRevenueAnalysisResponse>(`/experiments/${experimentName}/revenue`);
  }

  async getChurnSummary(): Promise<ChurnSummaryResponse> {
    return this.request<ChurnSummaryResponse>('/churn/summary');
  }

  async getChurnAccounts(params?: {
    risk_tier?: string;
    industry?: string;
    plan_type?: string;
    limit?: number;
  }): Promise<ChurnAccountsResponse> {
    const q = new URLSearchParams();
    if (params?.risk_tier && params.risk_tier !== 'all') {
      q.append('risk_tier', params.risk_tier);
    }
    if (params?.industry && params.industry !== 'all') {
      q.append('industry', params.industry);
    }
    if (params?.plan_type && params.plan_type !== 'all') {
      q.append('plan_type', params.plan_type);
    }
    if (params?.limit) {
      q.append('limit', params.limit.toString());
    }
    const query = q.toString() ? `?${q.toString()}` : '';
    return this.request<ChurnAccountsResponse>(`/churn/accounts${query}`);
  }
}

export const api = new ApiClient();
