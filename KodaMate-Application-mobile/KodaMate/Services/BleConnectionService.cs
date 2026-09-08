using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using Plugin.BLE;
using Plugin.BLE.Abstractions;
using Plugin.BLE.Abstractions.Contracts;
using Plugin.BLE.Abstractions.EventArgs;

namespace KodaMate.Services;

/// <summary>
/// Plugin.BLE-backed implementation of <see cref="IBleConnectionService"/>.
/// Scans for the KODA Pi (which advertises our custom 128-bit service UUID),
/// connects, resolves the wifi_credentials + wifi_status characteristics, and
/// stays subscribed to notifications. Auto-reconnects on drop.
/// </summary>
public sealed class BleConnectionService : IBleConnectionService, IAsyncDisposable
{
    // Must match codeRaspberry/scripts/ble_wifi_provisioner.py
    public static readonly Guid ServiceUuid =
        new("4b6f6461-0000-1000-8000-00805f9b34fb");

    public static readonly Guid CharWifiCredentialsUuid =
        new("4b6f6461-0001-1000-8000-00805f9b34fb");

    public static readonly Guid CharWifiStatusUuid =
        new("4b6f6461-0002-1000-8000-00805f9b34fb");

    private const string DevicePrefix = "KODA-";
    private const int ScanTimeoutMs = 8000;
    private const int RetryDelayMs = 4000;

    private readonly IBluetoothLE _ble;
    private readonly IAdapter _adapter;
    private readonly SemaphoreSlim _gate = new(1, 1);

    private CancellationTokenSource? _runLoopCts;
    private Task? _runLoopTask;
    private IDevice? _device;
    private ICharacteristic? _wifiCredentialsChar;
    private ICharacteristic? _wifiStatusChar;

    private BleConnectionState _state = BleConnectionState.Idle;
    private BleWifiStatus? _lastWifiStatus;

    public event PropertyChangedEventHandler? PropertyChanged;

    public BleConnectionService()
    {
        _ble = CrossBluetoothLE.Current;
        _adapter = _ble.Adapter;
        _adapter.DeviceConnectionLost += OnConnectionLost;
        _adapter.DeviceDisconnected += OnConnectionLost;
    }

