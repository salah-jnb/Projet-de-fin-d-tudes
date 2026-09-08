namespace KodaMate.Models;

/// <summary>
/// Represents a chat message in the conversation with Koda AI.
/// </summary>
public class ChatMessage
{
    /// <summary>
    /// Unique identifier for the message.
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// The content/text of the message.
    /// </summary>
    public string Content { get; set; } = string.Empty;

    /// <summary>
    /// True if the message is from the user, false if from Koda.
    /// </summary>
    public bool IsUserMessage { get; set; }

    /// <summary>
    /// Timestamp when the message was sent.
    /// </summary>
    public DateTime Timestamp { get; set; } = DateTime.Now;

    /// <summary>
    /// Optional image attachment path for vision features.
    /// </summary>
    public string? ImagePath { get; set; }
}
