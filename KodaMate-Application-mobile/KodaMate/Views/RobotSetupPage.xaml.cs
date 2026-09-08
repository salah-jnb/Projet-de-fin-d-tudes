using KodaMate.ViewModels;

namespace KodaMate.Views;

public partial class RobotSetupPage : ContentPage
{
    public RobotSetupPage(RobotSetupViewModel viewModel)
    {
        InitializeComponent();
        BindingContext = viewModel;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        if (BindingContext is RobotSetupViewModel vm)
            await vm.OnAppearingAsync();
    }
}
