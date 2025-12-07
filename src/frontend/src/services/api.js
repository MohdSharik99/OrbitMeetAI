import axios from 'axios';

// Use proxy in development, direct URL in production
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.DEV ? '/api' : 'http://localhost:8000');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error('Request timeout');
      error.message = 'Request timeout. Please check if the backend server is running.';
    } else if (error.message === 'Network Error') {
      console.error('Network error - backend might not be running');
      error.message = 'Cannot connect to backend server. Please ensure the backend is running on port 8000.';
    } else if (error.response) {
      console.error('API Error Response:', error.response.status, error.response.data);
    } else {
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// Get list of all projects
export const getAllProjects = async () => {
  try {
    const response = await api.get('/projects');
    return response.data;
  } catch (error) {
    console.error('Error fetching projects:', error);
    throw error;
  }
};

// Get project data by project_key
export const getProjectData = async (projectKey) => {
  try {
    const response = await api.get(`/project/${encodeURIComponent(projectKey)}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching project data:', error);
    throw error;
  }
};

// Get project data by project_id (ObjectId)
export const getProjectDataById = async (projectId) => {
  try {
    const response = await api.get(`/project-by-id/${projectId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching project data by ID:', error);
    throw error;
  }
};

// Chat with OrbitMeetAI
export const chatWithOrbit = async (projectName, question, chatHistory = null) => {
  try {
    const response = await api.post('/orbit-chat', {
      project_name: projectName,
      question: question,
      chat_history: chatHistory,
    });
    return response.data;
  } catch (error) {
    console.error('Error chatting with Orbit:', error);
    throw error;
  }
};

// Get all transcripts (for project/meeting selection)
export const getAllTranscripts = async () => {
  try {
    const response = await api.get('/transcripts');
    return response.data;
  } catch (error) {
    console.error('Error fetching transcripts:', error);
    throw error;
  }
};

export default api;

