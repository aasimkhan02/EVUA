const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const TOKEN_KEY = 'evua_token';

// Called when a 401/403 is received — wipes local state and reloads to show login
const forceLogout = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('evua:last-run');
  localStorage.removeItem('evua:migration-prefs');
  // Trigger a full page reload so AuthContext re-runs and lands on login
  window.location.reload();
};

const api = {
  async request(endpoint, options = {}) {
    const token = localStorage.getItem(TOKEN_KEY);

    const headers = { ...options.headers };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Don't set Content-Type for FormData (browser sets it automatically with boundary)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    // Auto-logout on auth failure — stops the "stuck logged-in with invalid token" bug
    if (response.status === 401 || response.status === 403) {
      forceLogout();
      throw new Error('Session expired. Please log in again.');
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP Error ${response.status}`);
    }

    return data;
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, body, isFormData = false) {
    return this.request(endpoint, {
      method: 'POST',
      body: isFormData ? body : JSON.stringify(body),
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },
};

export default api;
