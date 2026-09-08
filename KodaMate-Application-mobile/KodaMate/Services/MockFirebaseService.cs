using KodaMate.Models;

namespace KodaMate.Services;

/// <summary>
/// Mock implementation of Firebase service for development and testing.
/// Replace with actual Firebase implementation for production.
/// </summary>
public class MockFirebaseService : IFirebaseService
{
    private RobotStatus _robotStatus = new()
    {
        IsPoweredOn = false,
        BatteryLevel = 78,
        IsConnected = true,
        SignalStrength = 85,
        Temperature = 22.5,
        Humidity = 45
    };

    private readonly List<Conversation> _conversations = new()
    {
        new Conversation
        {
            Title = "Daily Check-in",
            Snippet = "Good morning! How are you feeling today?",
            Timestamp = DateTime.Now.AddHours(-2),
            MessageCount = 5
        },
        new Conversation
        {
            Title = "Medication Reminder",
            Snippet = "Don't forget to take your vitamins at 8 AM...",
            Timestamp = DateTime.Now.AddDays(-1),
            MessageCount = 3
        },
        new Conversation
        {
            Title = "Weather Update",
            Snippet = "It's going to be sunny today with a high of 25°C...",
            Timestamp = DateTime.Now.AddDays(-2),
            MessageCount = 4
        }
    };

    private readonly List<Notification> _notifications = new()
    {
        new Notification
        {
            Title = "Medication Reminder",
            Message = "Time to take your evening vitamins",
            Type = NotificationType.Reminder,
            Timestamp = DateTime.Now.AddMinutes(-30)
        },
        new Notification
        {
            Title = "Safety Alert",
            Message = "Unusual activity detected in the living room",
            Type = NotificationType.Safety,
            Timestamp = DateTime.Now.AddHours(-1)
        }
    };

    private readonly List<AgendaItem> _agendaItems = new()
    {
        new AgendaItem
        {
            Title = "Morning Medication",
            Description = "Take vitamins and supplements",
            ScheduledTime = DateTime.Today.AddHours(8),
            Category = AgendaCategory.Medication,
            IsCompleted = true
        },
        new AgendaItem
        {
            Title = "Light Exercise",
            Description = "15 minutes of stretching",
            ScheduledTime = DateTime.Today.AddHours(10),
            Category = AgendaCategory.Exercise
        },
        new AgendaItem
        {
            Title = "Doctor Appointment",
            Description = "Annual checkup with Dr. Smith",
            ScheduledTime = DateTime.Today.AddHours(14),
            DurationMinutes = 60,
            Category = AgendaCategory.Appointment
        }
    };

    private readonly List<SmartNote> _smartNotes = new()
    {
        new SmartNote
        {
            Content = "Buy groceries: milk, eggs, bread",
            Source = "Voice command"
        },
        new SmartNote
        {
            Content = "Call daughter on Sunday",
            Source = "From conversation"
        },
        new SmartNote
        {
            Content = "Water the plants",
            IsCompleted = true,
            Source = "Koda AI suggestion"
        }
    };

    private AppSettings _settings = new();

    /// <inheritdoc />
    public event EventHandler<RobotStatus>? OnRobotStatusChanged;

    /// <inheritdoc />
    public async Task<RobotStatus> GetRobotStatusAsync()
    {
        await Task.Delay(100); // Simulate network delay
        return _robotStatus;
    }

    /// <inheritdoc />
    public async Task SetRobotPowerAsync(bool isPoweredOn)
    {
        await Task.Delay(200);
        _robotStatus.IsPoweredOn = isPoweredOn;
        _robotStatus.CurrentActivity = isPoweredOn ? RobotActivity.Idle : RobotActivity.Sleeping;
        OnRobotStatusChanged?.Invoke(this, _robotStatus);
    }

    /// <inheritdoc />
    public async Task<ChatMessage> SendMessageAsync(string message, string? imagePath = null)
    {
        await Task.Delay(500); // Simulate AI response time

        // Return a mock AI response
        return new ChatMessage
        {
            Content = $"I received your message: \"{message}\". As your smart companion, I'm here to help! Is there anything specific you'd like me to assist you with?",
            IsUserMessage = false,
            ImagePath = null
        };
    }

    /// <inheritdoc />
    public async Task<List<Conversation>> GetConversationsAsync()
    {
        await Task.Delay(100);
        return _conversations;
    }

    /// <inheritdoc />
    public async Task<List<Notification>> GetNotificationsAsync()
    {
        await Task.Delay(100);
        return _notifications;
    }

    /// <inheritdoc />
    public async Task MarkNotificationReadAsync(string notificationId)
    {
        await Task.Delay(50);
        var notification = _notifications.FirstOrDefault(n => n.Id == notificationId);
        if (notification != null)
        {
            notification.IsRead = true;
        }
    }

    /// <inheritdoc />
    public async Task<List<AgendaItem>> GetAgendaItemsAsync()
    {
        await Task.Delay(100);
        return _agendaItems;
    }

    /// <inheritdoc />
    public async Task<List<SmartNote>> GetSmartNotesAsync()
    {
        await Task.Delay(100);
        return _smartNotes;
    }

    /// <inheritdoc />
    public async Task SaveSettingsAsync(AppSettings settings)
    {
        await Task.Delay(100);
        _settings = settings;
    }

    /// <inheritdoc />
    public async Task<AppSettings> GetSettingsAsync()
    {
        await Task.Delay(100);
        return _settings;
    }
}
