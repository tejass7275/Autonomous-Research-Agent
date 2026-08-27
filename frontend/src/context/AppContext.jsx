// // AppContext.jsx
// // Lightweight auth context: tracks whether the user is logged in and exposes
// // login/logout actions. Kept intentionally simple — swap for a state library
// // if the app's shared state grows beyond auth.

// import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
// import * as api from "../api/client";

// const AppContext = createContext(null);

// export function AppProvider({ children }) {
//   const [isAuthenticated, setIsAuthenticated] = useState(
//     () => !!localStorage.getItem("access_token")
//   );
//   const [authError, setAuthError] = useState(null);

//   useEffect(() => {
//     const handleExpired = () => setIsAuthenticated(false);
//     window.addEventListener("auth:expired", handleExpired);
//     return () => window.removeEventListener("auth:expired", handleExpired);
//   }, []);

//   const login = useCallback(async (email, password) => {
//     setAuthError(null);
//     try {
//       await api.login(email, password);
//       setIsAuthenticated(true);
//       return true;
//     } catch (err) {
//       setAuthError(err.response?.data?.detail || "Login failed");
//       return false;
//     }
//   }, []);

//   const logout = useCallback(() => {
//     api.logout();
//     setIsAuthenticated(false);
//   }, []);

//   const value = { isAuthenticated, authError, login, logout };

//   return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
// }

// export function useAppContext() {
//   const ctx = useContext(AppContext);
//   if (!ctx) {
//     throw new Error("useAppContext must be used within an AppProvider");
//   }
//   return ctx;
// }


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

  const [isAuthenticated, setIsAuthenticated] = useState(
  () => !!sessionStorage.getItem("access_token")
);

  const [authError, setAuthError] = useState(null);

  useEffect(() => {

    const handleExpired = () => {
      setIsAuthenticated(false);
    };

    window.addEventListener("auth:expired", handleExpired);

    return () => {
      window.removeEventListener("auth:expired", handleExpired);
    };

  }, []);


  const login = useCallback(async (email, password) => {

    setAuthError(null);

    // TEMPORARY FRONTEND TEST LOGIN
    // Remove this when FastAPI authentication is ready.

    if (
      email === "test@example.com" &&
      password === "test123"
    ) {

      localStorage.setItem(
        "access_token",
        "frontend-test-token"
      );

      setIsAuthenticated(true);

      return true;
    }

    setAuthError(
      "Invalid test credentials. Use test@example.com / test123"
    );

    return false;

  }, []);


  const logout = useCallback(() => {

    api.logout();

    setIsAuthenticated(false);

  }, []);


  const value = {
    isAuthenticated,
    authError,
    login,
    logout,
  };


  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}


export function useAppContext() {

  const ctx = useContext(AppContext);

  if (!ctx) {
    throw new Error(
      "useAppContext must be used within an AppProvider"
    );
  }

  return ctx;
}