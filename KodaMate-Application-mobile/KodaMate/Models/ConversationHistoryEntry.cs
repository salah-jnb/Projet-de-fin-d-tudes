namespace KodaMate.Models;

/// <summary>
/// Ligne affichée dans l'historique (séparateur de date ou fil question/réponse).
/// </summary>
public class ConversationHistoryEntry
{
    public bool IsDateHeader { get; init; }

    public string DisplayDate { get; init; } = string.Empty;

    public int Idconv { get; init; }

    public string Question { get; init; } = string.Empty;

    public string Reponce { get; init; } = string.Empty;

    /// <summary>Date du message (ex. « 19 mai 2026 »).</summary>
    public string MessageDateLabel { get; init; } = string.Empty;
}
