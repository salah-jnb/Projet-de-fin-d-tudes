using System.Text.Json.Serialization;

namespace KodaMate.Models;

/// <summary>
/// Ligne de la table <c>note</c> (GET/POST /api/notes).
/// </summary>
public class NoteBackend
{
    public int Id { get; set; }

    [JsonPropertyName("note")]
    public string Note { get; set; } = string.Empty;

    public bool Etat { get; set; }

    [JsonPropertyName("date")]
    public DateTime? Date { get; set; }

    [JsonPropertyName("idkoda")]
    public string Idkoda { get; set; } = string.Empty;
}
