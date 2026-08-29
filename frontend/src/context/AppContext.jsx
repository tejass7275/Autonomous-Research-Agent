// AppContext.jsx
//
// Authentication context for the application.
// Login and registration are handled by the FastAPI backend.
// The JWT access token is stored in sessionStorage so that
// refreshing the page keeps the user logged in during the session.

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";

import * as api from "../api/client";

const AppContext = createContext(null);

export function AppProvider({ children }) {

  // Check whether a JWT already exists when the application starts.
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!sessionStorage.getItem("access_token")
  );

  const [authError, setAuthError] = useState(null);


  // Handle expired/invalid JWT tokens.
  useEffect(() => {

    const handleExpired = () => {

      sessionStorage.removeItem("access_token");

      setIsAuthenticated(false);

      setAuthError("Your session has expired. Please sign in again.");
    };

    window.addEventListener("auth:expired", handleExpired);

    return () => {
      window.removeEventListener("auth:expired", handleExpired);
    };

  }, []);
 // ---------------------------------------------------------
  // REGISTER
  // ---------------------------------------------------------

  const register = useCallback(async (email, password, fullName) => {
  setAuthError(null);

  try {
    await api.register(email, password, fullName);

    // Registration successful.
    // We don't automatically log the user in here.
    return true;

  } catch (err) {
    const message =
      err.response?.data?.detail ||
      "Registration failed. Please try again.";

    setAuthError(message);

    return false;
  }
}, []);


  // ---------------------------------------------------------
  // LOGIN
  // ---------------------------------------------------------

  const login = useCallback(async (email, password) => {

    setAuthError(null);

    try {

      // Call the real FastAPI login endpoint.
      const data = await api.login(email, password);

      // Store JWT returned by backend.
      sessionStorage.setItem(
        "access_token",
        data.access_token
      );

      setIsAuthenticated(true);

      return true;

    } catch (err) {

      const message =
        err.response?.data?.detail ||
        "Login failed. Please check your email and password.";

      setAuthError(message);

      setIsAuthenticated(false);

      return false;
    }

  }, []);


  // ---------------------------------------------------------
  // LOGOUT
  // ---------------------------------------------------------

  const logout = useCallback(() => {

    api.logout();

    sessionStorage.removeItem("access_token");

    setIsAuthenticated(false);

    setAuthError(null);

  }, []);


  const value = {
    isAuthenticated,
    authError,
    login,
    register,
    logout,
  };


  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}


// ---------------------------------------------------------
// CUSTOM HOOK
// ---------------------------------------------------------

export function useAppContext() {

  const ctx = useContext(AppContext);

  if (!ctx) {
    throw new Error(
      "useAppContext must be used within an AppProvider"
    );
  }

  return ctx;
}