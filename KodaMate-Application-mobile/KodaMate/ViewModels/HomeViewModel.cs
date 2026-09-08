using System.Windows.Input;
using KodaMate.Models;
using KodaMate.Services;

namespace KodaMate.ViewModels;

/// <summary>
/// ViewModel for the Home/Remote Control page.
/// Consomme IDistributeurService (power on/off + setting state)
/// et IWeatherService (Open-Meteo) pour les données environnementales.
/// </summary>
public class HomeViewModel : BaseViewModel
{
    private readonly IDistributeurService _distributeurService;
    private readonly IWeatherService _weatherService;
    private readonly INavigationService _navigationService;
    private readonly IWifiModalService _wifiModal;
    private readonly IBleConnectionService _ble;

    private bool _isRobotPoweredOn;
    private bool _isConnected;
    private int _batteryLevel = 100;
    private double _temperature;
    private int _humidity;
    private double _windSpeed;
    private string _weatherEmoji = "🌡️";
    private string _weatherDescription = "Chargement...";
    private string _robotName = "Koda";
    private string _connectionStatus = "…";
    private string _lastSyncTime = "…";
    private bool _isPowerButtonAnimating;
    private string _cityName = AppConfig.CityName;
    private Color _wifiIndicatorColor = Color.FromArgb("#E53935");
    private bool _isBleConnected;
    private Color _bleIndicatorColor = Color.FromArgb("#E53935");
    private string _bleTooltip = "BLE déconnecté";

    public Color WifiIndicatorColor
    {
        get => _wifiIndicatorColor;
        set => SetProperty(ref _wifiIndicatorColor, value);
    }

    public bool IsBleConnected
    {
        get => _isBleConnected;
        private set => SetProperty(ref _isBleConnected, value);
    }

    public Color BleIndicatorColor
    {
        get => _bleIndicatorColor;
        private set => SetProperty(ref _bleIndicatorColor, value);
    }

    public string BleTooltip
    {
        get => _bleTooltip;
        private set => SetProperty(ref _bleTooltip, value);
    }

    public bool IsRobotPoweredOn
    {
        get => _isRobotPoweredOn;
        set => SetProperty(ref _isRobotPoweredOn, value);
    }

    public bool IsConnected
    {
        get => _isConnected;
        set => SetProperty(ref _isConnected, value, onChanged: () =>
        {
            ConnectionStatus = value ? "Connecté" : "Déconnecté";
        });
    }

    public int BatteryLevel
    {
        get => _batteryLevel;
        set => SetProperty(ref _batteryLevel, value);
    }

    public double Temperature
    {
        get => _temperature;
        set => SetProperty(ref _temperature, value);
    }

    public int Humidity
    {
        get => _humidity;
        set => SetProperty(ref _humidity, value);
    }

    public double WindSpeed
    {
        get => _windSpeed;
        set => SetProperty(ref _windSpeed, value);
    }

    public string WeatherEmoji
    {
        get => _weatherEmoji;
        set => SetProperty(ref _weatherEmoji, value);
    }

    public string WeatherDescription
    {
        get => _weatherDescription;
        set => SetProperty(ref _weatherDescription, value);
    }

    public string RobotName
    {
        get => _robotName;
        set => SetProperty(ref _robotName, value);
    }

    public string ConnectionStatus
    {
        get => _connectionStatus;
        set => SetProperty(ref _connectionStatus, value);
    }

    public string LastSyncTime
    {
        get => _lastSyncTime;
        set => SetProperty(ref _lastSyncTime, value);
    }

    public bool IsPowerButtonAnimating
    {
        get => _isPowerButtonAnimating;
        set => SetProperty(ref _isPowerButtonAnimating, value);
    }

    public string CityName
    {
        get => _cityName;
        set => SetProperty(ref _cityName, value);
    }

    public ICommand TogglePowerCommand { get; }
    public ICommand RefreshCommand { get; }
    public ICommand OpenSettingsCommand { get; }
    public ICommand OpenWifiNetworksCommand { get; }

