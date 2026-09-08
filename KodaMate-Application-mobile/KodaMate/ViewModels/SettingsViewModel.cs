using System.Text.Json;
using System.Windows.Input;
using KodaMate.Helpers;
using KodaMate.Services;

namespace KodaMate.ViewModels;

/// <summary>
/// Paramètres onglet : charge/enregistre via GET/PUT <c>/api/settings</c>.
/// </summary>
public class SettingsViewModel : BaseViewModel
{
    private readonly IDistributeurService _distributeurService;
    private readonly IWifiModalService _wifiModal;
    private readonly ISessionService _session;
    private readonly IServiceProvider _services;

    private string _robotName = "Koda";
    private string _sexe = string.Empty;
    private string _caractere = string.Empty;
    private string _langue = "fr-FR";
    private string _motDePasseSetting = string.Empty;
    private string _dateSetting = DateTime.Now.ToString("yyyy-MM-dd");
    private bool _robotEtat = true;
    private string _selectedVoice = "Female";
    private bool _notificationsEnabled = true;
    private bool _healthMonitoringEnabled = true;
    private string _wifiNetwork = "Appuyez sur « Wi‑Fi » dans l’en-tête ou Configure";
    private string _appVersion = "1.0.0-PRO";
    private Color _wifiIndicatorColor = Color.FromArgb("#E53935");

    public Color WifiIndicatorColor
    {
        get => _wifiIndicatorColor;
        set => SetProperty(ref _wifiIndicatorColor, value);
    }

    public ICommand OpenWifiNetworksCommand { get; }

    public List<string> VoiceOptions { get; } = new() { "Female", "Male", "Neutral", "Child" };

    public string RobotName
    {
        get => _robotName;
        set => SetProperty(ref _robotName, value);
    }

    public string Sexe
    {
        get => _sexe;
        set => SetProperty(ref _sexe, value);
    }

    public string Caractere
    {
        get => _caractere;
        set => SetProperty(ref _caractere, value);
    }

    public string Langue
    {
        get => _langue;
        set => SetProperty(ref _langue, value);
    }

    public string MotDePasseSetting
    {
        get => _motDePasseSetting;
        set => SetProperty(ref _motDePasseSetting, value);
    }

    public string DateSetting
    {
        get => _dateSetting;
        set => SetProperty(ref _dateSetting, value);
    }

    public bool RobotEtat
    {
        get => _robotEtat;
        set => SetProperty(ref _robotEtat, value);
    }

    public string SelectedVoice
    {
        get => _selectedVoice;
        set => SetProperty(ref _selectedVoice, value);
    }

    public bool NotificationsEnabled
    {
        get => _notificationsEnabled;
        set => SetProperty(ref _notificationsEnabled, value);
    }

    public bool HealthMonitoringEnabled
    {
        get => _healthMonitoringEnabled;
        set => SetProperty(ref _healthMonitoringEnabled, value);
    }

    public string WifiNetwork
    {
        get => _wifiNetwork;
        set => SetProperty(ref _wifiNetwork, value);
    }

    public string AppVersion
    {
        get => _appVersion;
        set => SetProperty(ref _appVersion, value);
    }

    public ICommand SaveSettingsCommand { get; }
    public ICommand ConfigureWifiCommand { get; }
    public ICommand ShowAboutCommand { get; }
    public ICommand ResetSettingsCommand { get; }
    public ICommand LogoutCommand { get; }

    public SettingsViewModel(
        IDistributeurService distributeurService,
        IWifiModalService wifiModal,
        ISessionService session,
        IServiceProvider services)
    {
        _distributeurService = distributeurService;
        _wifiModal = wifiModal;
        _session = session;
        _services = services;
        Title = "Paramètres";

        SaveSettingsCommand = new AsyncRelayCommand(SaveSettingsAsync);
        ConfigureWifiCommand = new AsyncRelayCommand(OpenWifiFromCardAsync);
        OpenWifiNetworksCommand = new AsyncRelayCommand(OpenWifiNetworksAsync);
        ShowAboutCommand = new AsyncRelayCommand(ShowAboutAsync);
        ResetSettingsCommand = new AsyncRelayCommand(ResetSettingsAsync);
        LogoutCommand = new AsyncRelayCommand(LogoutAsync);
    }

