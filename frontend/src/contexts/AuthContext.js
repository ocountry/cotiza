import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('vigil_session_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  };

  const checkAuth = async () => {
    const token = localStorage.getItem('vigil_session_token');
    if (!token) {
      setLoading(false);
      setUser(null);
      return;
    }

    try {
      const response = await fetch(`${API}/auth/me`, {
        credentials: 'include',
        headers: {
          ...getAuthHeaders(),
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        localStorage.removeItem('vigil_session_token');
        setUser(null);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    window.location.href = `${API}/auth/google/login`;
  };

  const logout = async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          ...getAuthHeaders(),
        },
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('vigil_session_token');
      setUser(null);
    }
  };

  const processSession = async (token) => {
    if (!token) return null;

    localStorage.setItem('vigil_session_token', token);

    try {
      const response = await fetch(`${API}/auth/me`, {
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        return userData;
      }
      return null;
    } catch (error) {
      console.error('Session processing failed:', error);
      return null;
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, processSession, checkAuth, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
