namespace KodaMate.Services;

public sealed class SessionService : ISessionService
{
    private const string KeySessionVersion = "km_session_version";
    private const int CurrentSessionVersion = 1;

    private const string KeyLoggedIn = "km_logged_in";
    private const string KeyEmail = "km_email";
    private const string KeyIdProduit = "km_idproduit";
    private const string KeyIdKoda = "km_idkoda";
    private const string KeyRobotConfigured = "km_robot_configured";

    public bool IsLoggedIn =>
        Preferences.Get(KeySessionVersion, 0) == CurrentSessionVersion
        && Preferences.Get(KeyLoggedIn, false)
        && !string.IsNullOrWhiteSpace(Email)
        && IdProduit is > 0;

    public bool IsRobotConfigured => Preferences.Get(KeyRobotConfigured, false);

    public string? Email
    {
        get
        {
            var s = Preferences.Get(KeyEmail, string.Empty);
            return string.IsNullOrEmpty(s) ? null : s;
        }
    }

    public string? IdKoda
    {
        get
        {
            var s = Preferences.Get(KeyIdKoda, string.Empty);
            return string.IsNullOrEmpty(s) ? null : s;
        }
    }

    public int? IdProduit
    {
        get
        {
            if (!Preferences.ContainsKey(KeyIdProduit)) return null;
            return Preferences.Get(KeyIdProduit, 0);
        }
    }

    public void SetSession(string email, int idProduit, string? idKoda)
    {
        Preferences.Set(KeySessionVersion, CurrentSessionVersion);
        Preferences.Set(KeyLoggedIn, true);
        Preferences.Set(KeyEmail, email);
        Preferences.Set(KeyIdProduit, idProduit);
        if (!string.IsNullOrEmpty(idKoda))
            Preferences.Set(KeyIdKoda, idKoda);
    }

    public void SetRobotConfigured(bool configured = true) =>
        Preferences.Set(KeyRobotConfigured, configured);

    public void Clear()
    {
        Preferences.Remove(KeySessionVersion);
        Preferences.Remove(KeyLoggedIn);
        Preferences.Remove(KeyEmail);
        Preferences.Remove(KeyIdProduit);
        Preferences.Remove(KeyIdKoda);
        Preferences.Remove(KeyRobotConfigured);
        Preferences.Remove("km_wifi_saved_ssid");
    }
}
