# Frontend Integration Guide

## API Base URL Configuration

### Vercel Environment Variables

Add these to your Vercel project settings:

```
VITE_API_URL=https://your-railway-app.up.railway.app/api/v1
```

For production with custom domain:
```
VITE_API_URL=https://api.hiringcircle.us/api/v1
```

## API Client Setup

### Axios Configuration (React/Vue)

```javascript
// api.js
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for CORS
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(
          `${import.meta.env.VITE_API_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        );
        
        const { access_token, refresh_token } = response.data.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
```

## Authentication Flow

### 1. Registration

```javascript
// Register component
const register = async (userData) => {
  try {
    const response = await api.post('/auth/register', {
      email: userData.email,
      password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName,
    });
    
    // Show success message
    alert('Registration successful! Please check your email to verify your account.');
    
    return response.data;
  } catch (error) {
    console.error('Registration failed:', error.response?.data?.detail);
    throw error;
  }
};
```

### 2. Email Verification

```javascript
// VerifyEmail component
const verifyEmail = async (token) => {
  try {
    const response = await api.post('/auth/verify-email', { token });
    
    alert('Email verified successfully! You can now log in.');
    navigate('/login');
    
    return response.data;
  } catch (error) {
    console.error('Verification failed:', error.response?.data?.detail);
    alert('Invalid or expired verification link.');
  }
};

// Get token from URL
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (token) {
    verifyEmail(token);
  }
}, []);
```

### 3. Login

```javascript
// Login component
const login = async (credentials) => {
  try {
    const response = await api.post('/auth/login', {
      email: credentials.email,
      password: credentials.password,
    });
    
    const { access_token, refresh_token, user } = response.data.data;
    
    // Store tokens
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('user', JSON.stringify(user));
    
    // Redirect to dashboard
    navigate('/dashboard');
    
    return response.data;
  } catch (error) {
    if (error.response?.status === 403) {
      alert('Please verify your email before logging in.');
    } else {
      alert('Invalid email or password.');
    }
    throw error;
  }
};
```

### 4. Password Reset

```javascript
// ForgotPassword component
const requestPasswordReset = async (email) => {
  try {
    await api.post('/auth/forgot-password', { email });
    alert('If an account exists, a password reset link has been sent.');
  } catch (error) {
    // Always show success to prevent email enumeration
    alert('If an account exists, a password reset link has been sent.');
  }
};

// ResetPassword component
const resetPassword = async (token, newPassword) => {
  try {
    await api.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    alert('Password reset successful! Please log in.');
    navigate('/login');
  } catch (error) {
    alert('Invalid or expired reset link.');
  }
};
```

### 5. Logout

```javascript
const logout = () => {
  // Clear stored data
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  
  // Redirect to login
  navigate('/login');
};
```

## Protected Routes

```javascript
// ProtectedRoute component
const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }
      
      try {
        // Verify token by fetching user profile
        await api.get('/auth/me');
        setIsAuthenticated(true);
      } catch (error) {
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, []);
  
  if (isLoading) {
    return <div>Loading...</div>;
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};
```

## User Profile

```javascript
// Fetch user profile
const fetchProfile = async () => {
  try {
    const response = await api.get('/users/me');
    return response.data.data;
  } catch (error) {
    console.error('Failed to fetch profile:', error);
    throw error;
  }
};

// Update profile
const updateProfile = async (profileData) => {
  try {
    const response = await api.put('/users/me', profileData);
    return response.data.data;
  } catch (error) {
    console.error('Failed to update profile:', error);
    throw error;
  }
};

// Change password
const changePassword = async (currentPassword, newPassword) => {
  try {
    await api.post('/users/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    alert('Password changed successfully');
  } catch (error) {
    alert('Current password is incorrect');
    throw error;
  }
};
```

## Error Handling

```javascript
// Error handler utility
const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data.detail || 'Bad request';
      case 401:
        return 'Session expired. Please log in again.';
      case 403:
        return data.detail || 'Access denied';
      case 404:
        return 'Resource not found';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return data.detail || 'An error occurred';
    }
  } else if (error.request) {
    // Request made but no response
    return 'Network error. Please check your connection.';
  } else {
    return 'An unexpected error occurred';
  }
};
```

## CORS Configuration

The backend is configured to accept requests from:
- `https://hiringcircle.us`
- `https://www.hiringcircle.us`
- `http://localhost:3000` (development)
- `http://localhost:5173` (Vite dev server)

If you need to add more origins, update the `CORS_ORIGINS` environment variable in Railway.

## Testing Locally

1. Start backend:
```bash
cd hiringcircle-backend
uvicorn main:app --reload
```

2. Start frontend:
```bash
cd frontend
npm run dev
```

3. Update `.env.local`:
```
VITE_API_URL=http://localhost:8000/api/v1
```

## Production Checklist

- [ ] Frontend deployed to Vercel
- [ ] Backend deployed to Railway
- [ ] Environment variables set in both platforms
- [ ] Custom domain configured (GoDaddy)
- [ ] HTTPS enabled
- [ ] CORS origins updated with production domains
- [ ] Email SMTP configured
- [ ] Database migrations applied
