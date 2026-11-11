export interface DatasetMetadata {
  id: string;
  filename: string;
  file_type: string;
  row_count: number;
  column_count: number;
  file_size_bytes: number;
  created_at: string;
}

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  semantic_role: string;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: (string | number)[];
  min_val?: number;
  max_val?: number;
  mean_val?: number;
  median_val?: number;
  std_val?: number;
  top_frequencies?: Record<string, number>;
  date_min?: string;
  date_max?: string;
}

export interface DatasetProfile {
  dataset_id: string;
  metadata: DatasetMetadata;
  columns: ColumnProfile[];
  total_cells: number;
  total_missing_cells: number;
  missing_cells_percentage: number;
  duplicate_rows: number;
  data_quality_score: number;
  preview_rows: Record<string, any>[];
}

export interface SampleDatasetInfo {
  id: string;
  title: string;
  category: string;
  description: string;
  filename: string;
  row_count: number;
  column_count: number;
  sample_questions: string[];
}

export interface AnalysisInsights {
  findings: string[];
  interpretation: string;
  caveats: string[];
}

export interface AnalysisResponse {
  id: string;
  session_id: string;
  question: string;
  plan: string;
  generated_code: string;
  execution_status: string;
  metrics: Record<string, any>;
  tables: {
    name: string;
    columns: string[];
    data: Record<string, any>[];
  }[];
  charts: {
    figure: any;
    caption: string;
  }[];
  insights: AnalysisInsights;
  warnings: string[];
  provider_used: string;
  execution_duration_ms: number;
  timestamp: string;
}

export interface StreamEvent {
  event_type: string;
  stage: string;
  message: string;
  payload?: any;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
  sandbox_enabled: boolean;
  providers: {
    primary: string;
    gemini_ready: boolean;
    groq_ready: boolean;
    heuristic_fallback_ready: boolean;
  };
  limits: {
    max_upload_size_mb: number;
    max_rows: number;
    timeout_seconds: number;
  };
}
