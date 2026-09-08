namespace KodaMate.Services;

/// <summary>
/// URL du backend FastAPI Distributeur (<c>/api</c> inclus).
/// </summary>
public static class AppConfig
{
    public const string ApiBaseUrlPreferenceKey = "km_api_base_url";

#if ANDROID
    /// <summary>IP Wi‑Fi du PC (<c>ipconfig</c>), ex. <c>http://192.168.1.8:8000/api</c>.</summary>
    public const string AndroidPhysicalDeviceBaseUrl = "http://192.168.1.8:8000/api";

    private const string AndroidEmulatorBaseUrl = "http://10.0.2.2:8000/api";

    private static string DefaultAndroidBaseUrl =>
        global::KodaMate.Platforms.Android.AndroidHostResolver.ResolveAndroidApiBaseUrl(
            AndroidEmulatorBaseUrl,
            AndroidPhysicalDeviceBaseUrl);
#else
    private const string DefaultDesktopBaseUrl = "http://127.0.0.1:8000/api";
#endif

    /// <summary>URL effective (préférence utilisateur ou défaut plateforme).</summary>
    public static string BaseUrl
    {
        get
        {
            var custom = Preferences.Get(ApiBaseUrlPreferenceKey, string.Empty);
            if (!string.IsNullOrWhiteSpace(custom))
                return ApiBaseUrlNormalizer.Normalize(custom.Trim().TrimEnd('/'));

#if ANDROID
            return ApiBaseUrlNormalizer.Normalize(DefaultAndroidBaseUrl);
#else
            return DefaultDesktopBaseUrl;
#endif
        }
    }

    public static void SaveBaseUrl(string apiBaseUrl)
    {
        Preferences.Set(ApiBaseUrlPreferenceKey, ApiBaseUrlNormalizer.Normalize(apiBaseUrl.Trim().TrimEnd('/')));
    }

#if ANDROID
    public static string DefaultBaseUrlForDisplay => DefaultAndroidBaseUrl;
#else
    public static string DefaultBaseUrlForDisplay => DefaultDesktopBaseUrl;
#endif

    public const double WeatherLatitude = 36.7372;
    public const double WeatherLongitude = 3.0868;
    public const string CityName = "Alger";
}
