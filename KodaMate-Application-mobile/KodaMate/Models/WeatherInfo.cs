namespace KodaMate.Models;

/// <summary>
/// Données météo récupérées depuis l'API Open-Meteo (gratuite, sans clé API).
/// </summary>
public class WeatherInfo
{
    public double Temperature { get; set; }
    public int Humidity { get; set; }
    public double WindSpeed { get; set; }
    public int WeatherCode { get; set; }
    public string City { get; set; } = "Ma Ville";

    /// <summary>Emoji représentant la météo selon le WMO code.</summary>
    public string WeatherEmoji => WeatherCode switch
    {
        0 => "☀️",
        1 or 2 => "🌤️",
        3 => "☁️",
        45 or 48 => "🌫️",
        51 or 53 or 55 => "🌦️",
        61 or 63 or 65 => "🌧️",
        71 or 73 or 75 => "❄️",
        80 or 81 or 82 => "⛈️",
        95 => "🌩️",
        _ => "🌡️"
    };

    public string WeatherDescription => WeatherCode switch
    {
        0 => "Ciel dégagé",
        1 or 2 => "Partiellement nuageux",
        3 => "Nuageux",
        45 or 48 => "Brouillard",
        51 or 53 or 55 => "Bruine",
        61 or 63 or 65 => "Pluie",
        71 or 73 or 75 => "Neige",
        80 or 81 or 82 => "Averses",
        95 => "Orage",
        _ => "Variable"
    };
}
