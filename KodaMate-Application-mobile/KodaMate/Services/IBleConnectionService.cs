using System.ComponentModel;

namespace KodaMate.Services;

/// <summary>
/// State machine for the BLE link to the KODA Pi.
/// </summary>
public enum BleConnectionState
{
    Idle,         // never started or stopped
    Scanning,     // looking for the Pi advertisement
    Connecting,   // found it, GATT handshake in progress
    Connected,    // characteristics resolved, ready to push commands
    Failed,       // last attempt errored; will auto-retry
}

/// <summary>
/// Status pushed back by the Pi after a Wi-Fi credentials write.
/// Mirrors the JSON shape produced by codeRaspberry/scripts/ble_wifi_provisioner.py:
///   {"state": "connecting|connected|failed", "ssid": "...", "ip": "...", "error": "..."}
/// </summary>
public sealed record BleWifiStatus(string State, string Ssid, string Ip, string? Error);

/// <summary>
/// Singleton that owns the BLE link to the Pi: scans, connects, retries,
/// exposes connection state for the home header indicator, and lets callers
/// send Wi-Fi credentials over the GATT write characteristic.
/// </summary>
public interface IBleConnectionService : INotifyPropertyChanged
{
    /// <summary>Current high-level state of the link.</summary>
    BleConnectionState State { get; }

    /// <summary>True iff <see cref="State"/> == Connected.</summary>
    bool IsConnected { get; }

    /// <summary>Last status payload received from the Pi (or null).</summary>
    BleWifiStatus? LastWifiStatus { get; }

    /// <summary>
    /// Begin background scan + auto-connect. Idempotent — safe to call multiple times.
    /// </summary>
    Task StartAsync(CancellationToken cancellationToken = default);

    /// <summary>Stop background scan + drop any active connection.</summary>
    Task StopAsync();

    /// <summary>
    /// Push Wi-Fi credentials to the Pi. Throws if not currently connected.
    /// The actual connection result comes back asynchronously via
    /// <see cref="LastWifiStatus"/> (the property fires PropertyChanged).
    /// </summary>
    Task SendWifiCredentialsAsync(string ssid, string password, CancellationToken cancellationToken = default);
}
