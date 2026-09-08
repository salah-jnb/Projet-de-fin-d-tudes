using System.Net.Http;
using System.Windows.Input;
using KodaMate.Helpers;
using KodaMate.Models;
using KodaMate.Services;

namespace KodaMate.ViewModels;

public sealed class LoginViewModel : BaseViewModel
{
    private readonly IDistributeurService _api;
    private readonly ISessionService _session;
    private readonly IServiceProvider _services;

    private string _email = string.Empty;
    private string _password = string.Empty;
    private string _serverUrl = AppConfig.DefaultBaseUrlForDisplay;
    private string _errorMessage = string.Empty;
    private string _statusMessage = string.Empty;

    public string Email
    {
        get => _email;
        set => SetProperty(ref _email, value);
    }

    public string Password
    {
        get => _password;
        set => SetProperty(ref _password, value);
    }

    /// <summary>URL API du PC (ex. http://192.168.1.8:8000/api).</summary>
    public string ServerUrl
    {
        get => _serverUrl;
        set => SetProperty(ref _serverUrl, value);
    }

    public string ErrorMessage
    {
        get => _errorMessage;
        set => SetProperty(ref _errorMessage, value);
    }

    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }

    public ICommand LoginCommand { get; }
    public ICommand TestServerCommand { get; }
    public ICommand ResetSessionCommand { get; }

    public LoginViewModel(IDistributeurService api, ISessionService session, IServiceProvider services)
    {
        _api = api;
        _session = session;
        _services = services;
        Title = "Connexion";
        LoginCommand = new AsyncRelayCommand(LoginAsync);
        TestServerCommand = new AsyncRelayCommand(TestServerAsync);
        ResetSessionCommand = new RelayCommand(ResetSession);
    }

    public override Task OnAppearingAsync()
    {
        var saved = Preferences.Get(AppConfig.ApiBaseUrlPreferenceKey, string.Empty);
        ServerUrl = string.IsNullOrWhiteSpace(saved) ? AppConfig.DefaultBaseUrlForDisplay : saved;
        StatusMessage = $"URL active : {AppConfig.BaseUrl}";
        return Task.CompletedTask;
    }

    private void ResetSession()
    {
        _session.Clear();
        ErrorMessage = string.Empty;
        StatusMessage = "Session effacée. Connectez-vous à nouveau.";
        App.RelaunchFromSession(_services);
    }

    private async Task TestServerAsync()
    {
        if (string.IsNullOrWhiteSpace(ServerUrl))
        {
            ErrorMessage = "Indiquez l'URL du serveur (avec :8000).";
            return;
        }

        AppConfig.SaveBaseUrl(ServerUrl.Trim());
        ErrorMessage = string.Empty;
        StatusMessage = "Test en cours…";

        try
        {
            IsBusy = true;
            var ok = await BackendReachability.PingAsync(AppConfig.BaseUrl);
            StatusMessage = ok
                ? $"Serveur OK : {AppConfig.BaseUrl}"
                : $"Serveur injoignable : {AppConfig.BaseUrl} — vérifiez uvicorn, Wi‑Fi et pare-feu.";
            if (!ok)
                ErrorMessage = StatusMessage;
        }
        finally
        {
            IsBusy = false;
        }
    }

    private async Task LoginAsync()
    {
        if (IsBusy)
            return;

        if (string.IsNullOrWhiteSpace(Email))
        {
            ErrorMessage = "Email requis.";
            return;
        }

        if (!string.IsNullOrWhiteSpace(ServerUrl))
            AppConfig.SaveBaseUrl(ServerUrl.Trim());

        ErrorMessage = string.Empty;
        try
        {
            IsBusy = true;

            if (!await BackendReachability.PingAsync(AppConfig.BaseUrl))
            {
                ErrorMessage =
                    $"Impossible de joindre le serveur ({AppConfig.BaseUrl}). "
                    + "Vérifiez que le backend tourne, le même Wi‑Fi, et l'IP du PC (ipconfig).";
                return;
            }

            var response = await _api.LoginAsync(Email.Trim(), Password);
            if (response?.Data is null)
            {
                ErrorMessage = "Email ou mot de passe incorrect.";
                return;
            }

            var d = response.Data;
            _session.SetSession(d.Emailclient ?? Email.Trim(), d.Idproduit, d.Idkoda);
            App.RelaunchFromSession(_services);
        }
        catch (OperationCanceledException)
        {
            ErrorMessage =
                $"Délai dépassé — URL : {AppConfig.BaseUrl}. Vérifiez FastAPI (port 8000) et le réseau.";
            await PageAlerts.DisplayAlertAsync("Connexion", ErrorMessage);
        }
        catch (HttpRequestException ex)
        {
            ErrorMessage = $"Réseau / HTTP : {ex.Message} — URL : {AppConfig.BaseUrl}";
            await PageAlerts.DisplayAlertAsync("Connexion", ErrorMessage);
        }
        catch (Exception ex)
        {
            ErrorMessage = ex.Message;
            await PageAlerts.DisplayAlertAsync("Erreur", ex.Message);
        }
        finally
        {
            IsBusy = false;
        }
    }
}