    public override async Task OnAppearingAsync()
    {
        UpdateWifiAndLabel();
        await LoadSettingsAsync();
    }

    public override Task OnDisappearingAsync() => base.OnDisappearingAsync();

    private void UpdateWifiAndLabel()
    {
        var ssid = Preferences.Get("km_wifi_saved_ssid", "");
        WifiIndicatorColor = string.IsNullOrEmpty(ssid)
            ? Color.FromArgb("#E53935")
            : Color.FromArgb("#43A047");
        WifiNetwork = string.IsNullOrEmpty(ssid) ? "Aucun réseau enregistré (simulation)" : $"Enregistré : {ssid}";
    }

    private async Task OpenWifiNetworksAsync()
    {
        await _wifiModal.ShowWifiNetworksAsync(() =>
            MainThread.BeginInvokeOnMainThread(UpdateWifiAndLabel));
    }

    private async Task OpenWifiFromCardAsync() => await OpenWifiNetworksAsync();

    private async Task LogoutAsync()
    {
        var ok = await Shell.Current.DisplayAlert("Déconnexion", "Quitter la session ?", "Oui", "Non");
        if (!ok) return;
        _session.Clear();
        App.RelaunchFromSession(_services);
    }

    private async Task LoadSettingsAsync()
    {
        try
        {
            IsBusy = true;
            var settings = await _distributeurService.GetFullSettingsAsync();

            if (settings.ValueKind == JsonValueKind.Object)
            {
                if (settings.TryGetProperty("name", out var name))
                    RobotName = name.GetString() ?? "Koda";
                if (settings.TryGetProperty("sexe", out var sx))
                    Sexe = sx.GetString() ?? "";
                if (settings.TryGetProperty("caractere", out var c))
                    Caractere = c.GetString() ?? "";
                if (settings.TryGetProperty("langue", out var l))
                    Langue = l.GetString() ?? "fr-FR";
                if (settings.TryGetProperty("motdepasse", out var m))
                    MotDePasseSetting = m.GetString() ?? "";
                if (settings.TryGetProperty("date", out var d))
                    DateSetting = d.GetString() ?? DateSetting;
                if (settings.TryGetProperty("etat", out var e))
                {
                    RobotEtat = e.ValueKind switch
                    {
                        JsonValueKind.True => true,
                        JsonValueKind.False => false,
                        JsonValueKind.Number => e.GetInt32() != 0,
                        _ => RobotEtat
                    };
                }
            }
        }
        catch (Exception ex)
        {
            await PageAlerts.DisplayAlertAsync("Erreur", $"Impossible de charger les paramètres : {ex.Message}");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task SaveSettingsAsync()
    {
        try
        {
            IsBusy = true;

            var payload = new
            {
                name = RobotName.Trim(),
                sexe = Sexe.Trim(),
                date = DateSetting.Trim(),
                motdepasse = MotDePasseSetting,
                caractere = Caractere.Trim(),
                langue = Langue.Trim(),
                etat = RobotEtat
            };

            await _distributeurService.UpdateSettingsAsync(payload);
            await PageAlerts.DisplayAlertAsync("Succès", "Paramètres enregistrés sur le backend.");
        }
        catch (Exception ex)
        {
            await PageAlerts.DisplayAlertAsync("Erreur", $"Échec de l'enregistrement : {ex.Message}");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task ShowAboutAsync()
    {
        await PageAlerts.DisplayAlertAsync(
            "À propos de Koda Mate",
            $"Version : {AppVersion}\n\n" +
            "Koda Mate — application compagnon pour le robot Koda.\n" +
            "Backend Distributeur FastAPI + n8n.\n\n" +
            "© 2026 Koda Robotics.");
    }

    private async Task ResetSettingsAsync()
    {
        var confirm = await Shell.Current.DisplayAlert(
            "Réinitialiser",
            "Remettre le nom du robot à « Koda » ?",
            "Oui", "Non");

        if (confirm)
        {
            RobotName = "Koda";
            await SaveSettingsAsync();
        }
    }
}
