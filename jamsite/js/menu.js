document.addEventListener('DOMContentLoaded', function() {
  const menuToggle = document.getElementById('side-menu-toggle');
  const sideMenu = document.getElementById('side-menu');
  const overlay = document.getElementById('side-menu-overlay');

  function toggleMenu() {
    sideMenu.classList.toggle('open');
    overlay.classList.toggle('visible');
    document.body.style.overflow = sideMenu.classList.contains('open') ? 'hidden' : '';
  }

  menuToggle.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', toggleMenu);

  // Close menu when clicking a link
  const menuLinks = sideMenu.getElementsByClassName('side-menu-link');
  Array.from(menuLinks).forEach(link => {
    link.addEventListener('click', () => {
      if (sideMenu.classList.contains('open')) {
        toggleMenu();
      }
    });
  });
}); 