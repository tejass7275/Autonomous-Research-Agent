// App.jsx
// Root component for the Autonomous Research Agent.
// Handles authentication and switching between Dashboard and PaperDetail.

import React, { useState } from "react";
import { AppProvider, useAppContext } from "./context/AppContext";
import Dashboard from "./pages/Dashboard";
import PaperDetail from "./pages/PaperDetail";
import "./App.css";


/* =========================================
   Authentication Gate
========================================= */

function AuthGate({ children }) {
  const { isAuthenticated, login, authError } = useAppContext();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (isAuthenticated) {
    return children;
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    login(email, password);
  };

  return (
    <div className="auth-page">

      {/* Background decoration */}
      <div className="auth-background-circle auth-circle-one"></div>
      <div className="auth-background-circle auth-circle-two"></div>

      <div className="auth-card">

        {/* Logo */}
        <div className="auth-logo">
          <span>AI</span>
        </div>

        {/* Heading */}
        <div className="auth-header">
          <h1>Welcome back</h1>

          <p>
            Sign in to your Autonomous Research Agent
          </p>
        </div>

        {/* Login Form */}
        <form
          onSubmit={handleSubmit}
          className="auth-form"
        >

          {/* Email */}
          <div className="form-group">

            <label htmlFor="email">
              Email address
            </label>

            <input
              id="email"
              type="email"
              className="form-input"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

          </div>


          {/* Password */}
          <div className="form-group">

            <div className="password-label-row">

              <label htmlFor="password">
                Password
              </label>

              <span className="forgot-password">
                Secure login
              </span>

            </div>

            <input
              id="password"
              type="password"
              className="form-input"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

          </div>


          {/* Error */}
          {authError && (
            <div className="auth-error">
              <span className="error-icon">!</span>

              <span>{authError}</span>
            </div>
          )}


          {/* Submit */}
          <button
            type="submit"
            className="auth-button"
          >
            <span>Sign in</span>
            <span className="button-arrow">→</span>
          </button>

        </form>


        {/* Divider */}
        <div className="auth-divider">
          <span>AI-powered research</span>
        </div>


        {/* Features */}
        <div className="auth-features">

          <div className="feature-item">
            <div className="feature-icon">
              ⌕
            </div>

            <div>
              <strong>Smart Search</strong>
              <span>Discover research papers</span>
            </div>
          </div>


          <div className="feature-item">
            <div className="feature-icon">
              ✦
            </div>

            <div>
              <strong>AI Insights</strong>
              <span>Generate intelligent summaries</span>
            </div>
          </div>

        </div>


        {/* Footer */}
        <p className="auth-footer">
          Autonomous Research Agent
        </p>

      </div>

    </div>
  );
}


/* =========================================
   Application Content
========================================= */

function AppContent() {
  const [selectedPaperId, setSelectedPaperId] = useState(null);

  return (
    <div className="app">

      {selectedPaperId ? (

        <PaperDetail
          paperId={selectedPaperId}
          onBack={() => setSelectedPaperId(null)}
        />

      ) : (

        <Dashboard
          onSelectPaper={(paper) =>
            setSelectedPaperId(paper.id)
          }
        />

      )}

    </div>
  );
}


/* =========================================
   Root App
========================================= */

export default function App() {
  return (
    <AppProvider>

      <AuthGate>
        <AppContent />
      </AuthGate>

    </AppProvider>
  );
}