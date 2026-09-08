using KodaMate.ViewModels;

namespace KodaMate.Views;

public partial class WifiNetworksPage : ContentPage
{
    public WifiNetworksPage(WifiNetworksViewModel viewModel)
    {
        InitializeComponent();
        BindingContext = viewModel;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        if (BindingContext is WifiNetworksViewModel vm)
            await vm.OnAppearingAsync();
    }
}
