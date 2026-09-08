using System.Text.Json;
using KodaMate.Models;

namespace KodaMate.Services;

/// <summary>
/// Interface du service backend Distributeur FastAPI.
/// </summary>
public interface IDistributeurService
{
    // ── AUTH ───────────────────────────────────────────────
    Task<AuthLoginResponse?> LoginAsync(string email, string password);

    // ── POWER ──────────────────────────────────────────────
    Task PowerOnAsync();
    Task PowerOffAsync();
    Task<bool> GetRobotPowerStateAsync();

    // ── NOTES (table note, /api/notes) ──────────────────────
    Task<List<NoteBackend>> GetAllNotesAsync();
    Task<NoteBackend?> CreateNoteAsync(string note, bool etat = false, DateTime? date = null);
    Task PatchNoteEtatAsync(int id, bool etat);
    Task DeleteNoteAsync(int id);
    Task UpdateNoteAsync(int id, string? note = null, bool? etat = null, DateTime? date = null);

    // ── CHAT / N8N / HISTORY ───────────────────────────────
    Task<string> SendToN8nAsync(string question);
    Task<List<ConversationBackend>> GetLastConversationsAsync();
    Task<List<ConversationBackend>> GetAllConversationsAsync(DateTime? dateFrom = null, DateTime? dateTo = null);

    // ── SETTINGS ───────────────────────────────────────────
    Task<JsonElement> GetFullSettingsAsync();
    Task UpdateSettingsAsync(object settingsData);
}
