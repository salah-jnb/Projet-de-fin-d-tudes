using System.Diagnostics;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using KodaMate.Converters;
using KodaMate.Helpers;
using KodaMate.Models;

namespace KodaMate.Services;

/// <summary>
/// Implémentation réelle du service backend Distributeur.
/// </summary>
public class DistributeurApiService : IDistributeurService
{
    private HttpClient _http = null!;
    private string? _configuredBaseUrl;

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new DateOnlyStringJsonConverter() }
    };

    public DistributeurApiService() => RefreshHttpClientIfNeeded();

    private void RefreshHttpClientIfNeeded()
    {
        var baseUrl = ApiBaseUrlNormalizer.Normalize(AppConfig.BaseUrl).TrimEnd('/');
        if (!baseUrl.EndsWith("/api", StringComparison.OrdinalIgnoreCase))
            baseUrl += "/api";

        if (_configuredBaseUrl == baseUrl && _http is not null)
            return;

        _http?.Dispose();
        _configuredBaseUrl = baseUrl;
        _http = new HttpClient
        {
            BaseAddress = new Uri(baseUrl + "/"),
            Timeout = TimeSpan.FromSeconds(60)
        };
#if DEBUG
        Debug.WriteLine($"[DistributeurApi] BaseAddress={_http.BaseAddress}");
#endif
    }

    // ══════════════════════════════════════════════════════
    //  AUTH
    // ══════════════════════════════════════════════════════

    public async Task<AuthLoginResponse?> LoginAsync(string email, string password)
    {
        RefreshHttpClientIfNeeded();
        var payload = new { emailclient = email.Trim(), motdepasse = password };
        using var response = await _http.PostAsJsonAsync("auth/login", payload, _jsonOptions).ConfigureAwait(false);
        if (response.StatusCode == HttpStatusCode.Unauthorized)
            return null;
        if (response.StatusCode == HttpStatusCode.ServiceUnavailable)
            throw new HttpRequestException("Le serveur ne peut pas joindre la base de données. Réessayez.");
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<AuthLoginResponse>(_jsonOptions).ConfigureAwait(false);
    }

    public async Task PowerOnAsync()
    {
        RefreshHttpClientIfNeeded();
        var response = await _http.PostAsync("power-on", null);
        response.EnsureSuccessStatusCode();
    }

    public async Task PowerOffAsync()
    {
        RefreshHttpClientIfNeeded();
        var response = await _http.PostAsync("power-off", null);
        response.EnsureSuccessStatusCode();
    }

    public async Task<bool> GetRobotPowerStateAsync()
    {
        RefreshHttpClientIfNeeded();
        var setting = await _http.GetFromJsonAsync<JsonElement>("settings", _jsonOptions);
        if (setting.TryGetProperty("etat", out var etat))
        {
            if (etat.ValueKind == JsonValueKind.True) return true;
            if (etat.ValueKind == JsonValueKind.False) return false;
            if (etat.ValueKind == JsonValueKind.Number) return etat.GetInt32() != 0;
        }
        return false;
    }

    public async Task<List<NoteBackend>> GetAllNotesAsync()
    {
        RefreshHttpClientIfNeeded();
        var result = await _http.GetFromJsonAsync<List<NoteBackend>>("notes", _jsonOptions);
        return result ?? new List<NoteBackend>();
    }

    public async Task<NoteBackend?> CreateNoteAsync(string note, bool etat = false, DateTime? date = null)
    {
        RefreshHttpClientIfNeeded();
        var payload = new Dictionary<string, object?> { ["note"] = note, ["etat"] = etat };
        if (date.HasValue) payload["date"] = date.Value;

        var response = await _http.PostAsJsonAsync("notes", payload, _jsonOptions);
        response.EnsureSuccessStatusCode();
        var list = await response.Content.ReadFromJsonAsync<List<NoteBackend>>(_jsonOptions);
        return list?.FirstOrDefault();
    }

    public async Task PatchNoteEtatAsync(int id, bool etat)
    {
        RefreshHttpClientIfNeeded();
        var q = etat ? "true" : "false";
        var response = await _http.PatchAsync($"notes/{id}/etat?etat={q}", null);
        response.EnsureSuccessStatusCode();
    }

    public async Task DeleteNoteAsync(int id)
    {
        RefreshHttpClientIfNeeded();
        var response = await _http.DeleteAsync($"notes/{id}");
        response.EnsureSuccessStatusCode();
    }

    public async Task UpdateNoteAsync(int id, string? note = null, bool? etat = null, DateTime? date = null)
    {
        RefreshHttpClientIfNeeded();
        var payload = new Dictionary<string, object?>();
        if (note is not null) payload["note"] = note;
        if (etat.HasValue) payload["etat"] = etat.Value;
        if (date.HasValue) payload["date"] = date.Value;

        var response = await _http.PutAsJsonAsync($"notes/{id}", payload, _jsonOptions);
        response.EnsureSuccessStatusCode();
    }

    public async Task<string> SendToN8nAsync(string question)
    {
        RefreshHttpClientIfNeeded();
        var payload = new Dictionary<string, string> { ["question"] = question };
        var response = await _http.PostAsJsonAsync("trigger-n8n", payload, _jsonOptions);
        response.EnsureSuccessStatusCode();

        var raw = await response.Content.ReadAsStringAsync();
        var display = N8nResponseParser.ExtractDisplayText(raw);
        return string.IsNullOrWhiteSpace(display) ? raw : display;
    }

    public async Task<List<ConversationBackend>> GetLastConversationsAsync()
    {
        RefreshHttpClientIfNeeded();
        var result = await _http.GetFromJsonAsync<List<ConversationBackend>>("conversations/last100", _jsonOptions);
        return result ?? new List<ConversationBackend>();
    }

    public async Task<List<ConversationBackend>> GetAllConversationsAsync(DateTime? dateFrom = null, DateTime? dateTo = null)
    {
        RefreshHttpClientIfNeeded();
        var parts = new List<string>();
        if (dateFrom.HasValue)
            parts.Add($"date_from={Uri.EscapeDataString(dateFrom.Value.ToString("yyyy-MM-dd"))}");
        if (dateTo.HasValue)
            parts.Add($"date_to={Uri.EscapeDataString(dateTo.Value.ToString("yyyy-MM-dd"))}");

        var url = parts.Count > 0 ? $"conversations?{string.Join("&", parts)}" : "conversations";
        try
        {
            using var response = await _http.GetAsync(url).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
            {
#if DEBUG
                Debug.WriteLine($"[DistributeurApi] conversations HTTP {(int)response.StatusCode}");
#endif
                return await GetLastConversationsAsync().ConfigureAwait(false);
            }

            var json = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
            var result = JsonSerializer.Deserialize<List<ConversationBackend>>(json, _jsonOptions);
            return result ?? new List<ConversationBackend>();
        }
        catch (Exception ex)
        {
#if DEBUG
            Debug.WriteLine($"[DistributeurApi] GetAllConversations failed: {ex.Message}");
#endif
            return await GetLastConversationsAsync().ConfigureAwait(false);
        }
    }

    public async Task<JsonElement> GetFullSettingsAsync()
    {
        RefreshHttpClientIfNeeded();
        return await _http.GetFromJsonAsync<JsonElement>("settings", _jsonOptions);
    }

    public async Task UpdateSettingsAsync(object settingsData)
    {
        RefreshHttpClientIfNeeded();
        var response = await _http.PutAsJsonAsync("settings", settingsData, _jsonOptions);
        response.EnsureSuccessStatusCode();
    }
}
