async function loadSidebar() {
  const container = document.querySelector('[data-sidebar]');
  if (!container) return;
  try {
    const response = await fetch('/partials/sidebar.html');
    if (!response.ok) {
      throw new Error('Unable to load sidebar');
    }
    container.innerHTML = await response.text();
    const currentPath = window.location.pathname;
    container.querySelectorAll('.nav-link').forEach((link) => {
      const linkPath = new URL(link.getAttribute('href'), window.location.origin).pathname;
      if (linkPath === currentPath) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      }
    });
  } catch (error) {
    console.error('Failed to load sidebar', error);
  }
}

document.addEventListener('DOMContentLoaded', loadSidebar);
