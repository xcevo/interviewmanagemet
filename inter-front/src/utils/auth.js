export const setTokens = (access) => {
  localStorage.setItem('access_token', access);
};

export const logout = () => {
  localStorage.removeItem('access_token');
  window.location = '/login';
};

export const isLoggedIn = () => !!localStorage.getItem('access_token');
