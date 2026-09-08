using System.Text.Json.Serialization;
using KodaMate.Converters;

namespace KodaMate.Models;

/// <summary>
/// Ligne de la table <c>conversation</c> (GET /api/conversations).
/// Supabase peut renvoyer <c>id</c> ou <c>idconv</c>, et <c>iduser</c> en UUID (string).
/// </summary>
public class ConversationBackend
{
    [JsonPropertyName("idconv")]
    public int Idconv { get; set; }

    [JsonPropertyName("id")]
    public int Id
    {
        get => Idconv;
        set => Idconv = value;
    }

    public string Question { get; set; } = string.Empty;

    [JsonPropertyName("reponce")]
    public string Reponce { get; set; } = string.Empty;

    [JsonPropertyName("date")]
    [JsonConverter(typeof(DateOnlyStringJsonConverter))]
    public DateTime Date { get; set; }

    [JsonPropertyName("typedequestion")]
    public string TypeDeQuestion { get; set; } = string.Empty;

    /// <summary>UUID ou entier selon la base — toujours stocké en string.</summary>
    [JsonPropertyName("iduser")]
    public string? Iduser { get; set; }

    [JsonPropertyName("idkoda")]
    public string? Idkoda { get; set; }
}
