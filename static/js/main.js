function toggleDarkMode() {
   var element = document.body;
   var header = document.querySelector('header');
   var footer = document.querySelector('footer');
   header.classList.toggle("grey-mode");
   element.classList.toggle("dark-mode");
   footer.classList.toggle("grey-mode");
}
