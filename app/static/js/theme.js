/* Light/dark theme. Loaded in <head> so the saved choice applies before first paint.
   Without a saved choice the page follows the operating system. */
(function () {
  var KEY = "folio.theme";
  var root = document.documentElement;

  function read() {
    try { return localStorage.getItem(KEY); } catch (error) { return null; }
  }

  function write(value) {
    try { localStorage.setItem(KEY, value); } catch (error) { /* private mode: ignore */ }
  }

  function current() {
    return root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }

  var saved = read();
  if (saved === "light" || saved === "dark") root.dataset.theme = saved;

  document.addEventListener("click", function (event) {
    if (!event.target.closest("[data-theme-toggle]")) return;
    var next = current() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    write(next);
  });
})();
