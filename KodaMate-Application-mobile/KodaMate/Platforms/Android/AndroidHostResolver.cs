using Android.OS;

namespace KodaMate.Platforms.Android;

/// <summary>
/// Choisit l'hôte API : <c>10.0.2.2</c> (émulateur → PC hôte) ou IP LAN (téléphone physique).
/// </summary>
public static class AndroidHostResolver
{
    public static string ResolveAndroidApiBaseUrl(string emulatorBaseUrl, string physicalBaseUrl)
    {
        var physical = physicalBaseUrl.Trim().TrimEnd('/');
        var chosen = LooksLikeEmulator() ? emulatorBaseUrl.Trim().TrimEnd('/') : physical;
        System.Diagnostics.Debug.WriteLine($"[ApiHost] LooksLikeEmulator={LooksLikeEmulator()} → {chosen}");
        return chosen;
    }

    private static bool LooksLikeEmulator()
    {
        var fp = Build.Fingerprint ?? "";
        var model = Build.Model ?? "";
        var manufacturer = Build.Manufacturer ?? "";
        var hardware = Build.Hardware ?? "";
        if (fp.Contains("generic", StringComparison.OrdinalIgnoreCase)) return true;
        if (fp.Contains("emulator", StringComparison.OrdinalIgnoreCase)) return true;
        if (model.Contains("sdk_gphone", StringComparison.OrdinalIgnoreCase)) return true;
        if (model.Contains("Emulator", StringComparison.OrdinalIgnoreCase)) return true;
        if (model.Contains("Android SDK", StringComparison.OrdinalIgnoreCase)) return true;
        if (manufacturer.Contains("Genymotion", StringComparison.OrdinalIgnoreCase)) return true;
        if (hardware.Equals("goldfish", StringComparison.OrdinalIgnoreCase)) return true;
        if (hardware.Equals("ranchu", StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }
}
