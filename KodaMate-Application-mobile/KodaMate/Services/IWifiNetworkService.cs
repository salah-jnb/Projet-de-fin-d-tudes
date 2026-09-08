namespace KodaMate.Services;

/// <summary>
/// Liste des SSID visibles (scan Wi‑Fi). Android : scan réel si permissions OK ;
/// autres plateformes : réseaux de démonstration + noms optionnels du système si disponibles.
/// </summary>
public interface IWifiNetworkService
{
    Task<IReadOnlyList<string>> GetAvailableSsidsAsync(CancellationToken cancellationToken = default);
}
