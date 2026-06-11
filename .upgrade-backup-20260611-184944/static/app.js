const form = document.getElementById("forecast-form");
const cityInput = document.getElementById("city");
const daysInput = document.getElementById("days");
const suggestionsBox = document.getElementById("city-suggestions");
const statusBox = document.getElementById("status");
const dashboard = document.getElementById("dashboard");
const locationTitle = document.getElementById("location-title");
const updatedAt = document.getElementById("updated-at");
const currentCard = document.getElementById("current-card");
const dailyGrid = document.getElementById("daily-grid");
const hourlyGrid = document.getElementById("hourly-grid");
const forecastCount = document.getElementById("forecast-count");
const favoritesList = document.getElementById("favorites-list");
const recentList = document.getElementById("recent-list");
const favoriteButton = document.getElementById("favorite-button");
const refreshButton = document.getElementById("refresh-button");
const clearHistoryButton = document.getElementById("clear-history");
const unitToggle = document.getElementById("unit-toggle");
const themeToggle = document.getElementById("theme-toggle");

const state = {
    unit: localStorage.getItem("neutweather-unit") || "C",
    theme: localStorage.getItem("neutweather-theme") || "light",
    activeSuggestionIndex: -1,
    suggestions: [],
    currentQuery: { city: "Cairo,EG", days: "3" },
    currentLocationLabel: "Cairo,EG",
    currentData: null,
    suggestionController: null,
};

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

function readStorage(key) {
    try {
        return JSON.parse(localStorage.getItem(key)) || [];
    } catch {
        return [];
    }
}

function writeStorage(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

function getFavorites() {
    return readStorage("neutweather-favorites");
}

function getRecentSearches() {
    return readStorage("neutweather-recent");
}

function showStatus(message, type = "loading") {
    statusBox.textContent = message;
    statusBox.className = `status-card ${type}`;
}

function hideStatus() {
    statusBox.className = "status-card hidden";
}

function formatTemperature(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "--";
    }

    const celsius = Number(value);
    const displayValue = state.unit === "F" ? (celsius * 9) / 5 + 32 : celsius;
    return `${Math.round(displayValue)}°${state.unit}`;
}

function formatMetric(value, suffix = "") {
    if (value === null || value === undefined || value === "") {
        return "--";
    }
    return `${value}${suffix}`;
}

function parseForecastDate(item) {
    if (item.date_time) {
        return new Date(item.date_time.replace(" ", "T"));
    }

    if (item.timestamp) {
        return new Date(Number(item.timestamp) * 1000);
    }

    return new Date();
}

function weatherSymbol(condition = "") {
    const value = condition.toLowerCase();

    if (value.includes("thunder")) return "⛈";
    if (value.includes("snow")) return "❄";
    if (value.includes("rain") || value.includes("drizzle")) return "🌧";
    if (value.includes("mist") || value.includes("fog") || value.includes("haze")) return "🌫";
    if (value.includes("cloud")) return "☁";
    if (value.includes("clear")) return "☀";
    return "⛅";
}

function dayLabel(date) {
    return date.toLocaleDateString(undefined, { weekday: "short" });
}

function timeLabel(date) {
    return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function dateKey(date) {
    return date.toISOString().slice(0, 10);
}

function closeSuggestions() {
    suggestionsBox.innerHTML = "";
    suggestionsBox.classList.add("hidden");
    state.activeSuggestionIndex = -1;
}

function selectSuggestion(value) {
    cityInput.value = value;
    closeSuggestions();
    cityInput.focus();
}

function highlightSuggestion() {
    suggestionsBox.querySelectorAll(".suggestion-item").forEach((item, index) => {
        item.classList.toggle("active", index === state.activeSuggestionIndex);
    });
}

function renderSuggestions() {
    if (!state.suggestions.length) {
        closeSuggestions();
        return;
    }

    suggestionsBox.innerHTML = state.suggestions
        .map((item, index) => {
            const value = `${item.city},${item.code}`;
            return `
                <li class="suggestion-item" role="option" data-index="${index}" data-value="${escapeHtml(value)}">
                    <strong>${escapeHtml(item.city)}</strong>
                    <small>${escapeHtml(item.country)} · ${escapeHtml(item.code)}</small>
                </li>
            `;
        })
        .join("");

    suggestionsBox.classList.remove("hidden");
    state.activeSuggestionIndex = -1;

    suggestionsBox.querySelectorAll(".suggestion-item").forEach((item) => {
        item.addEventListener("click", () => selectSuggestion(item.dataset.value));
    });
}

async function fetchSuggestions(query) {
    const value = query.trim();

    if (!value) {
        closeSuggestions();
        return;
    }

    if (state.suggestionController) {
        state.suggestionController.abort();
    }

    state.suggestionController = new AbortController();

    try {
        const params = new URLSearchParams({ q: value, limit: "8" });
        const response = await fetch(`/cities?${params.toString()}`, {
            signal: state.suggestionController.signal,
        });

        if (!response.ok) return;

        const data = await response.json();
        state.suggestions = data.suggestions || [];
        renderSuggestions();
    } catch (error) {
        if (error.name !== "AbortError") {
            closeSuggestions();
        }
    }
}

function debounce(callback, wait = 180) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => callback(...args), wait);
    };
}

