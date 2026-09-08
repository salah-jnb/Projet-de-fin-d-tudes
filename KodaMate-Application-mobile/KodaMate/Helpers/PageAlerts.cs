namespace KodaMate.Helpers;

public static class PageAlerts
{
    public static Task DisplayAlertAsync(string title, string message, string cancel = "OK")
    {
        if (Shell.Current is not null)
            return Shell.Current.DisplayAlert(title, message, cancel);
        var p = Application.Current?.MainPage;
        return p is null ? Task.CompletedTask : p.DisplayAlert(title, message, cancel);
    }

    public static Task<string?> DisplayPromptAsync(
        string title,
        string message,
        string accept = "OK",
        string cancel = "Annuler",
        string? placeholder = null,
        int maxLength = -1,
        Keyboard? keyboard = null,
        string initialValue = "")
    {
        if (Shell.Current is not null)
            return Shell.Current.DisplayPromptAsync(title, message, accept, cancel, placeholder, maxLength, keyboard, initialValue);
        var p = Application.Current?.MainPage;
        return p is null ? Task.FromResult<string?>(null) : p.DisplayPromptAsync(title, message, accept, cancel, placeholder, maxLength, keyboard, initialValue);
    }
}
