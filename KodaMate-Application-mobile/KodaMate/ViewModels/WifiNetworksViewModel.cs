using System.Collections.ObjectModel;
using System.Windows.Input;
using KodaMate.Helpers;
using KodaMate.Services;

namespace KodaMate.ViewModels;

public sealed class WifiNetworksViewModel : BaseViewModel
{
    private readonly IWifiNetworkService _wifi;
    private readonly IBleConnectionService _ble;

    public ObservableCollection<string> Networks { get; } = new();

    public ICommand RefreshCommand { get; }
    public ICommand PickNetworkCommand { get; }
    public ICommand CloseCommand { get; }

    public WifiNetworksViewModel(IWifiNetworkService wifi, IBleConnectionService ble)
    {
        _wifi = wifi;
        _ble = ble;
        Title = "Wi‑Fi";
        RefreshCommand = new AsyncRelayCommand(LoadAsync);
        PickNetworkCommand = new AsyncRelayCommand<string>(PickAsync);
        CloseCommand = new AsyncRelayCommand(CloseAsync);
    }

    public override async Task OnAppearingAsync() => await LoadAsync();

    private async Task LoadAsync()
    {
        if (IsBusy) return;
        try
        {
            IsBusy = true;
            var list = await _wifi.GetAvailableSsidsAsync();
            Networks.Clear();
            foreach (var s in list.Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(x => x))
                Networks.Add(s);
        }
        catch (Exception ex)
        {
            await PageAlerts.DisplayAlertAsync("Wi‑Fi", ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task PickAsync(string? ssid)
    {
        if (string.IsNullOrWhiteSpace(ssid)) return;

        if (!_ble.IsConnected)
        {
            await PageAlerts.DisplayAlertAsync(
                "Wi‑Fi",
                "Le robot n'est pas joignable en Bluetooth. Approche-toi du robot et patiente — l'icône 🛰️ doit devenir verte avant d'envoyer le mot de passe.");
            return;
        }

        var pwd = await PageAlerts.DisplayPromptAsync(
            "Connexion Wi‑Fi",
            $"Mot de passe pour « {ssid} » — envoyé au robot via Bluetooth.",
            placeholder: "Mot de passe",
            accept: "Valider",
            cancel: "Annuler");

        if (pwd is null)
            return;

        try
        {
            IsBusy = true;
            await _ble.SendWifiCredentialsAsync(ssid, pwd);
            Preferences.Set("km_wifi_saved_ssid", ssid);

            // Wait briefly for the Pi to report a final state (connecting → connected/failed).
            var deadline = DateTime.UtcNow.AddSeconds(20);
            BleWifiStatus? final = null;
            while (DateTime.UtcNow < deadline)
            {
                var status = _ble.LastWifiStatus;
                if (status is not null && status.State is "connected" or "failed")
                {
                    final = status;
                    break;
                }
                await Task.Delay(500);
            }

            if (final?.State == "connected")
            {
                await PageAlerts.DisplayAlertAsync(
                    "Wi‑Fi",
                    $"Le robot est maintenant sur « {final.Ssid} ». IP : {final.Ip}");
            }
            else if (final?.State == "failed")
            {
                await PageAlerts.DisplayAlertAsync(
                    "Wi‑Fi — échec",
                    $"Le robot n'a pas pu se connecter à « {ssid} ».\n{final.Error}");
            }
            else
            {
                await PageAlerts.DisplayAlertAsync(
                    "Wi‑Fi",
                    $"Demande envoyée pour « {ssid} ». Vérifie l'état dans Réglages — la connexion peut prendre encore quelques secondes.");
            }
        }
        catch (Exception ex)
        {
            await PageAlerts.DisplayAlertAsync("Wi‑Fi — erreur", ex.Message);
        }
        finally
        {
            IsBusy = false;
        }

        await CloseAsync();
    }

    private async Task CloseAsync()
    {
        if (Shell.Current is null) return;
        await MainThread.InvokeOnMainThreadAsync(async () =>
        {
            await Shell.Current.Navigation.PopModalAsync();
        });
    }
}
