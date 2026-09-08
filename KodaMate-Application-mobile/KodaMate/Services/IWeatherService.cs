using KodaMate.Models;

namespace KodaMate.Services;

/// <summary>
/// Interface du service météo (Open-Meteo, gratuit, sans clé API).
/// </summary>
public interface IWeatherService
{
    /// <summary>
    /// Récupère les données météo actuelles pour les coordonnées configurées dans AppConfig.
    /// </summary>
    Task<WeatherInfo> GetCurrentWeatherAsync();
}
