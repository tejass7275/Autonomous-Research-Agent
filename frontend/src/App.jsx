import React, { useState } from "react";
import { AppProvider, useAppContext } from "./context/AppContext";
import Dashboard from "./pages/Dashboard";
import PaperDetail from "./pages/PaperDetail";
import "./App.css";


function AuthGate({ children }) {

  const {
    isAuthenticated,
    login,
    register,
    authError,
  } = useAppContext();


  const [isSignUp, setIsSignUp] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");

  const [successMessage, setSuccessMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);


  if (isAuthenticated) {
    return children;
  }


  const handleSubmit = async (e) => {

    e.preventDefault();

    setSuccessMessage("");
    setIsSubmitting(true);


    if (isSignUp) {

      const success = await register(
        email,
        password,
        fullName
      );

      if (success) {

        setSuccessMessage(
          "Account created successfully. Please sign in."
        );

        // Switch back to login.
        setIsSignUp(false);

        setPassword("");
        setFullName("");
      }

    } else {

      await login(email, password);
    }

    setIsSubmitting(false);
  };


  const switchMode = () => {

    setIsSignUp(!isSignUp);

    setEmail("");
    setPassword("");
    setFullName("");

    setSuccessMessage("");
  };


  return (

    <div className="auth-page">

      <div className="auth-card">

        {/* Logo / Branding */}

        <div className="auth-brand">

          <div className="auth-logo">
            🔬
          </div>

          <h1>
            Autonomous Research Agent
          </h1>

          <p>
            Discover, analyze and understand research papers with AI.
          </p>

        </div>


        {/* Tabs */}

        <div className="auth-tabs">

          <button
            type="button"
            className={!isSignUp ? "auth-tab active" : "auth-tab"}
            onClick={() => {
              setIsSignUp(false);
              setSuccessMessage("");
            }}
          >
            Sign In
          </button>


          <button
            type="button"
            className={isSignUp ? "auth-tab active" : "auth-tab"}
            onClick={() => {
              setIsSignUp(true);
              setSuccessMessage("");
            }}
          >
            Create Account
          </button>

        </div>


        {/* Heading */}

        <div className="auth-heading">

          <h2>
            {isSignUp ? "Create your account" : "Welcome back"}
          </h2>

          <p>
            {isSignUp
              ? "Join the AI-powered research workspace."
              : "Sign in to continue your research."
            }
          </p>

        </div>


        {/* Form */}

        <form
          onSubmit={handleSubmit}
          className="auth-form"
        >

          {isSignUp && (

            <div className="form-group">

              <label htmlFor="fullName">
                Full Name
              </label>

              <input
                id="fullName"
                type="text"
                placeholder="Enter your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />

            </div>

          )}


          <div className="form-group">

            <label htmlFor="email">
              Email
            </label>

            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

          </div>


          <div className="form-group">

            <label htmlFor="password">
              Password
            </label>

            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

          </div>


          {/* Error */}

          {authError && (

            <div className="auth-error">
              {authError}
            </div>

          )}


          {/* Success */}

          {successMessage && (

            <div className="auth-success">
              {successMessage}
            </div>

          )}


          {/* Submit */}

          <button
            type="submit"
            className="auth-submit"
            disabled={isSubmitting}
          >

            {isSubmitting
              ? "Please wait..."
              : isSignUp
                ? "Create Account"
                : "Sign In"
            }

          </button>

        </form>


        {/* Bottom switch */}

        <div className="auth-switch">

          {isSignUp
            ? "Already have an account?"
            : "Don't have an account?"
          }

          <button
            type="button"
            onClick={switchMode}
          >

            {isSignUp
              ? "Sign In"
              : "Create Account"
            }

          </button>

        </div>

      </div>

    </div>
  );
}


function AppContent() {

  const [selectedPaperId, setSelectedPaperId] = useState(null);

  return selectedPaperId ? (

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

  );
}


export default function App() {

  return (

    <AppProvider>

      <AuthGate>

        <AppContent />

      </AuthGate>

    </AppProvider>
  );
}