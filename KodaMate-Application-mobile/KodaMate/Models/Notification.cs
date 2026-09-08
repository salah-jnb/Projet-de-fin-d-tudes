namespace KodaMate.Models;

/// <summary>
/// Represents a notification or alert from Koda.
/// </summary>
public class Notification
{
    /// <summary>
    /// Unique identifier for the notification.
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// Notification title.
    /// </summary>
    public string Title { get; set; } = string.Empty;

    /// <summary>
    /// Detailed message content.
    /// </summary>
    public string Message { get; set; } = string.Empty;

    /// <summary>
    /// Type of notification (Urgent, Info, Reminder, Safety).
    /// </summary>
    public NotificationType Type { get; set; } = NotificationType.Info;

    /// <summary>
    /// When the notification was created.
    /// </summary>
    public DateTime Timestamp { get; set; } = DateTime.Now;

    /// <summary>
    /// Whether the notification has been read.
    /// </summary>
    public bool IsRead { get; set; }

    /// <summary>
    /// Icon name for the notification type.
    /// </summary>
    public string Icon => Type switch
    {
        NotificationType.Urgent => "⚠️",
        NotificationType.Safety => "🛡️",
        NotificationType.Reminder => "⏰",
        _ => "ℹ️"
    };

    /// <summary>
    /// Accent color based on notification type.
    /// </summary>
    public string AccentColor => Type switch
    {
        NotificationType.Urgent => "#FF5252",
        NotificationType.Safety => "#FF9800",
        NotificationType.Reminder => "#2979FF",
        _ => "#00E5FF"
    };
}

/// <summary>
/// Types of notifications supported by Koda.
/// </summary>
public enum NotificationType
{
    Info,
    Reminder,
    Urgent,
    Safety
}
