/**
 * API utility for making authenticated requests to the backend.
 * Automatically includes the session token from localStorage.
 */

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const apiFetch = (endpoint, options = {}) => {
  const token = localStorage.getItem('vigil_session_token');
  const url = endpoint.startsWith('http') ? endpoint : `${API}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  return fetch(url, {
    ...options,
    credentials: 'include',
    headers,
  });
};

export default apiFetch;