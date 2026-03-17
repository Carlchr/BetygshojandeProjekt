function toggleDarkMode() {
   document.body.classList.toggle("dark-mode");
   document.footer.classList.toggle("dark-mode");
   document.header.classList.toggle("dark-mode");
   localStorage.setItem("darkMode", document.body.classList.contains("dark-mode"));
}
