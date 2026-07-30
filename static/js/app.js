const form = document.querySelector("#assessment-form");

const translations = {
  en: {
    nav_assess: "Assess", nav_route: "Route planner", nav_ai: "AI designer", nav_aircraft: "Aircraft", nav_history: "History",
    nav_about: "About", nav_ai_route: "AI route", network_label: "FLIGHTCHECK AVIATION NETWORK",
    network_status: "PLANNING SYSTEM ONLINE", ai_eyebrow: "AI-assisted route exploration",
    ai_title: "Tell it the mission.<br>Compare the tradeoff.",
    ai_intro: "Enter the airports, aircraft, and loading. FlightCheck asks the AI for a candidate optimized for lowest estimated fuel or fastest time, then validates each waypoint before placing it on the map.",
    mission: "MISSION", where_fly: "Where will you fly?", departure: "Departure airport", arrival: "Arrival airport",
    aircraft_loading: "AIRCRAFT & LOADING", carrying: "What are you carrying?", aircraft_type: "Aircraft type",
    performance: "PERFORMANCE", poh_numbers: "Use your POH numbers.", objective: "OBJECTIVE",
    prioritize: "What should the agent prioritize?", lowest_fuel: "Lowest estimated fuel",
    lowest_fuel_help: "Prefer the candidate with the lowest calculated cruise fuel.", fastest: "Fastest estimated time",
    fastest_help: "Prefer the shortest practical candidate route.", generate_route: "Generate candidate route"
    ,landing_kicker: "STUDENT PILOT DECISION SUPPORT", landing_title: "Plan with clarity.<br><em>Fly with purpose.</em>",
    landing_intro: "FlightCheck brings preflight risk reflection, route planning, weather factors, fuel estimates, and AI-assisted waypoint exploration into one focused student-pilot workspace.",
    start_briefing: "Start briefing", route_plan: "Route plan", proof_risk: "PAVE risk review",
    proof_route: "AI route candidates", proof_history: "Saved planning history",
    mission_heading: "One place to slow down before you speed up.",
    mission_copy: "Use structured questions to recognize risk, compare route tradeoffs, and prepare what must be verified with official aviation sources and your instructor.",
    feature_route: "Route intelligence", feature_route_copy: "Waypoints, altitude targets, estimated time, and fuel.",
    feature_decision: "Decision discipline", feature_decision_copy: "PAVE factors presented as an intentional briefing flow.",
    aircraft_library: "Aircraft"
  },
  zh: {
    nav_assess: "风险评估", nav_route: "手动航线", nav_ai: "AI 航线设计", nav_aircraft: "飞机资料", nav_history: "历史记录",
    nav_about: "关于", nav_ai_route: "AI 航线", network_label: "FLIGHTCHECK 航空网络",
    network_status: "规划系统在线", ai_eyebrow: "AI 辅助航线探索",
    ai_title: "输入飞行任务。<br>比较时间与燃油。",
    ai_intro: "输入起飞机场、到达机场、机型和载重。FlightCheck 会根据最低燃油或最快时间生成候选航线，并验证每一个航点后再显示在地图上。",
    mission: "飞行任务", where_fly: "你准备飞往哪里？", departure: "起飞机场", arrival: "到达机场",
    aircraft_loading: "飞机与载重", carrying: "本次飞行装载多少？", aircraft_type: "飞机型号",
    performance: "性能数据", poh_numbers: "请使用 POH 中的数据。", objective: "优化目标",
    prioritize: "AI 应优先考虑什么？", lowest_fuel: "最低预计燃油",
    lowest_fuel_help: "优先选择预计巡航燃油最少的候选航线。", fastest: "最快预计时间",
    fastest_help: "优先选择距离较短的合理候选航线。", generate_route: "生成候选航线"
    ,landing_kicker: "学生飞行员决策支持", landing_title: "清晰规划。<br><em>目标明确地飞行。</em>",
    landing_intro: "FlightCheck 将飞行前风险检查、航线规划、天气因素、燃油估算和 AI 航点探索整合到一个专注的学生飞行员工作空间。",
    start_briefing: "开始飞行简报", route_plan: "规划航线", proof_risk: "PAVE 风险检查",
    proof_route: "AI 候选航线", proof_history: "保存规划记录",
    mission_heading: "在加速之前，先给自己一个慢下来思考的地方。",
    mission_copy: "通过结构化问题识别风险、比较航线方案，并明确需要使用官方航空资料和教员进一步核实的内容。",
    feature_route: "航线智能", feature_route_copy: "航点、目标高度、预计时间与燃油。",
    feature_decision: "决策纪律", feature_decision_copy: "将 PAVE 因素组织成有步骤的飞行简报。",
    aircraft_library: "飞机资料"
  },
  es: {
    nav_assess: "Evaluar", nav_route: "Planificador", nav_ai: "Diseñador IA", nav_aircraft: "Aeronaves", nav_history: "Historial",
    nav_about: "Acerca de", nav_ai_route: "Ruta IA", network_label: "RED DE AVIACIÓN FLIGHTCHECK",
    network_status: "SISTEMA DE PLANIFICACIÓN ACTIVO", ai_eyebrow: "Exploración de rutas asistida por IA",
    ai_title: "Define la misión.<br>Compara el resultado.",
    ai_intro: "Introduce los aeropuertos, la aeronave y la carga. FlightCheck solicita una ruta candidata optimizada por combustible o tiempo y valida cada punto antes de mostrarlo en el mapa.",
    mission: "MISIÓN", where_fly: "¿Adónde vas a volar?", departure: "Aeropuerto de salida", arrival: "Aeropuerto de llegada",
    aircraft_loading: "AERONAVE Y CARGA", carrying: "¿Qué vas a transportar?", aircraft_type: "Tipo de aeronave",
    performance: "RENDIMIENTO", poh_numbers: "Utiliza los datos del POH.", objective: "OBJETIVO",
    prioritize: "¿Qué debe priorizar el agente?", lowest_fuel: "Menor combustible estimado",
    lowest_fuel_help: "Prefiere la ruta con menor consumo de crucero calculado.", fastest: "Menor tiempo estimado",
    fastest_help: "Prefiere la ruta candidata práctica más corta.", generate_route: "Generar ruta candidata"
    ,landing_kicker: "APOYO PARA PILOTOS ESTUDIANTES", landing_title: "Planifica con claridad.<br><em>Vuela con propósito.</em>",
    landing_intro: "FlightCheck reúne evaluación de riesgos, rutas, meteorología, combustible y exploración de puntos asistida por IA en un solo espacio.",
    start_briefing: "Iniciar briefing", route_plan: "Planificar ruta", proof_risk: "Evaluación PAVE",
    proof_route: "Rutas candidatas IA", proof_history: "Historial guardado",
    mission_heading: "Un lugar para reducir la velocidad antes de acelerar.",
    mission_copy: "Usa preguntas estructuradas para reconocer riesgos, comparar rutas y preparar lo que debe verificarse con fuentes oficiales y tu instructor.",
    feature_route: "Inteligencia de ruta", feature_route_copy: "Puntos, altitudes, tiempo y combustible estimados.",
    feature_decision: "Disciplina de decisión", feature_decision_copy: "Factores PAVE organizados como un briefing intencional.",
    aircraft_library: "Aeronaves"
  }
};

