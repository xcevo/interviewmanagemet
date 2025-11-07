import axios from 'axios';
import { setTokens, logout } from '../utils/auth';


const baseURL = process.env.REACT_APP_API_BASE_URL ;
const api = axios.create({
  baseURL,
  withCredentials: true,
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  res => res,
  async err => {
    const originalRequest = err.config;
    if (
      err.response &&
      err.response.status === 401 &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      try {
        const res = await axios.post(`${baseURL}auth/refresh`, {}, {
          withCredentials: true,
        });

        const newAccessToken = res.data.access_token;
        setTokens(newAccessToken);
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        logout();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(err);
  }
);

// ✅ Export functions individually
export const login = (username, password) =>
  api.post('/auth/login', { username, password });

export const fetchCategories = () => api.get('/categories/');
export const createCategory = (name) => api.post('/categories/', { name });
export const updateCategory = (id, data) => api.put(`/categories/${id}`, data);
export const deleteCategory = (id) => api.delete(`/categories/${id}`);

export const fetchCriteria = () => api.get('/criteria/');
export const createCriteria = data => api.post('/criteria/', data);

export const fetchQuestions = categoryId => api.get(`/questions/${categoryId}`);
export const uploadQuestions = formData =>
  api.post('/questions/upload', formData);
export const updateQuestion = (id, data) =>
  api.put(`/questions/${id}`, data);
export const deleteQuestion = id =>
  api.delete(`/questions/${id}`);




export const updateCriteria = (id, data) =>
  api.put(`/criteria/${id}`, data);

export const deleteCriteria = (id) =>
  api.delete(`/criteria/${id}`);


// Upload Excel
export const uploadCandidates = (formData) =>
  api.post('/users/upload', formData);

// Get all candidates for logged-in admin
export const fetchCandidates = () =>
  api.get('/users/get-all-candidates');

// CRUD for a single candidate
export const getCandidate = (id) =>
  api.get(`/users/candidate/${id}`);

export const updateCandidate = (id, data) =>
  api.put(`/users/candidate/${id}`, data);

export const deleteCandidate = (id) =>
  api.delete(`/users/candidate/${id}`);
export const fetchValidity = () => api.get('/users/validity');
export const createValidity = (data) => api.post('/users/validity', data);
export const updateValidityWindow = (id, data) => api.put(`/users/validity/${id}`, data);