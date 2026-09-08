using KodaMate.ViewModels;
using KodaMate.Views;

namespace KodaMate;

/// <summary>
/// Application shell - manages navigation structure and routes.
/// </summary>
public partial class AppShell : Shell
{
    public AppShell()
    {
        InitializeComponent();
        RegisterRoutes();
        Navigated += OnShellNavigated;
    }

    /// <summary>
    /// Après assignation comme MainPage, force le chargement de l'onglet Home (OnAppearing + API).
    /// </summary>
    public void EnsureInitialTabLoaded()
    {
        Dispatcher.Dispatch(async () =>
        {
            await Task.Delay(80);
            if (CurrentPage?.BindingContext is BaseViewModel vm)
                await vm.OnAppearingAsync();
            else
                await GoToAsync("//home");
        });
    }

    private void OnShellNavigated(object? sender, ShellNavigatedEventArgs e)
    {
        if (e.Source != ShellNavigationSource.ShellItemChanged
            && e.Source != ShellNavigationSource.ShellSectionChanged
            && e.Source != ShellNavigationSource.ShellContentChanged)
            return;

        if (CurrentPage?.BindingContext is BaseViewModel vm)
            _ = vm.OnAppearingAsync();
    }

    /// <summary>
    /// Registers navigation routes for Shell navigation.
    /// </summary>
    private static void RegisterRoutes()
    {
        // Register additional routes for navigation
        Routing.RegisterRoute("history", typeof(HistoryPage));
        Routing.RegisterRoute("notifications", typeof(NotificationsPage));
        
        // Deep navigation routes (for navigating from one tab to another with parameters)
        Routing.RegisterRoute("home/notifications", typeof(NotificationsPage));
        Routing.RegisterRoute("chat/history", typeof(HistoryPage));
    }
}
