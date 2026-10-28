// useTheme.js
// Light/dark theme state. The choice is stored in localStorage and applied as
// <html data-theme="light|dark">, which theme.css keys off. index.html applies
// the saved value before React loads, so there's no white flash on refresh.

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "theme";
const VALID = ["light", "dark"];

function getInitialTheme() {
  // index.html already set the attribute from localStorage before React mounted.
  const applied = document.documentElement.getAttribute("data-theme");
  if (VALID.includes(applied)) return applied;

  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (VALID.includes(saved)) return saved;
  } catch {
    // localStorage can be unavailable (private mode / blocked) — fall through
  }
  return "light";
}

export function useTheme() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore — theme still works for this session
    }
  }, [theme]);

  const toggleTheme = useCallback(
    () => setTheme((current) => (current === "dark" ? "light" : "dark")),
    []
  );

  return { theme, toggleTheme };
}
