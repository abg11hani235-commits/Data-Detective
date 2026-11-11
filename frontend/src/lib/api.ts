import { DatasetProfile, SampleDatasetInfo, AnalysisResponse, HealthStatus } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

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
    const res = await fetch(`${API_BASE}/api/health`);
    return handleResponse(res);
  },

  async getSamples(): Promise<SampleDatasetInfo[]> {
    const res = await fetch(`${API_BASE}/api/samples`);
    return handleResponse(res);
  },

  async loadSample(sampleId: string): Promise<DatasetProfile> {
    const res = await fetch(`${API_BASE}/api/samples/${sampleId}/load`, {
      method: "POST",
    });
    return handleResponse(res);
  },

  async uploadDataset(file: File): Promise<DatasetProfile> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/datasets/upload`, {
      method: "POST",
      body: formData,
    });
    return handleResponse(res);
  },

  async createSession(datasetId?: string): Promise<{ session_id: string; dataset_id?: string }> {
    const res = await fetch(`${API_BASE}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId }),
    });
    return handleResponse(res);
  },

  async attachDataset(sessionId: string, datasetId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/set_dataset/${datasetId}`, {
      method: "POST",
    });
    return handleResponse(res);
  },

  async askQuestion(sessionId: string, question: string): Promise<AnalysisResponse> {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    return handleResponse(res);
  },

  async getSessionHistory(sessionId: string): Promise<AnalysisResponse[]> {
    const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`);
    return handleResponse(res);
  },

  getReportDownloadUrl(analysisId: string, format: "html" | "markdown" = "html", sessionId?: string): string {
    const sessParam = sessionId ? `&session_id=${sessionId}` : "";
    return `${API_BASE}/api/reports/${analysisId}/download?format=${format}${sessParam}`;
  },

  getHtmlReportUrl(analysisId: string, sessionId?: string): string {
    const sessParam = sessionId ? `?session_id=${sessionId}` : "";
    return `${API_BASE}/api/reports/${analysisId}/html${sessParam}`;
  },
};
