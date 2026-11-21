(function () {
  var form = document.getElementById("compare-form");
  if (!form) return;
  var button = document.querySelector("[data-compare-button]");
  var counter = document.querySelector("[data-compare-count]");
  var min = 2;
  var max = parseInt(form.getAttribute("data-max") || "4", 10);

  function boxes() {
    return document.querySelectorAll('input[name="ids"][form="compare-form"]');
  }

  function update() {
    var checked = Array.prototype.filter.call(boxes(), function (b) { return b.checked; });
    var n = checked.length;
    if (counter) {
      counter.textContent = n === 0
        ? "Tick " + min + " to " + max + " products to compare them side by side."
        : n + " selected" + (n > max ? " - choose at most " + max : n < min ? " - choose at least " + min : "");
    }
    if (button) button.disabled = n < min || n > max;
  }

  boxes().forEach(function (b) { b.addEventListener("change", update); });
  update();
})();
