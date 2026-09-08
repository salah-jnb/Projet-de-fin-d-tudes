using Microsoft.Extensions.Logging;
using KodaMate.Services;
using KodaMate.ViewModels;
using KodaMate.Views;

namespace KodaMate;

/// <summary>
/// Point d'entrée MAUI : DI, polices, services.
/// </summary>
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();

        builder
            .UseMauiApp<App>()
            .ConfigureFonts(fonts =>
            {
                fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
                fonts.AddFont("OpenSans-Semibold.ttf", "OpenSansSemibold");
            });

        builder.Services.AddSingleton<ISessionService, SessionService>();
        builder.Services.AddSingleton<IWifiNetworkService, WifiNetworkService>();
        builder.Services.AddSingleton<IWifiModalService, WifiModalService>();
        builder.Services.AddSingleton<IBleConnectionService, BleConnectionService>();

        builder.Services.AddSingleton<IDistributeurService, DistributeurApiService>();
        builder.Services.AddSingleton<IWeatherService, WeatherService>();
        builder.Services.AddSingleton<IFirebaseService, MockFirebaseService>();
        builder.Services.AddSingleton<INavigationService, NavigationService>();

        builder.Services.AddTransient<AppShell>();

        builder.Services.AddTransient<LoginViewModel>();
        builder.Services.AddTransient<LoginPage>();
        builder.Services.AddTransient<RobotSetupViewModel>();
        builder.Services.AddTransient<RobotSetupPage>();
        builder.Services.AddTransient<WifiNetworksViewModel>();
        builder.Services.AddTransient<WifiNetworksPage>();

        builder.Services.AddTransient<HomeViewModel>();
        builder.Services.AddTransient<ChatViewModel>();
        builder.Services.AddTransient<HistoryViewModel>();
        builder.Services.AddTransient<NotificationsViewModel>();
        builder.Services.AddTransient<SettingsViewModel>();

        builder.Services.AddTransient<HomePage>();
        builder.Services.AddTransient<ChatPage>();
        builder.Services.AddTransient<HistoryPage>();
        builder.Services.AddTransient<NotificationsPage>();
        builder.Services.AddTransient<SettingsPage>();

#if DEBUG
        builder.Logging.AddDebug();
#endif

        return builder.Build();
    }
}