const debouncedSuggestions = debounce(fetchSuggestions);

function groupDailyForecast(items) {
    const groups = new Map();

    items.forEach((item) => {
        const date = parseForecastDate(item);
        const key = dateKey(date);

        if (!groups.has(key)) {
            groups.set(key, []);
        }

        groups.get(key).push(item);
    });

    return [...groups.entries()].map(([key, values]) => {
        const temperatures = values
            .map((item) => Number(item.temperature_c))
            .filter((value) => !Number.isNaN(value));

        const representative = values[Math.floor(values.length / 2)] || values[0];

        return {
            date: new Date(`${key}T12:00:00`),
            condition: representative.condition,
            min: temperatures.length ? Math.min(...temperatures) : null,
            max: temperatures.length ? Math.max(...temperatures) : null,
        };
    });
}

function renderCurrent(item) {
    const condition = item.condition || "Weather update";
    const visibilityKm = item.visibility_m ? (Number(item.visibility_m) / 1000).toFixed(1) : null;

    currentCard.innerHTML = `
        <div class="current-main">
            <span class="weather-symbol" aria-hidden="true">${weatherSymbol(condition)}</span>
            <div>
                <p class="current-temp">${formatTemperature(item.temperature_c)}</p>
                <p class="current-condition">${escapeHtml(condition)}</p>
            </div>
        </div>
        <div class="current-details">
            <span>Feels like ${formatTemperature(item.feels_like_c)}</span>
            <span>Cloud cover ${formatMetric(item.cloudiness, "%")}</span>
            <span>Visibility ${visibilityKm ? `${visibilityKm} km` : "--"}</span>
        </div>
    `;

    document.getElementById("humidity-value").textContent = formatMetric(item.humidity, "%");
    document.getElementById("wind-value").textContent = formatMetric(item.wind_speed, " m/s");
    document.getElementById("pressure-value").textContent = formatMetric(item.pressure_hpa, " hPa");
    document.getElementById("rain-value").textContent = formatMetric(item.rain_probability, "%");
}

function renderDaily(items) {
    const daily = groupDailyForecast(items);

    dailyGrid.innerHTML = daily
        .map((item) => `
            <article class="daily-card">
                <span class="card-day">${escapeHtml(dayLabel(item.date))}</span>
                <span class="card-symbol" aria-hidden="true">${weatherSymbol(item.condition)}</span>
                <strong class="daily-temp">${formatTemperature(item.max)}</strong>
                <span class="card-condition">Low ${formatTemperature(item.min)} · ${escapeHtml(item.condition || "Weather update")}</span>
            </article>
        `)
        .join("");
}

function renderHourly(items) {
    hourlyGrid.innerHTML = items
        .slice(0, 12)
        .map((item) => {
            const date = parseForecastDate(item);
            return `
                <article class="hourly-card">
                    <span class="hour-label">${escapeHtml(timeLabel(date))}</span>
                    <span class="card-symbol" aria-hidden="true">${weatherSymbol(item.condition)}</span>
                    <strong class="hourly-temp">${formatTemperature(item.temperature_c)}</strong>
                    <span class="card-condition">${escapeHtml(item.condition || "Weather update")}</span>
                </article>
            `;
        })
        .join("");
}

function renderDashboard(data) {
    const items = data.forecast || [];
    const current = items[0];

    if (!current) {
        throw new Error("No weather entries were returned for this city.");
    }

    const location = data.country ? `${data.city}, ${data.country}` : data.city;
    state.currentLocationLabel = location;
    state.currentData = data;

    locationTitle.textContent = location;
    updatedAt.textContent = `Updated ${new Date(data.generated_at).toLocaleString()}`;
    forecastCount.textContent = `${data.forecast_count} forecast entries`;

    renderCurrent(current);
    renderDaily(items);
    renderHourly(items);
    renderCollections();
    updateFavoriteButton();

    dashboard.classList.remove("hidden");
}

function addRecentSearch(city) {
    const recent = getRecentSearches().filter((item) => item.toLowerCase() !== city.toLowerCase());
    recent.unshift(city);
    writeStorage("neutweather-recent", recent.slice(0, 6));
}

