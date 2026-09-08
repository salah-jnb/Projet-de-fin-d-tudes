using KodaMate.ViewModels;

namespace KodaMate.Views;

/// <summary>
/// Chat page - AI conversation interface with Koda.
/// </summary>
public partial class ChatPage : ContentPage
{
    private readonly ChatViewModel _viewModel;

    public ChatPage(ChatViewModel viewModel)
    {
        InitializeComponent();
        BindingContext = _viewModel = viewModel;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        await _viewModel.OnAppearingAsync();
    }

    protected override async void OnDisappearing()
    {
        base.OnDisappearing();
        await _viewModel.OnDisappearingAsync();
    }
}
