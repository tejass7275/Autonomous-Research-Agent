// main.jsx
// Vite/React entry point.

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import ThemeToggle from "./components/ThemeToggle/ThemeToggle";
import "./theme.css"; // keep AFTER App so the dark overrides load last

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeToggle />
    <App />
  </React.StrictMode>
);
