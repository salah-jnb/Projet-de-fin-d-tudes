using System.Text.Json;
using System.Windows.Input;
using KodaMate.Helpers;
using KodaMate.Services;

namespace KodaMate.ViewModels;

/// <summary>
/// Première configuration du robot : tous les champs <c>setting</c> du backend.
/// </summary>
public sealed class RobotSetupViewModel : BaseViewModel
{
    private readonly IDistributeurService _api;
    private readonly ISessionService _session;
    private readonly IServiceProvider _services;

    private string _robotName = string.Empty;
    private string _sexe = string.Empty;
    private string _dateStr = DateTime.Now.ToString("yyyy-MM-dd");
    private string _motDePasse = string.Empty;
    private string _caractere = string.Empty;
    private string _langue = "fr-FR";
    private bool _robotPoweredOn = true;

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

    public string DateStr
    {
        get => _dateStr;
        set => SetProperty(ref _dateStr, value);
    }

    public string MotDePasse
    {
        get => _motDePasse;
        set => SetProperty(ref _motDePasse, value);
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

    public bool RobotPoweredOn
    {
        get => _robotPoweredOn;
        set => SetProperty(ref _robotPoweredOn, value);
    }

    public ICommand SaveCommand { get; }

    public RobotSetupViewModel(IDistributeurService api, ISessionService session, IServiceProvider services)
    {
        _api = api;
        _session = session;
        _services = services;
        Title = "Configuration robot";
        SaveCommand = new AsyncRelayCommand(SaveAsync);
    }

    public override async Task OnAppearingAsync()
    {
        try
        {
            IsBusy = true;
            var s = await _api.GetFullSettingsAsync();
            if (s.ValueKind == JsonValueKind.Object)
            {
                if (s.TryGetProperty("name", out var n)) RobotName = n.GetString() ?? "";
                if (s.TryGetProperty("sexe", out var sx)) Sexe = sx.GetString() ?? "";
                if (s.TryGetProperty("date", out var d)) DateStr = d.GetString() ?? DateStr;
                if (s.TryGetProperty("motdepasse", out var m)) MotDePasse = m.GetString() ?? "";
                if (s.TryGetProperty("caractere", out var c)) Caractere = c.GetString() ?? "";
                if (s.TryGetProperty("langue", out var l)) Langue = l.GetString() ?? "fr-FR";
                if (s.TryGetProperty("etat", out var e))
                {
                    RobotPoweredOn = e.ValueKind switch
                    {
                        JsonValueKind.True => true,
                        JsonValueKind.False => false,
                        JsonValueKind.Number => e.GetInt32() != 0,
                        _ => RobotPoweredOn
                    };
                }
            }
        }
        catch
        {
            /* hors ligne : champs laissés à la saisie */
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task SaveAsync()
    {
        if (string.IsNullOrWhiteSpace(RobotName))
        {
            await PageAlerts.DisplayAlertAsync("Validation", "Le nom du robot est obligatoire.");
            return;
        }

        try
        {
            IsBusy = true;
            var payload = new
            {
                name = RobotName.Trim(),
                sexe = Sexe.Trim(),
                date = DateStr.Trim(),
                motdepasse = MotDePasse,
                caractere = Caractere.Trim(),
                langue = Langue.Trim(),
                etat = RobotPoweredOn
            };

            await _api.UpdateSettingsAsync(payload);
            _session.SetRobotConfigured(true);
            App.RelaunchFromSession(_services);
        }
        catch (Exception ex)
        {
            await PageAlerts.DisplayAlertAsync("Erreur", ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }
}
