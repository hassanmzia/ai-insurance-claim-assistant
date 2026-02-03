import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import {
  AuthTokens, Claim, ClaimDocument, DashboardSummary, FraudAlert,
  InsurancePolicy, Notification, PaginatedResponse, PolicyDocument, User, AgentCard,
} from '../types';

const API_URL = process.env.REACT_APP_API_URL || 'http://172.168.1.95:4062/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 120000,
      headers: { 'Content-Type': 'application/json' },
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          const refreshToken = localStorage.getItem('refresh_token');
          if (refreshToken) {
            try {
              const response = await axios.post(`${API_URL}/token/refresh/`, {
                refresh: refreshToken,
              });
              localStorage.setItem('access_token', response.data.access);
              if (response.data.refresh) {
                localStorage.setItem('refresh_token', response.data.refresh);
              }
              error.config.headers.Authorization = `Bearer ${response.data.access}`;
              return this.client.request(error.config);
            } catch {
              localStorage.removeItem('access_token');
              localStorage.removeItem('refresh_token');
              window.location.href = '/login';
            }
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(username: string, password: string): Promise<AuthTokens> {
    const { data } = await this.client.post('/token/', { username, password });
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    return data;
  }

  async register(userData: Record<string, string>): Promise<any> {
    const { data } = await this.client.post('/auth/register/', userData);
    return data;
  }

  async getCurrentUser(): Promise<User> {
    const { data } = await this.client.get('/auth/me/');
    return data;
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  // Dashboard
  async getDashboard(): Promise<DashboardSummary> {
    const { data } = await this.client.get('/dashboard/');
    return data;
  }

  async getAnalytics(period?: number): Promise<any> {
    const { data } = await this.client.get('/analytics/', { params: { period } });
    return data;
  }

  // Claims
  async getClaims(params?: Record<string, any>): Promise<PaginatedResponse<Claim>> {
    const { data } = await this.client.get('/claims/', { params });
    return data;
  }

  async getClaim(id: string): Promise<Claim> {
    const { data } = await this.client.get(`/claims/${id}/`);
    return data;
  }

  async createClaim(claimData: Record<string, any>): Promise<Claim> {
    const { data } = await this.client.post('/claims/', claimData);
    return data;
  }

  async updateClaim(id: string, claimData: Record<string, any>): Promise<Claim> {
    const { data } = await this.client.patch(`/claims/${id}/`, claimData);
    return data;
  }

  async processClaim(id: string, processingType: string = 'full'): Promise<any> {
    const { data } = await this.client.post(`/claims/${id}/process/`, {
      processing_type: processingType,
    });
    return data;
  }

  async assignClaim(id: string, adjusterId: number): Promise<any> {
    const { data } = await this.client.post(`/claims/${id}/assign/`, {
      adjuster_id: adjusterId,
    });
    return data;
  }

  async updateClaimStatus(id: string, status: string, extra?: Record<string, any>): Promise<any> {
    const { data } = await this.client.post(`/claims/${id}/update_status/`, {
      status, ...extra,
    });
    return data;
  }

  async uploadClaimDocument(id: string, formData: FormData): Promise<ClaimDocument> {
    const { data } = await this.client.post(`/claims/${id}/upload_document/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  }

  async addClaimNote(id: string, content: string, isInternal: boolean = true): Promise<any> {
    const { data } = await this.client.post(`/claims/${id}/add_note/`, {
      content, is_internal: isInternal,
    });
    return data;
  }

  // Policies
  async getPolicies(params?: Record<string, any>): Promise<PaginatedResponse<InsurancePolicy>> {
    const { data } = await this.client.get('/policies/', { params });
    return data;
  }

  // Policy Documents
  async getPolicyDocuments(): Promise<PaginatedResponse<PolicyDocument>> {
    const { data } = await this.client.get('/policy-documents/');
    return data;
  }

  async uploadPolicyDocument(formData: FormData): Promise<PolicyDocument> {
    const { data } = await this.client.post('/policy-documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  }

  async indexPolicyDocument(id: string): Promise<any> {
    const { data } = await this.client.post(`/policy-documents/${id}/index/`);
    return data;
  }

  // Fraud Alerts
  async getFraudAlerts(params?: Record<string, any>): Promise<PaginatedResponse<FraudAlert>> {
    const { data } = await this.client.get('/fraud-alerts/', { params });
    return data;
  }

  async resolveFraudAlert(id: string, resolution: string, notes: string): Promise<FraudAlert> {
    const { data } = await this.client.post(`/fraud-alerts/${id}/resolve/`, {
      resolution, notes,
    });
    return data;
  }

  // Notifications
  async getNotifications(): Promise<PaginatedResponse<Notification>> {
    const { data } = await this.client.get('/notifications/');
    return data;
  }

  async markNotificationRead(id: string): Promise<void> {
    await this.client.post(`/notifications/${id}/mark_read/`);
  }

  async markAllNotificationsRead(): Promise<void> {
    await this.client.post('/notifications/mark_all_read/');
  }

  // Agents (A2A)
  async getAgents(): Promise<{ agents: AgentCard[] }> {
    const agentUrl = API_URL.replace('/api', '/agents');
    const { data } = await axios.get(`${agentUrl}/agents`);
    return data;
  }

  // MCP Tools
  async getMCPTools(): Promise<any> {
    const mcpUrl = API_URL.replace('/api', '/mcp');
    const { data } = await axios.get(`${mcpUrl}/tools/list`);
    return data;
  }
}

export const api = new ApiService();
export default api;
