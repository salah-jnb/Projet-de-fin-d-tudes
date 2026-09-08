using System.Linq;
using KodaMate.Views;

namespace KodaMate.Services;

public sealed class WifiModalService : IWifiModalService
{
    private readonly IServiceProvider _services;

    public WifiModalService(IServiceProvider services) => _services = services;

    public async Task ShowWifiNetworksAsync(Action? afterClose = null)
    {
        var page = _services.GetRequiredService<WifiNetworksPage>();
        if (page.Parent is not null)
            return;

        void OnDisappearing(object? sender, EventArgs e)
        {
            page.Disappearing -= OnDisappearing;
            afterClose?.Invoke();
        }

        page.Disappearing += OnDisappearing;

        async Task Push()
        {
            if (Shell.Current is not null)
                await Shell.Current.Navigation.PushModalAsync(page);
            else
            {
                var root = Application.Current?.Windows.FirstOrDefault()?.Page;
                if (root?.Navigation is not null)
                    await root.Navigation.PushModalAsync(page);
            }
        }

        if (MainThread.IsMainThread)
            await Push();
        else
            await MainThread.InvokeOnMainThreadAsync(Push);
    }
}
