using System.Text.Json;

namespace KodaMate.Helpers;

/// <summary>
/// Extrait le texte affichable depuis la réponse brute n8n / backend.
/// </summary>
public static class N8nResponseParser
{
    private static readonly string[] TextFields =
    [
        "output", "response", "answer", "text", "message", "reply", "reponce"
    ];

    public static string ExtractDisplayText(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
            return string.Empty;

        raw = raw.Trim();

        try
        {
            using var doc = JsonDocument.Parse(raw);
            var root = doc.RootElement;

            if (root.ValueKind == JsonValueKind.Array && root.GetArrayLength() > 0)
                return CleanMessage(ExtractFromElement(root[0]));

            if (root.ValueKind == JsonValueKind.Object)
                return CleanMessage(ExtractFromElement(root));
        }
        catch (JsonException)
        {
            /* corps texte ou erreur HTTP */
        }

        return CleanMessage(raw);
    }

    private static string ExtractFromElement(JsonElement element)
    {
        if (element.ValueKind != JsonValueKind.Object)
            return element.ToString();

        foreach (var field in TextFields)
        {
            if (!element.TryGetProperty(field, out var val))
                continue;

            if (val.ValueKind == JsonValueKind.String)
                return val.GetString() ?? string.Empty;

            if (val.ValueKind == JsonValueKind.Array && val.GetArrayLength() > 0)
                return ExtractFromElement(val[0]);
        }

        return string.Empty;
    }

    private static string CleanMessage(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return string.Empty;

        text = text.Trim();

        // Artefact n8n : "... ? (content)"
        if (text.EndsWith("(content)", StringComparison.OrdinalIgnoreCase))
            text = text[..^"(content)".Length].TrimEnd();

        return text;
    }
}
