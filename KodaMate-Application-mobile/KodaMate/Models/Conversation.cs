namespace KodaMate.Models;

/// <summary>
/// Represents a conversation history entry.
/// </summary>
public class Conversation
{
    /// <summary>
    /// Unique identifier for the conversation.
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// Title or summary of the conversation.
    /// </summary>
    public string Title { get; set; } = string.Empty;

    /// <summary>
    /// Preview snippet of the first message.
    /// </summary>
    public string Snippet { get; set; } = string.Empty;

    /// <summary>
    /// When the conversation started.
    /// </summary>
    public DateTime Timestamp { get; set; } = DateTime.Now;

    /// <summary>
    /// Number of messages in the conversation.
    /// </summary>
    public int MessageCount { get; set; }
}
