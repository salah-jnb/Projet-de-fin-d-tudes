#if ANDROID
using Android.Content;
using Android.Net.Wifi;
#endif

namespace KodaMate.Services;

/// <inheritdoc />
public sealed class WifiNetworkService : IWifiNetworkService
{
    private static readonly string[] DemoNetworks =
    {
        "KodaNet-5G", "Orange_Fiber", "Bbox-2G4E", "FreeWifi", "Guest-Robot"
    };

    public async Task<IReadOnlyList<string>> GetAvailableSsidsAsync(CancellationToken cancellationToken = default)
    {
#if ANDROID
        try
        {
            var perm = await Permissions.RequestAsync<Permissions.LocationWhenInUse>().ConfigureAwait(false);
            if (perm != PermissionStatus.Granted)
                return DemoNetworks.ToList();

            var ctx = Platform.CurrentActivity ?? Android.App.Application.Context;
            var wifi = ctx.GetSystemService(Context.WifiService) as WifiManager;
            if (wifi is null || !wifi.IsWifiEnabled)
                return DemoNetworks.ToList();

#pragma warning disable CA1422
            wifi.StartScan();
#pragma warning restore CA1422
            await Task.Delay(2200, cancellationToken).ConfigureAwait(false);

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var list = new List<string>();
#pragma warning disable CA1422
            foreach (var r in wifi.ScanResults ?? new List<ScanResult>())
#pragma warning restore CA1422
            {
                var ssid = (r.Ssid ?? string.Empty).Trim().Trim('"');
                if (string.IsNullOrEmpty(ssid) || ssid == "<unknown ssid>" || !seen.Add(ssid))
                    continue;
                list.Add(ssid);
            }

            if (list.Count == 0)
                return DemoNetworks.ToList();

            list.Sort(StringComparer.OrdinalIgnoreCase);
            return list;
        }
        catch
        {
            return DemoNetworks.ToList();
        }
#else
        await Task.Delay(400, cancellationToken).ConfigureAwait(false);
        return DemoNetworks.ToList();
#endif
    }
}