const languageSelect = document.querySelector("#language-select");
function applyLanguage(language) {
  const chosen = translations[language] ? language : "en";
  document.documentElement.lang = chosen === "zh" ? "zh-CN" : chosen;
  document.documentElement.dataset.language = chosen;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const translated = translations[chosen][element.dataset.i18n];
    if (translated) element.textContent = translated;
  });
  document.querySelectorAll("[data-i18n-html]").forEach((element) => {
    const translated = translations[chosen][element.dataset.i18nHtml];
    if (translated) element.innerHTML = translated;
  });
  if (languageSelect) languageSelect.value = chosen;
  window.localStorage.setItem("flightcheck-language", chosen);
}
if (languageSelect) {
  languageSelect.addEventListener("change", () => applyLanguage(languageSelect.value));
  applyLanguage(window.localStorage.getItem("flightcheck-language") || "en");
}

if (form) {
  const steps = [...form.querySelectorAll(".form-step")];
  const next = document.querySelector("#next-button");
  const back = document.querySelector("#back-button");
  const submit = document.querySelector("#submit-button");
  const progress = document.querySelector("#progress-bar");
  const progressLabel = document.querySelector("#progress-label");
  const hint = document.querySelector("#step-hint");
  const hints = ["Pilot readiness", "Aircraft status", "Flight environment", "External pressures"];
  let activeStep = 0;

  function showStep(index) {
    activeStep = Math.max(0, Math.min(steps.length - 1, index));
    steps.forEach((step, stepIndex) => step.classList.toggle("active", stepIndex === activeStep));
    progress.style.width = `${((activeStep + 1) / steps.length) * 100}%`;
    progressLabel.textContent = `${activeStep + 1} of ${steps.length}`;
    hint.textContent = hints[activeStep];
    back.hidden = activeStep === 0;
    next.hidden = activeStep === steps.length - 1;
    submit.hidden = activeStep !== steps.length - 1;
    steps[activeStep].scrollIntoView({ behavior: "smooth", block: "center" });
  }

  next.addEventListener("click", () => {
    const inputs = [...steps[activeStep].querySelectorAll("input")];
    if (inputs.every((input) => input.reportValidity())) showStep(activeStep + 1);
  });
  back.addEventListener("click", () => showStep(activeStep - 1));

  form.querySelectorAll('input[type="range"][data-output]').forEach((input) => {
    const output = document.querySelector(`#${input.dataset.output}`);
    const update = () => { output.textContent = `${input.value}${input.dataset.suffix || ""}`; };
    input.addEventListener("input", update);
    update();
  });
}

