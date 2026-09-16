(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.tabs-links a'));
  var sections = links.map(function (a) {
    var href = a.getAttribute('href');
    return href.charAt(0) === '#' ? document.querySelector(href) : null;
  });

  function setActive(id) {
    links.forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('href') === '#' + id);
    });
  }

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) setActive(e.target.id);
      });
    }, { rootMargin: '-40% 0px -55% 0px', threshold: 0 });
    sections.forEach(function (s) { if (s) io.observe(s); });
  }
})();