function updateFavoriteButton() {
    const favorites = getFavorites();
    const isFavorite = favorites.some(
        (item) => item.toLowerCase() === state.currentQuery.city.toLowerCase()
    );

    favoriteButton.textContent = isFavorite ? "★ Saved city" : "☆ Save city";
}

function toggleFavorite() {
    const city = state.currentQuery.city;
    const favorites = getFavorites();
    const index = favorites.findIndex((item) => item.toLowerCase() === city.toLowerCase());

    if (index >= 0) {
        favorites.splice(index, 1);
    } else {
        favorites.unshift(city);
    }

    writeStorage("neutweather-favorites", favorites.slice(0, 8));
    updateFavoriteButton();
    renderCollections();
}

function createSearchChip(city) {
    return `<button type="button" data-search-city="${escapeHtml(city)}">${escapeHtml(city)}</button>`;
}

function renderCollection(container, values, emptyText) {
    container.innerHTML = values.length
        ? values.map(createSearchChip).join("")
        : `<p class="empty-copy">${escapeHtml(emptyText)}</p>`;
}

function renderCollections() {
    renderCollection(favoritesList, getFavorites(), "Save useful cities for faster access.");
    renderCollection(recentList, getRecentSearches(), "Your recent searches will appear here.");

    document.querySelectorAll("[data-search-city]").forEach((button) => {
        button.addEventListener("click", () => {
            cityInput.value = button.dataset.searchCity;
            loadForecast(button.dataset.searchCity, daysInput.value);
        });
    });
}

async function loadForecast(city, days) {
    const normalizedCity = city.trim();

    if (!normalizedCity) return;

    closeSuggestions();
    showStatus("Loading the latest weather forecast...", "loading");

    try {
        const params = new URLSearchParams({ city: normalizedCity, days: String(days) });
        const response = await fetch(`/forecast?${params.toString()}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to load this forecast.");
        }

        state.currentQuery = { city: normalizedCity, days: String(days) };
        addRecentSearch(normalizedCity);
        renderDashboard(data);
        hideStatus();
    } catch (error) {
        showStatus(error.message, "error");
    }
}

function applyTheme() {
    document.body.classList.toggle("dark-mode", state.theme === "dark");
    themeToggle.textContent = state.theme === "dark" ? "☀" : "☾";
}

function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("neutweather-theme", state.theme);
    applyTheme();
}

function toggleUnit() {
    state.unit = state.unit === "C" ? "F" : "C";
    localStorage.setItem("neutweather-unit", state.unit);
    unitToggle.textContent = `°${state.unit}`;

    if (state.currentData) {
        renderDashboard(state.currentData);
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    loadForecast(cityInput.value, daysInput.value);
});

cityInput.addEventListener("input", () => debouncedSuggestions(cityInput.value));

cityInput.addEventListener("keydown", (event) => {
    if (suggestionsBox.classList.contains("hidden")) return;

    if (event.key === "ArrowDown") {
        event.preventDefault();
        state.activeSuggestionIndex = (state.activeSuggestionIndex + 1) % state.suggestions.length;
        highlightSuggestion();
    }

    if (event.key === "ArrowUp") {
        event.preventDefault();
        state.activeSuggestionIndex = state.activeSuggestionIndex <= 0
            ? state.suggestions.length - 1
            : state.activeSuggestionIndex - 1;
        highlightSuggestion();
    }

    if (event.key === "Enter" && state.activeSuggestionIndex >= 0) {
        event.preventDefault();
        const item = state.suggestions[state.activeSuggestionIndex];
        selectSuggestion(`${item.city},${item.code}`);
    }

    if (event.key === "Escape") {
        closeSuggestions();
    }
});

document.addEventListener("click", (event) => {
    if (!event.target.closest(".autocomplete")) {
        closeSuggestions();
    }
});

document.querySelectorAll("[data-city]").forEach((button) => {
    button.addEventListener("click", () => {
        cityInput.value = button.dataset.city;
        loadForecast(button.dataset.city, daysInput.value);
    });
});

favoriteButton.addEventListener("click", toggleFavorite);
refreshButton.addEventListener("click", () => loadForecast(state.currentQuery.city, state.currentQuery.days));
clearHistoryButton.addEventListener("click", () => {
    writeStorage("neutweather-recent", []);
    renderCollections();
});
unitToggle.addEventListener("click", toggleUnit);
themeToggle.addEventListener("click", toggleTheme);

applyTheme();
unitToggle.textContent = `°${state.unit}`;
renderCollections();
loadForecast("Cairo,EG", 3);
