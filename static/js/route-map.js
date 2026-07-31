function greatCircleLeg(start, end, steps = 32) {
  const toRadians = (degrees) => degrees * Math.PI / 180;
  const toDegrees = (radians) => radians * 180 / Math.PI;
  const lat1 = toRadians(start.lat);
  const lon1 = toRadians(start.lon);
  const lat2 = toRadians(end.lat);
  const lon2 = toRadians(end.lon);
  const angularDistance = 2 * Math.asin(Math.sqrt(
    Math.sin((lat2 - lat1) / 2) ** 2
    + Math.cos(lat1) * Math.cos(lat2) * Math.sin((lon2 - lon1) / 2) ** 2
  ));
  if (angularDistance < 1e-9) return [[start.lat, start.lon]];

  const points = [];
  let previousLongitude = start.lon;
  for (let index = 0; index <= steps; index += 1) {
    const fraction = index / steps;
    const a = Math.sin((1 - fraction) * angularDistance) / Math.sin(angularDistance);
    const b = Math.sin(fraction * angularDistance) / Math.sin(angularDistance);
    const x = a * Math.cos(lat1) * Math.cos(lon1) + b * Math.cos(lat2) * Math.cos(lon2);
    const y = a * Math.cos(lat1) * Math.sin(lon1) + b * Math.cos(lat2) * Math.sin(lon2);
    const z = a * Math.sin(lat1) + b * Math.sin(lat2);
    const latitude = toDegrees(Math.atan2(z, Math.sqrt(x * x + y * y)));
    let longitude = toDegrees(Math.atan2(y, x));
    while (longitude - previousLongitude > 180) longitude -= 360;
    while (longitude - previousLongitude < -180) longitude += 360;
    points.push([latitude, longitude]);
    previousLongitude = longitude;
  }
  return points;
}

function greatCircleRoute(points) {
  const coordinates = [];
  points.slice(0, -1).forEach((point, index) => {
    const leg = greatCircleLeg(point, points[index + 1]);
    coordinates.push(...(index === 0 ? leg : leg.slice(1)));
  });
  return coordinates;
}

function unwrapRouteLongitudes(points) {
  let previousLongitude = Number(points[0].lon);
  return points.map((point, index) => {
    let longitude = Number(point.lon);
    if (index > 0) {
      while (longitude - previousLongitude > 180) longitude -= 360;
      while (longitude - previousLongitude < -180) longitude += 360;
    }
    previousLongitude = longitude;
    return { ...point, lon: longitude };
  });
}

function escapeMapText(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
}

function initializeRouteMap() {
  if (typeof window.L === "undefined") {
    document.querySelectorAll("[data-route-map]").forEach((container) => {
      container.innerHTML = '<div class="route-map-error"><strong>Map could not load.</strong><span>The waypoint list below is still available. Refresh the page to try again.</span></div>';
    });
    return;
  }
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

  const displayPoints = unwrapRouteLongitudes(points);
  const coordinates = greatCircleRoute(displayPoints);
  window.L.polyline(coordinates, {
    color: "#0f6075",
    weight: 4,
    opacity: 0.9,
    dashArray: "10 7",
  }).addTo(map);

  points.forEach((point, pointIndex) => {
    const icon = window.L.divIcon({
      className: "flight-waypoint-icon",
      html: `<span>${point.order}</span>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });
    const altitudeLabel = point.altitude
      ? `${Number(point.altitude).toLocaleString()} ft`
      : (point.elevation_ft !== null && point.elevation_ft !== undefined
        ? `FIELD ${Number(point.elevation_ft).toLocaleString()} ft`
        : "ALT TBD");
    window.L.marker([point.lat, displayPoints[pointIndex].lon], { icon })
      .addTo(map)
      .bindTooltip(
        `<b>${escapeMapText(point.id)}</b><span>${escapeMapText(altitudeLabel)}</span>`,
        { permanent: true, direction: "top", offset: [0, -15], className: "flight-waypoint-label" }
      )
      .bindPopup(
        `<div class="map-popup"><small>WAYPOINT ${escapeMapText(point.order)}</small><strong>${escapeMapText(point.id)}</strong><span>${escapeMapText(point.name)}</span>${point.elevation_ft !== null && point.elevation_ft !== undefined ? `<b>Field elevation · ${Number(point.elevation_ft).toLocaleString()} ft MSL</b>` : ""}${point.altitude ? `<b>Target altitude · ${Number(point.altitude).toLocaleString()} ft MSL</b>` : ""}${point.forecast_wind ? `<em>Forecast wind · ${escapeMapText(point.forecast_wind)}</em>` : ""}${point.facility ? `<em>${escapeMapText(point.facility)}${point.frequency ? ` · ${escapeMapText(point.frequency)}` : ""}</em>` : ""}<code>${Number(point.lat).toFixed(4)}, ${Number(point.lon).toFixed(4)}</code></div>`
      );
  });

  const legend = window.L.control({ position: "bottomleft" });
  legend.onAdd = () => {
    const element = window.L.DomUtil.create("div", "route-map-legend");
    element.innerHTML = "<b>GEODESIC ROUTE</b><span>Great-circle legs between verified waypoints</span>";
    return element;
  };
  legend.addTo(map);

  map.fitBounds(coordinates, { padding: [55, 55], maxZoom: 9 });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeRouteMap);
} else {
  initializeRouteMap();
}
