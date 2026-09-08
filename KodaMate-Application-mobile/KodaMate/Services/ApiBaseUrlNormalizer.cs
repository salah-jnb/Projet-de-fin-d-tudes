using System.Net;

namespace KodaMate.Services;

/// <summary>
/// Corrige les URLs du type <c>http://192.168.x.x/api</c> (port 80 implicite) en <c>http://192.168.x.x:8000/api</c>
/// pour le développement local FastAPI/uvicorn.
/// </summary>
internal static class ApiBaseUrlNormalizer
{
    internal static string Normalize(string baseUrl)
    {
        baseUrl = baseUrl.Trim().TrimEnd('/');
        if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri))
            return baseUrl;

        if (uri.Scheme != "http" || uri.Port != 80)
            return baseUrl;

        if (!IsPrivateLanIPv4(uri.Host))
            return baseUrl;

        var path = uri.AbsolutePath;
        if (string.IsNullOrEmpty(path) || path == "/")
            path = "/api";

        return $"http://{uri.Host}:8000{path}".TrimEnd('/');
    }

    private static bool IsPrivateLanIPv4(string host)
    {
        if (!IPAddress.TryParse(host, out var ip))
            return false;
        if (ip.AddressFamily != System.Net.Sockets.AddressFamily.InterNetwork)
            return false;

        var b = ip.GetAddressBytes();
        if (b[0] == 10) return true;
        if (b[0] == 127) return true;
        if (b[0] == 192 && b[1] == 168) return true;
        if (b[0] == 172 && b[1] >= 16 && b[1] <= 31) return true;
        return false;
    }
}