document.querySelectorAll("[data-confirm-delete]").forEach((formElement) => {
  formElement.addEventListener("submit", (event) => {
    if (!window.confirm("Remove this assessment from your history?")) event.preventDefault();
  });
});

const navlogRows = document.querySelector("#navlog-rows");
if (navlogRows) {
  const departureInput = document.querySelector('input[name="departure"]');
  const destinationInput = document.querySelector('input[name="destination"]');
  const checkpointsInput = document.querySelector('input[name="checkpoints"]');

  function routeIdentifiers() {
    const middle = checkpointsInput.value
      .replace(/\n/g, ",")
      .split(/[\s,]+/)
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);
    return [departureInput.value.trim().toUpperCase(), ...middle, destinationInput.value.trim().toUpperCase()]
      .filter(Boolean);
  }

  function savedNavlogValues() {
    const saved = new Map();
    navlogRows.querySelectorAll(".navlog-editor-row").forEach((row) => {
      const key = row.querySelector('[name="leg_waypoint"]').value;
      saved.set(key, {
        altitude: row.querySelector('[name="leg_altitude"]').value,
        facility: row.querySelector('[name="leg_facility"]').value,
        frequency: row.querySelector('[name="leg_frequency"]').value,
        notes: row.querySelector('[name="leg_notes"]').value,
      });
    });
    return saved;
  }

  function createInput(name, placeholder, type = "text") {
    const input = document.createElement("input");
    input.name = name;
    input.type = type;
    input.placeholder = placeholder;
    return input;
  }

  function renderNavlog() {
    const saved = savedNavlogValues();
    navlogRows.replaceChildren();
    routeIdentifiers().forEach((identifier, index) => {
      const values = saved.get(identifier) || {};
      const row = document.createElement("div");
      row.className = "navlog-editor-row";

      const waypoint = document.createElement("div");
      waypoint.className = "waypoint-cell";
      waypoint.innerHTML = `<span>${index + 1}</span><strong>${identifier}</strong>`;
      const hidden = createInput("leg_waypoint", "", "hidden");
      hidden.value = identifier;
      waypoint.appendChild(hidden);

      const altitude = createInput("leg_altitude", "e.g. 5,500", "number");
      altitude.min = "0";
      altitude.max = "60000";
      altitude.step = "100";
      altitude.value = values.altitude || "";
      const facility = createInput("leg_facility", "e.g. New York Approach");
      facility.maxLength = 80;
      facility.value = values.facility || "";
      const frequency = createInput("leg_frequency", "e.g. 118.40");
      frequency.inputMode = "decimal";
      frequency.maxLength = 12;
      frequency.value = values.frequency || "";
      const notes = createInput("leg_notes", "e.g. climb, report position");
      notes.maxLength = 200;
      notes.value = values.notes || "";

      row.append(waypoint, altitude, facility, frequency, notes);
      navlogRows.appendChild(row);
    });
  }

  [departureInput, destinationInput, checkpointsInput].forEach((input) => input.addEventListener("input", renderNavlog));
  renderNavlog();
}

