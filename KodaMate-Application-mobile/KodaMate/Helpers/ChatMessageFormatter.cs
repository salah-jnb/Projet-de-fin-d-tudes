using KodaMate.Services;

namespace KodaMate.Helpers;

/// <summary>
/// Prépare le texte envoyé à n8n (suffixe personne connectée).
/// </summary>
public static class ChatMessageFormatter
{
    /// <summary>Ajoute <c>(oussema)</c> ou <c>(partie avant @ de l'email)</c> à la fin.</summary>
    public static string AppendPersonSuffix(string text, ISessionService? session = null)
    {
        text = text.Trim();
        if (string.IsNullOrEmpty(text))
            return text;

        var tag = ResolvePersonTag(session);
        if (text.EndsWith(tag, StringComparison.OrdinalIgnoreCase))
            return text;

        return $"{text} {tag}";
    }

    public static string ResolvePersonTag(ISessionService? session)
    {
        var email = session?.Email;
        if (!string.IsNullOrWhiteSpace(email))
        {
            var local = email.Split('@')[0].Trim();
            if (!string.IsNullOrEmpty(local))
                return $"({local})";
        }

        return "(oussema)";
    }
}