    public HomeViewModel(
        IDistributeurService distributeurService,
        IWeatherService weatherService,
        INavigationService navigationService,
        IWifiModalService wifiModal,
        IBleConnectionService ble)
    {
        _distributeurService = distributeurService;
        _weatherService = weatherService;
        _navigationService = navigationService;
        _wifiModal = wifiModal;
        _ble = ble;

        Title = "Home";

        TogglePowerCommand = new AsyncRelayCommand(TogglePowerAsync);
        RefreshCommand = new AsyncRelayCommand(RefreshAllAsync);
        OpenSettingsCommand = new AsyncRelayCommand(OpenSettingsAsync);
        OpenWifiNetworksCommand = new AsyncRelayCommand(OpenWifiNetworksAsync);

        _ble.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName is nameof(IBleConnectionService.IsConnected)
                                or nameof(IBleConnectionService.State))
            {
                MainThread.BeginInvokeOnMainThread(SyncBleIndicator);
            }
        };
        SyncBleIndicator();
    }

    private void SyncBleIndicator()
    {
        IsBleConnected = _ble.IsConnected;
        BleIndicatorColor = _ble.IsConnected
            ? Color.FromArgb("#43A047")
            : Color.FromArgb("#E53935");
        BleTooltip = _ble.State switch
        {
            BleConnectionState.Connected => "BLE connecté au robot",
            BleConnectionState.Connecting => "BLE — connexion…",
            BleConnectionState.Scanning => "BLE — recherche du robot…",
            BleConnectionState.Failed => "BLE indisponible (retry auto)",
            _ => "BLE inactif",
        };
    }

    public override Task OnAppearingAsync()
    {
        UpdateWifiIndicator();
        SyncBleIndicator();
        _ = RefreshAllAsync();
        // Kick off BLE again in case bootstrap was interrupted.
        _ = _ble.StartAsync();
        return Task.CompletedTask;
    }

    public override Task OnDisappearingAsync() => base.OnDisappearingAsync();

    private void UpdateWifiIndicator()
    {
        WifiIndicatorColor = string.IsNullOrEmpty(Preferences.Get("km_wifi_saved_ssid", ""))
            ? Color.FromArgb("#E53935")
            : Color.FromArgb("#43A047");
    }

    private async Task OpenWifiNetworksAsync()
    {
        await _wifiModal.ShowWifiNetworksAsync(() =>
            MainThread.BeginInvokeOnMainThread(UpdateWifiIndicator));
    }

    // ──────────────────────────────────────────────────────
    //  POWER TOGGLE → backend power-on / power-off
    // ──────────────────────────────────────────────────────
    private async Task TogglePowerAsync()
    {
        if (IsBusy) return;
        try
        {
            IsBusy = true;
            IsPowerButtonAnimating = true;

            if (IsRobotPoweredOn)
                await _distributeurService.PowerOffAsync();
            else
                await _distributeurService.PowerOnAsync();

            // Re-lire l'état depuis le backend pour être sûr
            IsRobotPoweredOn = await _distributeurService.GetRobotPowerStateAsync();
            IsConnected = IsRobotPoweredOn;

            HapticFeedback.Default.Perform(HapticFeedbackType.Click);
        }
        catch (Exception ex)
        {
            await Shell.Current.DisplayAlert("Erreur", $"Impossible de modifier l'état : {ex.Message}", "OK");
        }
        finally
        {
            IsBusy = false;
            IsPowerButtonAnimating = false;
        }
    }

    // ──────────────────────────────────────────────────────
    //  REFRESH = état power + météo réelle
    // ──────────────────────────────────────────────────────
    private async Task RefreshAllAsync()
    {
        if (IsBusy) return;
        try
        {
            IsBusy = true;

            var weatherTask = _weatherService.GetCurrentWeatherAsync();
            var powerTask = RunWithTimeoutAsync(
                () => _distributeurService.GetRobotPowerStateAsync(),
                TimeSpan.FromSeconds(8));

            await Task.WhenAll(powerTask, weatherTask);

            IsRobotPoweredOn = await powerTask;
            IsConnected = IsRobotPoweredOn;

            // Appliquer météo
            var w = weatherTask.Result;
            Temperature      = w.Temperature;
            Humidity         = w.Humidity;
            WindSpeed        = w.WindSpeed;
            WeatherEmoji     = w.WeatherEmoji;
            WeatherDescription = w.WeatherDescription;
            CityName         = w.City;

            LastSyncTime = DateTime.Now.ToString("HH:mm");
        }
        catch (Exception ex) when (IsBackendUnreachable(ex))
        {
            IsConnected = false;
            LastSyncTime = "Hors ligne";
        }
        catch (Exception ex)
        {
            await Shell.Current.DisplayAlert("Erreur", ex.Message, "OK");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task OpenSettingsAsync()
    {
        await _navigationService.NavigateToAsync("//settings");
    }

    private static async Task<T> RunWithTimeoutAsync<T>(Func<Task<T>> action, TimeSpan timeout)
    {
        var work = action();
        var delay = Task.Delay(timeout);
        var finished = await Task.WhenAny(work, delay);
        if (finished != work)
            throw new TimeoutException();
        return await work;
    }

    private static bool IsBackendUnreachable(Exception ex) =>
        ex is HttpRequestException or TimeoutException or OperationCanceledException;
}
