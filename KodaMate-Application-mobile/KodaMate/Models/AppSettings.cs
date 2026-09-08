namespace KodaMate.Models;

/// <summary>
/// Application settings model for Koda Mate.
/// </summary>
public class AppSettings
{
    /// <summary>
    /// Custom name for the Koda robot.
    /// </summary>
    public string RobotName { get; set; } = "Koda";

    /// <summary>
    /// Selected voice for Koda's speech.
    /// </summary>
    public VoiceType SelectedVoice { get; set; } = VoiceType.Female;

    /// <summary>
    /// Language preference.
    /// </summary>
    public string Language { get; set; } = "English";

    /// <summary>
    /// Whether notifications are enabled.
    /// </summary>
    public bool NotificationsEnabled { get; set; } = true;

    /// <summary>
    /// Whether health monitoring is enabled.
    /// </summary>
    public bool HealthMonitoringEnabled { get; set; } = true;

    /// <summary>
    /// WiFi network name.
    /// </summary>
    public string? WifiNetwork { get; set; }

    /// <summary>
    /// Firebase project ID.
    /// </summary>
    public string? FirebaseProjectId { get; set; }

    /// <summary>
    /// App version.
    /// </summary>
    public string AppVersion { get; set; } = "1.0.0";
}

/// <summary>
/// Available voice types for Koda.
/// </summary>
public enum VoiceType
{
    Female,
    Male,
    Neutral,
    Child
}
