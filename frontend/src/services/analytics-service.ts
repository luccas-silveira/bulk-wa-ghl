import { API_BASE_URL } from '../config/env';
import type { MessagingKpiParams, MessagingKpiResponse } from '../types/analytics';

const buildQueryString = (params?: MessagingKpiParams) => {
  const searchParams = new URLSearchParams();

  if (params?.days) {
    searchParams.append('days', params.days.toString());
  }

  if (params?.channel) {
    searchParams.append('channel', params.channel);
  }

  const query = searchParams.toString();
  return query ? `?${query}` : '';
};

const fetchKpis = async (params?: MessagingKpiParams): Promise<MessagingKpiResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/analytics/messaging-kpis${buildQueryString(params)}`);

  if (!response.ok) {
    let errorDetail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) errorDetail = String(body.detail);
    } catch {
      // JSON parse failed — keep the default errorDetail
    }
    throw new Error(`Falha ao buscar KPIs: ${errorDetail}`);
  }

  return response.json();
};

export const analyticsService = {
  fetchKpis,
};
