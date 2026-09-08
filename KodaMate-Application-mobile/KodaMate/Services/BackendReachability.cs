namespace KodaMate.Services;

/// <summary>
/// Test rapide de joignabilité du backend (racine HTTP, hors login).
/// </summary>
public static class BackendReachability
{
    public static async Task<bool> PingAsync(string apiBaseUrl, TimeSpan? timeout = null)
    {
        timeout ??= TimeSpan.FromSeconds(4);
        try
        {
            var root = apiBaseUrl.Trim().TrimEnd('/');
            if (root.EndsWith("/api", StringComparison.OrdinalIgnoreCase))
                root = root[..^4];

            using var cts = new CancellationTokenSource(timeout.Value);
            using var client = new HttpClient { Timeout = timeout.Value };
            var response = await client.GetAsync($"{root}/", cts.Token).ConfigureAwait(false);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }
}
