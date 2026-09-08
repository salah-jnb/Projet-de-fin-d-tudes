namespace KodaMate.Models;

/// <summary>
/// Represents the current status of the Koda robot.
/// </summary>
public class RobotStatus
{
    /// <summary>
    /// Whether the robot is powered on.
    /// </summary>
    public bool IsPoweredOn { get; set; }

    /// <summary>
    /// Current battery level (0-100).
    /// </summary>
    public int BatteryLevel { get; set; }

    /// <summary>
    /// Whether the robot is connected to WiFi.
    /// </summary>
    public bool IsConnected { get; set; }

    /// <summary>
    /// WiFi signal strength (0-100).
    /// </summary>
    public int SignalStrength { get; set; }

    /// <summary>
    /// Current room temperature in Celsius.
    /// </summary>
    public double Temperature { get; set; }

    /// <summary>
    /// Current humidity percentage.
    /// </summary>
    public int Humidity { get; set; }

    /// <summary>
    /// Robot's current activity status.
    /// </summary>
    public RobotActivity CurrentActivity { get; set; } = RobotActivity.Idle;

    /// <summary>
    /// Last sync timestamp with Firebase.
    /// </summary>
    public DateTime LastSync { get; set; } = DateTime.Now;

    /// <summary>
    /// Battery status icon based on level.
    /// </summary>
    public string BatteryIcon => BatteryLevel switch
    {
        >= 80 => "🔋",
        >= 50 => "🔋",
        >= 20 => "🪫",
        _ => "🪫"
    };

    /// <summary>
    /// Connection status text.
    /// </summary>
    public string ConnectionStatus => IsConnected ? "Connected" : "Disconnected";
}

/// <summary>
/// Robot activity states.
/// </summary>
public enum RobotActivity
{
    Idle,
    Listening,
    Speaking,
    Processing,
    Moving,
    Charging,
    Sleeping
}
