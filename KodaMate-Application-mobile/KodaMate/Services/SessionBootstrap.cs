namespace KodaMate.Services;

/// <summary>
/// Vérifie qu'une session en cache est complète et que le backend répond sur /api.
/// </summary>
public static class SessionBootstrap
{
    public static async Task<bool> ValidateStoredSessionAsync(IServiceProvider services)
    {
        var session = services.GetRequiredService<ISessionService>();
        if (!session.IsLoggedIn)
            return false;

        if (!await BackendReachability.PingAsync(AppConfig.BaseUrl).ConfigureAwait(false))
        {
            session.Clear();
            return false;
        }

        try
        {
            var api = services.GetRequiredService<IDistributeurService>();
            await api.GetFullSettingsAsync().ConfigureAwait(false);
            return true;
        }
        catch
        {
            session.Clear();
            return false;
        }
    }
}