const aircraftGrid = document.querySelector("#aircraft-grid");
if (aircraftGrid) {
  const manufacturer = document.querySelector("#filter-manufacturer");
  const range = document.querySelector("#filter-range");
  const aircraftClass = document.querySelector("#filter-class");
  const search = document.querySelector("#filter-search");
  const clear = document.querySelector("#clear-aircraft-filters");
  const count = document.querySelector("#aircraft-count");
  const empty = document.querySelector("#aircraft-empty");
  const cards = [...aircraftGrid.querySelectorAll(".aircraft-card")];

  function filterAircraft() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const matches = (manufacturer.value === "all" || card.dataset.maker === manufacturer.value)
        && (range.value === "all" || card.dataset.range === range.value)
        && (aircraftClass.value === "all" || card.dataset.class === aircraftClass.value)
        && (!query || card.dataset.name.includes(query) || card.dataset.maker.toLowerCase().includes(query));
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = visible;
    empty.hidden = visible !== 0;
  }

  function clearAircraftFilters() {
    manufacturer.value = "all";
    range.value = "all";
    aircraftClass.value = "all";
    search.value = "";
    filterAircraft();
  }

  [manufacturer, range, aircraftClass].forEach((control) => control.addEventListener("change", filterAircraft));
  search.addEventListener("input", filterAircraft);
  clear.addEventListener("click", clearAircraftFilters);
  empty.querySelector("button").addEventListener("click", clearAircraftFilters);
}

const routeAircraftData = document.querySelector("#aircraft-selector-data");
if (routeAircraftData) {
  const makerSelect = document.querySelector("#route-aircraft-maker");
  const familySelect = document.querySelector("#route-aircraft-family");
  const modelSelect = document.querySelector("#route-aircraft-model");
  let aircraftOptions = [];
  try {
    aircraftOptions = JSON.parse(routeAircraftData.textContent);
  } catch {
    aircraftOptions = [];
  }

  function replaceOptions(select, placeholder, values) {
    select.replaceChildren();
    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    select.appendChild(placeholderOption);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
    select.disabled = values.length === 0;
  }

  const makers = [...new Set(aircraftOptions.map((item) => item.maker))].sort();
  replaceOptions(makerSelect, "Choose manufacturer", makers);
  replaceOptions(familySelect, "Choose family", []);
  replaceOptions(modelSelect, "Choose model", []);

  makerSelect.addEventListener("change", () => {
    const families = [...new Set(
      aircraftOptions.filter((item) => item.maker === makerSelect.value).map((item) => item.family)
    )].sort();
    replaceOptions(familySelect, "Choose family", families);
    replaceOptions(modelSelect, "Choose model", []);
  });

  familySelect.addEventListener("change", () => {
    const models = aircraftOptions
      .filter((item) => item.maker === makerSelect.value && item.family === familySelect.value)
      .map((item) => item.name);
    replaceOptions(modelSelect, "Choose model", models);
  });
}
