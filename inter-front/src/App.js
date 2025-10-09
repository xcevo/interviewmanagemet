import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import { isLoggedIn } from './utils/auth';
import ErrorBoundary from "./ErrorBoundary";

const PrivateRoute = ({ children }) =>
  isLoggedIn() ? children : <Navigate to="/login" />;

function App() {
  return (
    <Router>
      <Routes>
        <Route
  path="/"
  element={
    <ErrorBoundary>
      <PrivateRoute>
        <Dashboard />
      </PrivateRoute>
    </ErrorBoundary>
  }
/>
<Route path="/login" element={<Login />} /> 
      </Routes>
    </Router>
  );
}

export default App;
