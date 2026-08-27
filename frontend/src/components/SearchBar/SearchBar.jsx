// SearchBar.jsx
// Search input for querying the paper corpus. Submits on Enter or button
// click; parent owns the actual search request via the onSearch callback.

import React, { useState } from "react";

export default function SearchBar({ onSearch, isLoading = false, placeholder = "Search research papers..." }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim()) {
      onSearch(value.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-bar">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        className="search-bar__input"
        aria-label="Search research papers"
        disabled={isLoading}
      />
      <button
        type="submit"
        className="search-bar__button"
        disabled={isLoading || !value.trim()}
      >
        {isLoading ? "Searching..." : "Search"}
      </button>
    </form>
  );
}
