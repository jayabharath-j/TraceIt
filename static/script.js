// ========================================
// FITNESS TRACKER - THEME SWITCHER
// ========================================

document.addEventListener("DOMContentLoaded", function () {
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");

  // ========================================
  // GET SAVED THEME
  // ========================================

  const savedTheme = localStorage.getItem("fitnessTheme");

  // Default = light mode

  let currentTheme = "light";

  if (savedTheme === "dark") {
    currentTheme = "dark";
  }

  // Apply theme when page loads

  applyTheme(currentTheme);

  // ========================================
  // THEME BUTTON
  // ========================================

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const currentTheme =
        document.documentElement.getAttribute("data-bs-theme");

      if (currentTheme === "dark") {
        applyTheme("light");

        localStorage.setItem("fitnessTheme", "light");
      } else {
        applyTheme("dark");

        localStorage.setItem("fitnessTheme", "dark");
      }
    });
  }

  // ========================================
  // APPLY THEME
  // ========================================

  function applyTheme(theme) {
    // Bootstrap 5.3 theme

    document.documentElement.setAttribute("data-bs-theme", theme);

    // Body class

    if (theme === "dark") {
      document.body.classList.add("dark-mode");
    } else {
      document.body.classList.remove("dark-mode");
    }

    // ========================================
    // CHANGE ICON
    // ========================================

    if (themeIcon) {
      if (theme === "dark") {
        themeIcon.textContent = "☀️";
      } else {
        themeIcon.textContent = "🌙";
      }
    }

    // ========================================
    // CHANGE BUTTON TITLE
    // ========================================

    if (themeToggle) {
      if (theme === "dark") {
        themeToggle.setAttribute("title", "Switch to light mode");

        themeToggle.setAttribute("aria-label", "Switch to light mode");
      } else {
        themeToggle.setAttribute("title", "Switch to dark mode");

        themeToggle.setAttribute("aria-label", "Switch to dark mode");
      }
    }
  }
});
