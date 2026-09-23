import { useState } from "react";
import { CapacitorHttp } from "@capacitor/core";
import "./App.css";

// API base URL is configurable per environment.
//
// - Development (.env.development) points at the local FastAPI backend.
// - Production (.env.production) points at the deployed backend.
//
// If VITE_API_BASE_URL is not provided, fall back to the existing
// production backend so the app keeps working exactly as before.

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "https://weathergpt-backend-2udp.onrender.com";

function App() {
  const [city, setCity] = useState("Chennai");
  const [weather, setWeather] = useState(null);
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [error, setError] = useState("");

  // --------------------------------------------------
  // Native GET request
  // --------------------------------------------------

  async function getWeatherFromAPI(cityName) {
    const response = await CapacitorHttp.get({
      url: `${API_BASE_URL}/api/weather`,
      params: {
        city: cityName,
      },
      headers: {
        Accept: "application/json",
      },
      connectTimeout: 10000,
      readTimeout: 15000,
    });

    if (response.status < 200 || response.status >= 300) {
      throw new Error(`Weather server returned ${response.status}`);
    }

    return response.data;
  }

  // --------------------------------------------------
  // Native POST request
  // --------------------------------------------------

  async function askAIFromAPI(prompt) {
    const response = await CapacitorHttp.post({
      url: `${API_BASE_URL}/api/chat`,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      data: {
        message: prompt,
      },
      connectTimeout: 10000,
      readTimeout: 30000,
    });

    if (response.status < 200 || response.status >= 300) {
      throw new Error(`AI server returned ${response.status}`);
    }

    return response.data;
  }

  // --------------------------------------------------
  // Search weather
  // --------------------------------------------------

  async function searchWeather() {
    if (!city.trim()) return;

    setWeatherLoading(true);
    setError("");
    setReply("");

    try {
      const data = await getWeatherFromAPI(city.trim());

      if (!data || data.error) {
        throw new Error(data?.error || "Unable to get weather");
      }

      setWeather(data);
    } catch (err) {
      console.error("Weather error:", err);

      setWeather(null);

      setError(
        `Failed to fetch weather: ${
          err?.message || "Unknown error"
        }`
      );
    } finally {
      setWeatherLoading(false);
    }
  }

  // --------------------------------------------------
  // Ask WeatherGPT
  // --------------------------------------------------

  async function askWeatherGPT() {
    if (!message.trim()) return;

    setLoading(true);
    setError("");

    try {
      let weatherContext = "";

      if (weather) {
        const current = weather.current;
        const daily = weather.daily;

        const sevenDayForecast = daily.time
          .map(
            (date, index) =>
              `${date}: Minimum ${daily.temperature_2m_min[index]}°C, Maximum ${daily.temperature_2m_max[index]}°C, Rain probability ${daily.precipitation_probability_max[index]}%, UV Index ${daily.uv_index_max[index]}`
          )
          .join("\n");

        const tomorrowForecast = `
Date: ${daily.time[1]}
Minimum temperature: ${daily.temperature_2m_min[1]}°C
Maximum temperature: ${daily.temperature_2m_max[1]}°C
Rain probability: ${daily.precipitation_probability_max[1]}%
UV Index: ${daily.uv_index_max[1]}
`;

        weatherContext = `
REAL WEATHER DATA
=================

Location:
${weather.location.city}, ${weather.location.country}

CURRENT WEATHER

Temperature: ${current.temperature_2m}°C
Feels like: ${current.apparent_temperature}°C
Humidity: ${current.relative_humidity_2m}%
Wind speed: ${current.wind_speed_10m} m/s
Precipitation: ${current.precipitation} mm
Weather code: ${current.weather_code}

TOMORROW'S FORECAST
===================

${tomorrowForecast}

7-DAY FORECAST
==============

${sevenDayForecast}
`;
      }

      const prompt = `
You are WeatherGPT.

${weatherContext}

USER QUESTION:

${message}

IMPORTANT RULES:

- Use the supplied real weather data when answering.
- Do not invent weather values.
- If the user asks about tomorrow, use tomorrow's forecast.
- If the user asks about another day, use the 7-day forecast when available.
- If the requested date is outside the supplied forecast, clearly say that the data is not available.
- Give practical advice when useful.
- Be friendly and concise.
`;

      const data = await askAIFromAPI(prompt);

      if (!data || !data.reply) {
        throw new Error("AI returned an empty response");
      }

      setReply(data.reply);
    } catch (err) {
      console.error("AI error:", err);

      setError(
        `AI request failed: ${
          err?.message || "Unknown error"
        }`
      );
    } finally {
      setLoading(false);
    }
  }

  // --------------------------------------------------
  // Keyboard handlers
  // --------------------------------------------------

  function handleChatKeyDown(e) {
    if (e.key === "Enter") {
      askWeatherGPT();
    }
  }

  function handleSearchKeyDown(e) {
    if (e.key === "Enter") {
      searchWeather();
    }
  }

  // --------------------------------------------------
  // Weather description
  // --------------------------------------------------

  function getWeatherDescription(code) {
    if (code === 0) return "Clear Sky";
    if (code === 1) return "Mainly Clear";
    if (code === 2) return "Partly Cloudy";
    if (code === 3) return "Overcast";
    if ([45, 48].includes(code)) return "Foggy";
    if ([51, 53, 55].includes(code)) return "Drizzle";
    if ([61, 63, 65].includes(code)) return "Rain";
    if ([71, 73, 75].includes(code)) return "Snow";
    if ([80, 81, 82].includes(code)) return "Rain Showers";
    if ([95, 96, 99].includes(code)) return "Thunderstorm";

    return "Mixed Weather";
  }

  // --------------------------------------------------
  // Weather icon
  // --------------------------------------------------

  function getWeatherIcon(code) {
    if (code === 0) return "☀️";
    if ([1, 2].includes(code)) return "🌤️";
    if (code === 3) return "☁️";
    if ([45, 48].includes(code)) return "🌫️";

    if (
      [51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)
    ) {
      return "🌧️";
    }

    if ([95, 96, 99].includes(code)) return "⛈️";
    if ([71, 73, 75].includes(code)) return "❄️";

    return "🌦️";
  }

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div className="app">

      <header className="header">

        <div className="logo">
          🌦️ <span>WeatherGPT</span>
        </div>

        <div className="search">

          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="Search city..."
          />

          <button onClick={searchWeather}>
            {weatherLoading ? "..." : "Search"}
          </button>

        </div>

      </header>

      <main className="container">

        {error && (
          <div className="error">
            ⚠️ {error}
          </div>
        )}

        {weather && (
          <>

            {/* Current weather */}

            <section className="hero">

              <div>

                <p className="location">
                  📍 {weather.location.city},{" "}
                  {weather.location.country}
                </p>

                <h1>
                  {Math.round(
                    weather.current.temperature_2m
                  )}°C
                </h1>

                <h2>
                  {getWeatherDescription(
                    weather.current.weather_code
                  )}
                </h2>

                <p className="feels">
                  Feels like{" "}
                  {Math.round(
                    weather.current.apparent_temperature
                  )}
                  °C
                </p>

              </div>

              <div className="weather-icon">
                {getWeatherIcon(
                  weather.current.weather_code
                )}
              </div>

            </section>

            {/* Stats */}

            <section className="stats">

              <div>
                <span>💧</span>
                <p>Humidity</p>
                <strong>
                  {weather.current.relative_humidity_2m}%
                </strong>
              </div>

              <div>
                <span>💨</span>
                <p>Wind</p>
                <strong>
                  {weather.current.wind_speed_10m} m/s
                </strong>
              </div>

              <div>
                <span>🌧️</span>
                <p>Rain</p>
                <strong>
                  {weather.current.precipitation} mm
                </strong>
              </div>

              <div>
                <span>🌡️</span>
                <p>Feels Like</p>
                <strong>
                  {Math.round(
                    weather.current.apparent_temperature
                  )}
                  °C
                </strong>
              </div>

            </section>

            {/* Tomorrow */}

            <section className="forecast">

              <h2>Tomorrow's Forecast</h2>

              <div className="hours">

                <div className="hour">

                  <p>{weather.daily.time[1]}</p>

                  <span>🌦️</span>

                  <strong>
                    {weather.daily.temperature_2m_max[1]}°C
                  </strong>

                  <p>
                    Low{" "}
                    {weather.daily.temperature_2m_min[1]}°C
                  </p>

                  <p>
                    🌧️{" "}
                    {
                      weather.daily
                        .precipitation_probability_max[1]
                    }%
                  </p>

                </div>

              </div>

            </section>

            {/* 7 days */}

            <section className="forecast">

              <h2>7-Day Forecast</h2>

              <div className="hours">

                {weather.daily.time.map(
                  (date, index) => (

                    <div
                      className="hour"
                      key={date}
                    >

                      <p>{date}</p>

                      <span>🌦️</span>

                      <strong>
                        {
                          weather.daily
                            .temperature_2m_max[index]
                        }°C
                      </strong>

                      <p>
                        Low{" "}
                        {
                          weather.daily
                            .temperature_2m_min[index]
                        }°C
                      </p>

                      <p>
                        🌧️{" "}
                        {
                          weather.daily
                            .precipitation_probability_max[
                            index
                          ]
                        }%
                      </p>

                    </div>

                  )
                )}

              </div>

            </section>

          </>
        )}

        {!weather && !weatherLoading && (

          <section className="hero">

            <div>

              <p className="location">
                📍 Search for a city
              </p>

              <h1>🌦️</h1>

              <h2>
                Welcome to WeatherGPT
              </h2>

              <p className="feels">
                Search a city to get real weather
                information.
              </p>

            </div>

            <div className="weather-icon">
              🌤️
            </div>

          </section>

        )}

        {/* AI */}

        <section className="ai-card">

          <div>

            <h2>
              🤖 Ask WeatherGPT
            </h2>

            <p>
              Ask about rain, temperature, travel,
              outdoor activities, clothing or
              weather plans.
            </p>

            <div className="chat-box">

              <input
                type="text"
                value={message}
                onChange={(e) =>
                  setMessage(e.target.value)
                }"}</
                onKeyDown={handleChatKeyDown}
                placeholder="Ask anything about the weather..."
              />

              <button
                onClick={askWeatherGPT}
                disabled={loading}
              >
                {loading
                  ? "Thinking..."
                  : "Send ➤"}
              </button>

            </div>

          </div>

        </section>

        {reply && (

          <section className="reply-card">

            <h2>
              🤖 WeatherGPT
            </h2>
          <strong>Dileep konisetti

            <p>{reply}</p>

          </section>

        )}

      </main>

      {/* =================================================
          PREMIUM DEVELOPER FOOTER
          ================================================= */}

      <footer className="weather-footer">

        <div className="footer-main-text">
          Made with ❤️ by{" strong>
        </div>

        <div className="footer-subtitle">
          WeatherGPT • Smarter Weather. Brighter Days.
        </div>

        <div className="footer-divider">

          <span></span>

          <span className="footer-cloud">
            ☁️
          </span>

          <span></span>

        </div>

        <div className="footer-copyright">
          © 2025 WeatherGPT. All rights reserved.
        </div>

      </footer>

    </div>
  );
}

export default App;