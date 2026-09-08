using System.Net.Http.Json;
using System.Text.Json;
using KodaMate.Models;

namespace KodaMate.Services;

/// <summary>
/// Service météo basé sur l'API Open-Meteo (100% gratuite, sans clé API).
/// Documentation : https://open-meteo.com/en/docs
/// </summary>
public class WeatherService : IWeatherService
{
    private static readonly HttpClient _http = new()
    {
        BaseAddress = new Uri("https://api.open-meteo.com/"),
        Timeout = TimeSpan.FromSeconds(10)
    };

    public async Task<WeatherInfo> GetCurrentWeatherAsync()
    {
        var lat = AppConfig.WeatherLatitude.ToString("F4", System.Globalization.CultureInfo.InvariantCulture);
        var lon = AppConfig.WeatherLongitude.ToString("F4", System.Globalization.CultureInfo.InvariantCulture);

        // current_weather inclut : temperature, windspeed, weathercode
        // hourly=relativehumidity_2m pour l'humidité de l'heure courante
        var url = $"v1/forecast?latitude={lat}&longitude={lon}" +
                  $"&current_weather=true" +
                  $"&hourly=relativehumidity_2m" +
                  $"&timezone=auto" +
                  $"&forecast_days=1";

        var doc = await _http.GetFromJsonAsync<JsonElement>(url);

        var cw = doc.GetProperty("current_weather");
        var temperature = cw.GetProperty("temperature").GetDouble();
        var windSpeed   = cw.GetProperty("windspeed").GetDouble();
        var weatherCode = cw.GetProperty("weathercode").GetInt32();
        var timeStr     = cw.GetProperty("time").GetString() ?? "";

        // Extraire l'humidité de l'heure correspondante
        int humidity = 50; // valeur par défaut
        try
        {
            var hourly = doc.GetProperty("hourly");
            var times  = hourly.GetProperty("time");
            var humArr = hourly.GetProperty("relativehumidity_2m");

            for (int i = 0; i < times.GetArrayLength(); i++)
            {
                if (times[i].GetString() == timeStr)
                {
                    humidity = humArr[i].GetInt32();
                    break;
                }
            }
        }
        catch { /* Ignore si l'humidité n'est pas disponible */ }

        return new WeatherInfo
        {
            Temperature = temperature,
            WindSpeed   = Math.Round(windSpeed, 1),
            WeatherCode = weatherCode,
            Humidity    = humidity,
            City        = AppConfig.CityName
        };
    }
}
