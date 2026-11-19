/*
  Hover/keyboard layer for the server-rendered price chart.

  - a vertical hairline follows the pointer and snaps to the nearest recorded date
  - ONE tooltip lists every retailer's price as of that date
  - ArrowLeft / ArrowRight step through the dates when the chart has focus
  - all text is inserted with textContent (never innerHTML)
  The same numbers are always available in the history table below the chart.
*/
(function () {
  var dataEl = document.getElementById("price-chart-data");
  var svg = document.getElementById("price-chart-svg");
  if (!dataEl || !svg) return;

  var chart = JSON.parse(dataEl.textContent);
  var g = chart.geometry;
  var NS = "http://www.w3.org/2000/svg";

  // every distinct recording time, ascending
  var times = [];
  chart.series.forEach(function (s) {
    s.points.forEach(function (p) { if (times.indexOf(p[0]) === -1) times.push(p[0]); });
  });
  times.sort(function (a, b) { return a - b; });
  if (!times.length) return;

  var wrap = svg.parentNode;
  var tip = document.createElement("div");
  tip.className = "chart-tip";
  tip.hidden = true;
  tip.setAttribute("aria-hidden", "true");
  wrap.appendChild(tip);

  var line = document.createElementNS(NS, "line");
  line.setAttribute("stroke", "#898781");
  line.setAttribute("stroke-width", "1");
  line.setAttribute("y1", g.yTop);
  line.setAttribute("y2", g.yBottom);
  line.style.display = "none";
  svg.appendChild(line);

  function xFor(ms) {
    return g.x0 + (ms - chart.tMin) / (chart.tMax - chart.tMin) * (g.x1 - g.x0);
  }
  function msFor(x) {
    return chart.tMin + (x - g.x0) / (g.x1 - g.x0) * (chart.tMax - chart.tMin);
  }
  function nearestIndex(ms) {
    var best = 0, bestDist = Infinity;
    times.forEach(function (t, i) {
      var d = Math.abs(t - ms);
      if (d < bestDist) { best = i; bestDist = d; }
    });
    return best;
  }
  function money(v) {
    return chart.currency + v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  var current = -1;

  function show(index) {
    current = index;
    var t = times[index];
    var x = xFor(t);
    line.setAttribute("x1", x);
    line.setAttribute("x2", x);
    line.style.display = "";

    tip.textContent = "";
    var date = document.createElement("div");
    date.className = "tip-date";
    date.textContent = new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
    tip.appendChild(date);

    chart.series.forEach(function (s) {
      var value = null;
      s.points.forEach(function (p) { if (p[0] <= t) value = p[1]; });
      var row = document.createElement("div");
      row.className = "tip-row";
      var name = document.createElement("span");
      name.className = "tip-name";
      var key = document.createElement("span");
      key.className = "tip-key";
      key.style.borderTopColor = s.color;
      name.appendChild(key);
      name.appendChild(document.createTextNode(s.name));
      var val = document.createElement("span");
      val.className = "tip-val";
      val.textContent = value === null ? "-" : money(value);
      row.appendChild(name);
      row.appendChild(val);
      tip.appendChild(row);
    });

    tip.hidden = false;
    var rect = svg.getBoundingClientRect();
    var scale = rect.width / g.width;
    var left = x * scale + 12;
    if (left + tip.offsetWidth > rect.width) left = x * scale - tip.offsetWidth - 12;
    tip.style.left = Math.max(0, left) + "px";
    tip.style.top = (g.yTop * scale + 6) + "px";
  }

  function hide() {
    current = -1;
    tip.hidden = true;
    line.style.display = "none";
  }

  svg.addEventListener("pointermove", function (e) {
    var rect = svg.getBoundingClientRect();
    var x = (e.clientX - rect.left) / rect.width * g.width;
    if (x < g.x0 - 4 || x > g.x1 + 4) { hide(); return; }
    show(nearestIndex(msFor(x)));
  });
  svg.addEventListener("pointerleave", hide);
  svg.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft") { show(current <= 0 ? 0 : current - 1); e.preventDefault(); }
    else if (e.key === "ArrowRight") { show(current < 0 ? times.length - 1 : Math.min(times.length - 1, current + 1)); e.preventDefault(); }
    else if (e.key === "Escape") { hide(); }
  });
  svg.addEventListener("blur", hide);
})();
