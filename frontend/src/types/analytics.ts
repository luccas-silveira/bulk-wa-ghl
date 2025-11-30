export interface MessagingKpiParams {
  days?: number;
  channel?: string;
}

export interface MessagingKpiTotals {
  sent: number;
  delivered: number;
  responses: number;
  deliveryRate: number;
  responseRate: number;
}

export interface MessagingKpiTimeline {
  labels: string[];
  sent: number[];
  delivered: number[];
  responses: number[];
}

export interface MessagingKpiBreakdownItem {
  label: string;
  sent: number;
  delivered: number;
  responses: number;
}

export interface MessagingKpiResponse {
  totals: MessagingKpiTotals;
  timeline: MessagingKpiTimeline;
  breakdown: MessagingKpiBreakdownItem[];
}
