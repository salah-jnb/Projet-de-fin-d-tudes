namespace KodaMate.Services;

/// <summary>Session locale (Preferences) après login API.</summary>
public interface ISessionService
{
    bool IsLoggedIn { get; }
    bool IsRobotConfigured { get; }
    string? Email { get; }
    string? IdKoda { get; }
    int? IdProduit { get; }

    void SetSession(string email, int idProduit, string? idKoda);
    void SetRobotConfigured(bool configured = true);
    void Clear();
}
