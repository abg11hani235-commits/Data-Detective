import { DatasetProfile, SampleDatasetInfo, AnalysisResponse, HealthStatus, InvestigationSummary } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getAuthHeaders(): Record<string, string> {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  }
  return {};
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errJson.message || errMsg;
    } catch {
      // Fallback to text
      const errText = await res.text();
      if (errText) errMsg = errText;
    }
    throw new ApiError(res.status, errMsg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/api/health`, {
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async getSamples(): Promise<SampleDatasetInfo[]> {
    const res = await fetch(`${API_BASE}/api/samples`, {
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async loadSample(sampleId: string): Promise<DatasetProfile> {
    const res = await fetch(`${API_BASE}/api/samples/${sampleId}/load`, {
      method: "POST",
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async uploadDataset(file: File): Promise<DatasetProfile> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/datasets/upload`, {
      method: "POST",
      headers: { ...getAuthHeaders() },
      body: formData,
    });
    return handleResponse(res);
  },

  async getAdvancedEda(datasetId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/datasets/${datasetId}/advanced-eda`, {
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async createSession(datasetId?: string): Promise<{ session_id: string; dataset_id?: string }> {
    const res = await fetch(`${API_BASE}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({ dataset_id: datasetId }),
    });
    return handleResponse(res);
  },

  async attachDataset(sessionId: string, datasetId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/set_dataset/${datasetId}`, {
      method: "POST",
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async askQuestion(sessionId: string, question: string): Promise<AnalysisResponse> {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({ question }),
    });
    return handleResponse(res);
  },

  async getSessionHistory(sessionId: string): Promise<AnalysisResponse[]> {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`, {
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async listInvestigations(): Promise<InvestigationSummary[]> {
    const res = await fetch(`${API_BASE}/api/investigations`, {
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async getInvestigation(sessionId: string): Promise<InvestigationSummary> {
    const res = await fetch(`${API_BASE}/api/investigations/${sessionId}`, {
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  async updateInvestigation(sessionId: string, title: string): Promise<InvestigationSummary> {
    const res = await fetch(`${API_BASE}/api/investigations/${sessionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({ title }),
    });
    return handleResponse(res);
  },

  async deleteInvestigation(sessionId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/investigations/${sessionId}`, {
      method: "DELETE",
      headers: { ...getAuthHeaders() },
    });
    return handleResponse(res);
  },

  getReportDownloadUrl(analysisId: string, format: "html" | "markdown" | "excel" = "html", sessionId?: string): string {
    const sessParam = sessionId ? `&session_id=${sessionId}` : "";
    return `${API_BASE}/api/reports/${analysisId}/download?format=${format}${sessParam}`;
  },

  getHtmlReportUrl(analysisId: string, sessionId?: string): string {
    const sessParam = sessionId ? `?session_id=${sessionId}` : "";
    return `${API_BASE}/api/reports/${analysisId}/html${sessParam}`;
  },
};
