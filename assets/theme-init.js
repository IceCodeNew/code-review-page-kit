(function () {
  var pref = 'auto';
  try { pref = localStorage.getItem('review-theme') || 'auto'; } catch (e) {}
  var dark = pref === 'dark' || (pref === 'auto' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  var root = document.documentElement;
  root.dataset.pref = pref;
  root.dataset.theme = dark ? 'dark' : 'light';
})();
