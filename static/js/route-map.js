function initializeRouteMap() {
  if (typeof window.L === "undefined") return;
  document.querySelectorAll("[data-route-map]").forEach((container) => {
  const dataElement = document.querySelector(`#${container.dataset.routeMap}`);
  if (!dataElement) return;

  let points;
  try {
    points = JSON.parse(dataElement.textContent);
  } catch {
    container.textContent = "Route map data could not be read.";
    return;
  }
  if (!Array.isArray(points) || points.length < 2) return;

  const map = window.L.map(container, {
    scrollWheelZoom: false,
    zoomControl: true,
  });
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  const coordinates = points.map((point) => [point.lat, point.lon]);
  window.L.polyline(coordinates, {
    color: "#0f6075",
    weight: 4,
    opacity: 0.9,
    dashArray: "10 7",
  }).addTo(map);

  points.forEach((point) => {
    const icon = window.L.divIcon({
      className: "flight-waypoint-icon",
      html: `<span>${point.order}</span>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });
    window.L.marker([point.lat, point.lon], { icon })
      .addTo(map)
      .bindPopup(
        `<div class="map-popup"><small>WAYPOINT ${point.order}</small><strong>${point.id}</strong><span>${point.name}</span>${point.altitude ? `<b>${point.altitude.toLocaleString()} ft MSL</b>` : ""}${point.facility ? `<em>${point.facility}${point.frequency ? ` · ${point.frequency}` : ""}</em>` : ""}<code>${point.lat.toFixed(4)}, ${point.lon.toFixed(4)}</code></div>`
      );
  });

  map.fitBounds(coordinates, { padding: [45, 45], maxZoom: 9 });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeRouteMap);
} else {
  initializeRouteMap();
}
