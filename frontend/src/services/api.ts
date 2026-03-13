import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for auth tokens
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("seedlings_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("seedlings_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Health check
export const checkHealth = () => api.get("/health");

// Events
export const submitEvent = (data: {
  source: string;
  event_type: string;
  text: string;
  context?: Record<string, unknown>;
  encrypted?: boolean;
  iv?: string;
  salt?: string;
}) => api.post("/events", data);

export const getEvents = (params?: { limit?: number; offset?: number }) =>
  api.get("/events", { params });

// Decisions
export const createDecision = (data: {
  title: string;
  rationale: string;
  expected_outcome: string;
  expected_outcome_date: string;
  confidence_score: number;
  alternatives?: string[];
}) => api.post("/decisions", data);

export const getDecisions = (params?: { status?: string }) =>
  api.get("/decisions", { params });

export const resolveDecision = (id: string, data: {
  actual_outcome: string;
  outcome_score: number;
}) => api.put(`/decisions/${id}/resolve`, data);

// Transcription
export const transcribeAudio = (audioBlob: Blob) => {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  return api.post("/transcribe", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

// Dashboard
export const getDashboardStats = () => api.get("/dashboard/stats");
export const getBiasDetections = () => api.get("/dashboard/biases");
export const getGrowthTrajectory = () => api.get("/dashboard/growth");

// Sparring
export const triggerSparring = (decisionId: string) =>
  api.post(`/sparring/${decisionId}`);

export const continueSparring = (
  decisionId: string,
  history: { role: string; content: string }[],
  userMessage: string
) =>
  api.post(`/sparring/${decisionId}/continue`, {
    conversation_history: history,
    user_message: userMessage,
  });

// Privacy
export const exportUserData = () => api.get("/privacy/export");
export const deleteUserData = () => api.delete("/privacy/data");

// Integrations
export const getIntegrationStatus = () => api.get("/integrations/status");
export const syncIntegrations = () => api.post("/integrations/sync");

export default api;
