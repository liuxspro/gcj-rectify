(function () {
  "use strict";

  // --- DOM refs ---
  var mapListEl = document.getElementById("map-list");
  var mapSelectEl = document.getElementById("map-select");
  var wmtsUrlEl = document.getElementById("wmts-url");
  var tileFormatEl = document.getElementById("tile-format");

  var maps = {};
  var mapKeys = [];
  var beforeMap = null;
  var afterMap = null;
  var compare = null;
  var currentMapId = null;

  // --- Vector tile style (OpenFreeMap bright) ---
  function vectorStyle() {
    return "https://tiles.openfreemap.org/styles/bright";
  }

  // --- Rectified tiles style ---
  function rectifiedStyle(mapId) {
    return {
      version: 8,
      sources: {
        rectified: {
          type: "raster",
          tiles: ["/tiles/" + mapId + "/{z}/{x}/{y}"],
          tileSize: 256,
        },
      },
      layers: [{ id: "rectified", type: "raster", source: "rectified" }],
    };
  }

  // --- Initialize or switch maps ---
  function setMaps(mapId) {
    var show = !!mapId;
    currentMapId = mapId;

    // Destroy previous compare and maps
    if (compare) {
      compare.remove();
      compare = null;
    }
    if (beforeMap) {
      beforeMap.remove();
      beforeMap = null;
    }
    if (afterMap) {
      afterMap.remove();
      afterMap = null;
    }

    var container = document.getElementById("comparison-container");

    // Clear container contents
    document.getElementById("before-map").innerHTML = "";
    document.getElementById("after-map").innerHTML = "";

    if (container) container.classList.add("is-loading");

    if (!show) return;

    var center = [117.147541, 34.238288];

    // Create before map (rectified tiles, left side)
    beforeMap = new maplibregl.Map({
      container: "before-map",
      style: rectifiedStyle(mapId),
      center: center,
      zoom: 12,
      attributionControl: false,
    });

    // Create after map (vector tile, right side)
    afterMap = new maplibregl.Map({
      container: "after-map",
      style: vectorStyle(),
      center: center,
      zoom: 12,
      attributionControl: false,
    });

    // Create compare immediately; maps load tiles asynchronously
    compare = new maplibregl.Compare(beforeMap, afterMap, container, {
      orientation: "vertical",
    });
    if (container) container.classList.remove("is-loading");
  }

  // --- Fetch config ---
  (async function loadConfig() {
    try {
      var res = await fetch("/config");
      if (!res.ok) throw new Error("HTTP " + res.status);
      var config = await res.json();
      wmtsUrlEl.textContent = window.location.origin + "/wmts";

      maps = config.maps || {};
      mapKeys = Object.keys(maps);

      var listHtml = "";
      for (var i = 0; i < mapKeys.length; i++) {
        var key = mapKeys[i];
        var m = maps[key];
        listHtml += '<li><span class="map-label">' +
          key +
          "</span> " +
          escapeHtml(m.name) +
          " (缩放: " +
          (m.min_zoom || "?") +
          "\u2013" +
          (m.max_zoom || "?") +
          ")</li>";
      }
      mapListEl.innerHTML = listHtml ||
        '<li style="color: var(--color-text-muted); padding: 5px 0;">暂无地图配置</li>';

      var optHtml = "";
      for (var j = 0; j < mapKeys.length; j++) {
        var k = mapKeys[j];
        var m2 = maps[k];
        optHtml += '<option value="' +
          k +
          '">' +
          escapeHtml(m2.name) +
          " (" +
          k +
          ")</option>";
      }
      mapSelectEl.innerHTML = optHtml;
      mapSelectEl.disabled = false;

      if (mapKeys.length > 0) {
        mapSelectEl.value = mapKeys[0];
        setMaps(mapKeys[0]);
      }
    } catch (err) {
      mapListEl.innerHTML =
        '<li style="color: var(--color-error);">❌ 无法获取地图列表</li>';
      mapSelectEl.innerHTML = '<option value="">加载失败</option>';
      mapSelectEl.disabled = true;
      console.error("Failed to fetch config:", err);
    }
  })();

  mapSelectEl.addEventListener("change", function () {
    setMaps(this.value || null);
  });

  // --- Utility: escape HTML to prevent XSS ---
  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
