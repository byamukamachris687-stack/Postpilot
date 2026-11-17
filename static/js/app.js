// Small UX helpers
document.addEventListener('DOMContentLoaded', () => {
  // auto-dismiss alerts after 5s
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(a => a.classList.remove('show'));
  }, 5000);
});