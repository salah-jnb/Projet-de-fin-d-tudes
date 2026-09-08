namespace KodaMate.Services;

/// <summary>
/// Interface for navigation service using Shell navigation.
/// </summary>
public interface INavigationService
{
    /// <summary>
    /// Navigates to a page by route.
    /// </summary>
    Task NavigateToAsync(string route);

    /// <summary>
    /// Navigates to a page with parameters.
    /// </summary>
    Task NavigateToAsync(string route, Dictionary<string, object> parameters);

    /// <summary>
    /// Navigates back.
    /// </summary>
    Task GoBackAsync();
}

/// <summary>
/// Shell-based navigation service implementation.
/// </summary>
public class NavigationService : INavigationService
{
    /// <inheritdoc />
    public async Task NavigateToAsync(string route)
    {
        await Shell.Current.GoToAsync(route);
    }

    /// <inheritdoc />
    public async Task NavigateToAsync(string route, Dictionary<string, object> parameters)
    {
        await Shell.Current.GoToAsync(route, parameters);
    }

    /// <inheritdoc />
    public async Task GoBackAsync()
    {
        await Shell.Current.GoToAsync("..");
    }
}