    public BleConnectionState State
    {
        get => _state;
        private set
        {
            if (_state == value) return;
            _state = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(IsConnected));
            Debug.WriteLine($"[BLE] state -> {value}");
        }
    }

    public bool IsConnected => _state == BleConnectionState.Connected;

    public BleWifiStatus? LastWifiStatus
    {
        get => _lastWifiStatus;
        private set
        {
            _lastWifiStatus = value;
            OnPropertyChanged();
        }
    }

    public async Task StartAsync(CancellationToken cancellationToken = default)
    {
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (_runLoopTask is { IsCompleted: false })
                return;

            _runLoopCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            _runLoopTask = Task.Run(() => RunLoopAsync(_runLoopCts.Token));
        }
        finally
        {
            _gate.Release();
        }
    }

    public async Task StopAsync()
    {
        await _gate.WaitAsync().ConfigureAwait(false);
        CancellationTokenSource? cts;
        Task? task;
        try
        {
            cts = _runLoopCts;
            task = _runLoopTask;
            _runLoopCts = null;
            _runLoopTask = null;
        }
        finally
        {
            _gate.Release();
        }

        cts?.Cancel();
        if (task is not null)
        {
            try { await task.ConfigureAwait(false); } catch { /* swallow */ }
        }
        await DisconnectInternalAsync().ConfigureAwait(false);
        State = BleConnectionState.Idle;
    }

    public async Task SendWifiCredentialsAsync(string ssid, string password, CancellationToken cancellationToken = default)
    {
        if (_wifiCredentialsChar is null || _device is null || !IsConnected)
            throw new InvalidOperationException("BLE link with the KODA robot is not connected.");

        var payload = JsonSerializer.SerializeToUtf8Bytes(new
        {
            ssid = ssid ?? string.Empty,
            password = password ?? string.Empty,
        });

        // Optimistic local status while the Pi works on it (will be overwritten
        // by the notification).
        LastWifiStatus = new BleWifiStatus("connecting", ssid ?? string.Empty, string.Empty, null);

        await _wifiCredentialsChar.WriteAsync(payload, cancellationToken).ConfigureAwait(false);
        Debug.WriteLine($"[BLE] wrote credentials for SSID={ssid}");
    }

    // ----------------------------------------------------------------------
    // Internal helpers
    // ----------------------------------------------------------------------

    private async Task RunLoopAsync(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                if (!await EnsurePermissionsAsync(token).ConfigureAwait(false))
                {
                    State = BleConnectionState.Failed;
                    await Task.Delay(RetryDelayMs * 2, token).ConfigureAwait(false);
                    continue;
                }

                if (!_ble.IsOn)
                {
                    State = BleConnectionState.Failed;
                    await Task.Delay(RetryDelayMs, token).ConfigureAwait(false);
                    continue;
                }

                State = BleConnectionState.Scanning;
                var device = await ScanForKodaAsync(token).ConfigureAwait(false);
                if (device is null)
                {
                    await Task.Delay(RetryDelayMs, token).ConfigureAwait(false);
                    continue;
                }

                State = BleConnectionState.Connecting;
                await ConnectAndResolveAsync(device, token).ConfigureAwait(false);
                if (!IsConnected) continue;

                // Stay alive until disconnected or cancelled.
                while (!token.IsCancellationRequested && IsConnected)
                    await Task.Delay(500, token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex)
            {
                Debug.WriteLine($"[BLE] run-loop error: {ex.Message}");
                State = BleConnectionState.Failed;
                try { await Task.Delay(RetryDelayMs, token).ConfigureAwait(false); }
                catch (OperationCanceledException) { break; }
            }
        }
    }

    private static async Task<bool> EnsurePermissionsAsync(CancellationToken token)
    {
#if ANDROID
        // Plugin.BLE itself prompts on first scan on Android 12+; we also need
        // FINE_LOCATION on older devices.
        var loc = await Permissions.RequestAsync<Permissions.LocationWhenInUse>().ConfigureAwait(false);
        if (loc != PermissionStatus.Granted)
            return false;
#endif
        token.ThrowIfCancellationRequested();
        return true;
    }

    private async Task<IDevice?> ScanForKodaAsync(CancellationToken token)
    {
        IDevice? found = null;
        EventHandler<DeviceEventArgs>? handler = null;
        handler = (_, e) =>
        {
            var name = e.Device?.Name ?? string.Empty;
            if (found is not null) return;
            if (name.StartsWith(DevicePrefix, StringComparison.OrdinalIgnoreCase))
            {
                Debug.WriteLine($"[BLE] discovered {name} (id={e.Device!.Id})");
                found = e.Device;
            }
        };
        _adapter.DeviceDiscovered += handler;
        using var scanCts = CancellationTokenSource.CreateLinkedTokenSource(token);
        scanCts.CancelAfter(ScanTimeoutMs);
        try
        {
            var scanFilter = new ScanFilterOptions { ServiceUuids = new[] { ServiceUuid } };
            await _adapter.StartScanningForDevicesAsync(
                scanFilter,
                deviceFilter: null,
                allowDuplicatesKey: false,
                cancellationToken: scanCts.Token
            ).ConfigureAwait(false);
        }
        catch (OperationCanceledException) { /* expected on timeout */ }
        finally
        {
            _adapter.DeviceDiscovered -= handler;
            try { await _adapter.StopScanningForDevicesAsync().ConfigureAwait(false); } catch { /* ignore */ }
        }
        return found;
    }

    private async Task ConnectAndResolveAsync(IDevice device, CancellationToken token)
    {
        await _adapter.ConnectToDeviceAsync(device, cancellationToken: token).ConfigureAwait(false);
        var service = await device.GetServiceAsync(ServiceUuid, token).ConfigureAwait(false);
        if (service is null)
        {
            Debug.WriteLine("[BLE] device connected but KODA service UUID not found");
            await _adapter.DisconnectDeviceAsync(device).ConfigureAwait(false);
            return;
        }
        _wifiCredentialsChar = await service.GetCharacteristicAsync(CharWifiCredentialsUuid).ConfigureAwait(false);
        _wifiStatusChar = await service.GetCharacteristicAsync(CharWifiStatusUuid).ConfigureAwait(false);

        if (_wifiStatusChar is not null)
        {
            _wifiStatusChar.ValueUpdated += OnWifiStatusUpdated;
            try { await _wifiStatusChar.StartUpdatesAsync(token).ConfigureAwait(false); } catch { /* notifies optional */ }

            // Initial read so the home page can show the Pi's current state.
            try
            {
                var (bytes, _) = await _wifiStatusChar.ReadAsync(token).ConfigureAwait(false);
                ParseAndStoreStatus(bytes);
            }
            catch { /* ignore */ }
        }

        _device = device;
        State = BleConnectionState.Connected;
    }

    private void OnWifiStatusUpdated(object? sender, CharacteristicUpdatedEventArgs e)
    {
        ParseAndStoreStatus(e.Characteristic.Value);
    }

    private void ParseAndStoreStatus(byte[]? bytes)
    {
        if (bytes is null || bytes.Length == 0) return;
        try
        {
            var json = Encoding.UTF8.GetString(bytes);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            LastWifiStatus = new BleWifiStatus(
                State: root.TryGetProperty("state", out var s) ? s.GetString() ?? "" : "",
                Ssid: root.TryGetProperty("ssid", out var ssid) ? ssid.GetString() ?? "" : "",
                Ip: root.TryGetProperty("ip", out var ip) ? ip.GetString() ?? "" : "",
                Error: root.TryGetProperty("error", out var err) ? err.GetString() : null
            );
            Debug.WriteLine($"[BLE] status update: {json}");
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[BLE] failed to parse status payload: {ex.Message}");
        }
    }

    private void OnConnectionLost(object? sender, DeviceEventArgs e)
    {
        if (_device is null || e.Device?.Id != _device.Id) return;
        Debug.WriteLine("[BLE] connection to KODA lost — will retry");
        _device = null;
        _wifiCredentialsChar = null;
        if (_wifiStatusChar is not null)
        {
            _wifiStatusChar.ValueUpdated -= OnWifiStatusUpdated;
            _wifiStatusChar = null;
        }
        State = BleConnectionState.Failed;
    }

    private async Task DisconnectInternalAsync()
    {
        if (_wifiStatusChar is not null)
        {
            _wifiStatusChar.ValueUpdated -= OnWifiStatusUpdated;
            try { await _wifiStatusChar.StopUpdatesAsync().ConfigureAwait(false); } catch { /* ignore */ }
            _wifiStatusChar = null;
        }
        _wifiCredentialsChar = null;
        if (_device is not null)
        {
            try { await _adapter.DisconnectDeviceAsync(_device).ConfigureAwait(false); } catch { /* ignore */ }
            _device = null;
        }
    }

    private void OnPropertyChanged([CallerMemberName] string? name = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));

    public async ValueTask DisposeAsync()
    {
        _adapter.DeviceConnectionLost -= OnConnectionLost;
        _adapter.DeviceDisconnected -= OnConnectionLost;
        await StopAsync().ConfigureAwait(false);
        _gate.Dispose();
    }
}
