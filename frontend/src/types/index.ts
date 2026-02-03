// =============================================================================
// Type Definitions for AI Insurance Claim Assistant
// =============================================================================

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'adjuster' | 'reviewer' | 'agent' | 'customer';
  department?: string;
  phone?: string;
  avatar?: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface PolicyDocument {
  id: string;
  title: string;
  policy_type: string;
  document: string;
  version: string;
  effective_date: string;
  expiry_date: string | null;
  is_indexed: boolean;
  chunk_count: number;
  uploaded_by_name: string;
  created_at: string;
}

export interface InsurancePolicy {
  id: string;
  policy_number: string;
  holder: number;
  holder_name: string;
  policy_type: string;
  status: string;
  premium_amount: string;
  deductible_amount: string;
  coverage_limit: string;
  effective_date: string;
  expiry_date: string;
  vehicle_details: Record<string, any>;
}

export interface Claim {
  id: string;
  claim_number: string;
  claimant_name: string;
  policy_number: string;
  policy: string;
  status: ClaimStatus;
  priority: Priority;
  loss_type: LossType;
  date_of_loss: string;
  date_reported: string;
  loss_description: string;
  loss_location: string;
  estimated_repair_cost: string;
  approved_amount: string | null;
  deductible_applied: string | null;
  settlement_amount: string | null;
  vehicle_details: Record<string, any>;
  third_party_involved: boolean;
  police_report_number: string;
  fraud_score: number | null;
  fraud_flags: FraudFlag[];
  ai_recommendation: AIRecommendation | null;
  ai_processing_log: ProcessingLogEntry[];
  assigned_adjuster: number | null;
  adjuster_name: string | null;
  documents: ClaimDocument[];
  notes: ClaimNote[];
  audit_logs: AuditLog[];
  fraud_alerts: FraudAlert[];
  agent_tasks: AgentTask[];
  document_count: number;
  created_at: string;
  updated_at: string;
}

export type ClaimStatus =
  | 'draft' | 'submitted' | 'under_review' | 'ai_processing'
  | 'pending_info' | 'approved' | 'partially_approved'
  | 'denied' | 'appealed' | 'settled' | 'closed';

export type Priority = 'low' | 'medium' | 'high' | 'urgent';

export type LossType =
  | 'collision' | 'comprehensive' | 'liability' | 'personal_injury'
  | 'property_damage' | 'theft' | 'vandalism' | 'weather' | 'other';

export interface FraudFlag {
  indicator: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

export interface AIRecommendation {
  policy_section: string;
  recommendation_summary: string;
  deductible: number | null;
  settlement_amount: number | null;
  ai_decision?: 'approve' | 'deny';
}

export interface ProcessingLogEntry {
  step: string;
  agent: string;
  status: string;
  duration_ms?: number;
  result_summary?: string;
  timestamp?: number;
}

export interface ClaimDocument {
  id: string;
  claim: string;
  document_type: string;
  file: string;
  filename: string;
  description: string;
  ai_extracted_data: Record<string, any>;
  uploaded_by_name: string;
  created_at: string;
}

export interface ClaimNote {
  id: string;
  claim: string;
  author: number;
  author_name: string;
  content: string;
  is_internal: boolean;
  is_ai_generated: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  claim: string;
  user: number;
  user_name: string;
  action: string;
  details: Record<string, any>;
  old_value: any;
  new_value: any;
  timestamp: string;
}

export interface FraudAlert {
  id: string;
  claim: string;
  claim_number: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: string;
  alert_type: string;
  description: string;
  indicators: any[];
  ai_confidence: number;
  reviewed_by_name: string | null;
  resolution_notes: string;
  created_at: string;
}

export interface AgentTask {
  id: string;
  claim: string;
  claim_number: string;
  agent_type: string;
  status: string;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  error_message: string;
  duration_ms: number | null;
  created_at: string;
}

export interface Notification {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  claim: string | null;
  claim_number: string | null;
  is_read: boolean;
  created_at: string;
}

export interface DashboardSummary {
  total_claims: number;
  pending_claims: number;
  approved_claims: number;
  denied_claims: number;
  total_payout: number;
  avg_processing_time_hours: number;
  fraud_alerts_count: number;
  claims_by_status: Record<string, number>;
  claims_by_type: Record<string, number>;
  recent_claims: Claim[];
  monthly_trend: { month: string; count: number; total_amount: number }[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AgentCard {
  agent_id: string;
  name: string;
  description: string;
  protocol: string;
  capabilities: { action: string; description: string }[];
  status: string;
}
