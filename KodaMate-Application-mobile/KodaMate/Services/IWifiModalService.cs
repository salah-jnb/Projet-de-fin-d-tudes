namespace KodaMate.Services;

public interface IWifiModalService
{
    /// <param name="afterClose">Invoqué quand la page Wi‑Fi est fermée (mise à jour indicateur).</param>
    Task ShowWifiNetworksAsync(Action? afterClose = null);
}
