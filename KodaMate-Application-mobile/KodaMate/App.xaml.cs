using KodaMate.Services;
using KodaMate.Views;

namespace KodaMate;

public partial class App : Application
{
    public App(IServiceProvider services)
    {
        Services = services;
        InitializeComponent();
        MainPage = CreateLoadingPage();
        _ = BootstrapAsync(services);
    }

    public static IServiceProvider Services { get; private set; } = null!;

    public static void RelaunchFromSession(IServiceProvider? services = null)
    {
        services ??= Services;
        if (Current is null) return;
        Current.MainPage = ResolveMainPage(services);
    }

    private static async Task BootstrapAsync(IServiceProvider services)
    {
        try
        {
            var session = services.GetRequiredService<ISessionService>();
            if (session.IsLoggedIn)
                await SessionBootstrap.ValidateStoredSessionAsync(services).ConfigureAwait(false);
        }
        catch
        {
            services.GetRequiredService<ISessionService>().Clear();
        }

        // Start scanning for the KODA Pi over BLE in the background. Plugin.BLE
        // will prompt for the runtime BLE/location permissions the first time;
        // we don't await this so it doesn't delay the UI boot.
        try
        {
            var ble = services.GetRequiredService<IBleConnectionService>();
            _ = ble.StartAsync();
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"[BLE] failed to start at bootstrap: {ex.Message}");
        }

        MainThread.BeginInvokeOnMainThread(() =>
        {
            if (Current is null) return;
            var page = ResolveMainPage(services);
            Current.MainPage = page;
            if (page is AppShell shell)
                shell.EnsureInitialTabLoaded();
        });
    }

    private static Page CreateLoadingPage() =>
        new ContentPage
        {
            BackgroundColor = Color.FromArgb("#121212"),
            Content = new VerticalStackLayout
            {
                VerticalOptions = LayoutOptions.Center,
                HorizontalOptions = LayoutOptions.Center,
                Spacing = 20,
                Children =
                {
                    new Image
                    {
                        Source = "koda_logo.png",
                        HeightRequest = 160,
                        WidthRequest = 160,
                        Aspect = Aspect.AspectFit,
                        HorizontalOptions = LayoutOptions.Center
                    },
                    new ActivityIndicator { IsRunning = true, Color = Color.FromArgb("#00E5FF") },
                    new Label
                    {
                        Text = "Connexion au serveur…",
                        TextColor = Color.FromArgb("#D1F7FF"),
                        HorizontalOptions = LayoutOptions.Center,
                        FontSize = 14
                    }
                }
            }
        };

    private static Page ResolveMainPage(IServiceProvider services)
    {
        var session = services.GetRequiredService<ISessionService>();
        if (!session.IsLoggedIn)
            return services.GetRequiredService<LoginPage>();
        if (!session.IsRobotConfigured)
            return services.GetRequiredService<RobotSetupPage>();
        return services.GetRequiredService<AppShell>();
    }
}
