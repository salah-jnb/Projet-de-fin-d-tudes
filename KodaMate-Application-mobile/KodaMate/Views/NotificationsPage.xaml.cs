using KodaMate.ViewModels;

namespace KodaMate.Views;

/// <summary>
/// Notifications page - View alerts and notifications from Koda.
/// </summary>
public partial class NotificationsPage : ContentPage
{
    private readonly NotificationsViewModel _viewModel;

    public NotificationsPage(NotificationsViewModel viewModel)
    {
        InitializeComponent();
        BindingContext = _viewModel = viewModel;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        await _viewModel.OnAppearingAsync();
    }
}
