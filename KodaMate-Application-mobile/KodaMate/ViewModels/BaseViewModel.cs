using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;

namespace KodaMate.ViewModels;

/// <summary>
/// Base ViewModel class implementing INotifyPropertyChanged.
/// Provides common functionality for all ViewModels.
/// </summary>
public abstract class BaseViewModel : INotifyPropertyChanged
{
    private bool _isBusy;
    private string _title = string.Empty;

    /// <summary>
    /// Indicates whether the ViewModel is performing a background operation.
    /// </summary>
    public bool IsBusy
    {
        get => _isBusy;
        set => SetProperty(ref _isBusy, value);
    }

    /// <summary>
    /// Page or section title.
    /// </summary>
    public string Title
    {
        get => _title;
        set => SetProperty(ref _title, value);
    }

    /// <summary>
    /// Inverse of IsBusy for binding to IsEnabled properties.
    /// </summary>
    public bool IsNotBusy => !IsBusy;

    /// <summary>
    /// Event raised when a property value changes.
    /// </summary>
    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>
    /// Sets a property value and raises PropertyChanged if the value changed.
    /// </summary>
    /// <typeparam name="T">Type of the property.</typeparam>
    /// <param name="backingStore">Reference to the backing field.</param>
    /// <param name="value">New value to set.</param>
    /// <param name="propertyName">Name of the property (auto-filled).</param>
    /// <param name="onChanged">Optional action to invoke when value changes.</param>
    /// <returns>True if the value was changed.</returns>
    protected bool SetProperty<T>(
        ref T backingStore,
        T value,
        [CallerMemberName] string propertyName = "",
        Action? onChanged = null)
    {
        if (EqualityComparer<T>.Default.Equals(backingStore, value))
            return false;

        backingStore = value;
        onChanged?.Invoke();
        OnPropertyChanged(propertyName);

        // Also notify IsNotBusy when IsBusy changes
        if (propertyName == nameof(IsBusy))
        {
            OnPropertyChanged(nameof(IsNotBusy));
        }

        return true;
    }

    /// <summary>
    /// Raises the PropertyChanged event.
    /// </summary>
    /// <param name="propertyName">Name of the changed property.</param>
    protected void OnPropertyChanged([CallerMemberName] string propertyName = "")
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    /// <summary>
    /// Called when the page appears. Override in derived classes.
    /// </summary>
    public virtual Task OnAppearingAsync()
    {
        return Task.CompletedTask;
    }

    /// <summary>
    /// Called when the page disappears. Override in derived classes.
    /// </summary>
    public virtual Task OnDisappearingAsync()
    {
        return Task.CompletedTask;
    }
}

/// <summary>
/// Relay command implementation for MVVM command binding.
/// </summary>
public class RelayCommand : ICommand
{
    private readonly Action<object?> _execute;
    private readonly Func<object?, bool>? _canExecute;

    public RelayCommand(Action<object?> execute, Func<object?, bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public RelayCommand(Action execute, Func<bool>? canExecute = null)
        : this(_ => execute(), canExecute != null ? _ => canExecute() : null)
    {
    }

    public event EventHandler? CanExecuteChanged;

    public bool CanExecute(object? parameter) => _canExecute?.Invoke(parameter) ?? true;

    public void Execute(object? parameter) => _execute(parameter);

    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}

/// <summary>
/// Generic relay command that accepts a typed parameter.
/// </summary>
public class RelayCommand<T> : ICommand
{
    private readonly Action<T?> _execute;
    private readonly Func<T?, bool>? _canExecute;

    public RelayCommand(Action<T?> execute, Func<T?, bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged;

    public bool CanExecute(object? parameter) => _canExecute?.Invoke(parameter is T t ? t : default) ?? true;

    public void Execute(object? parameter) => _execute(parameter is T t ? t : default);

    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}

/// <summary>
/// Async relay command implementation for MVVM command binding.
/// </summary>
public class AsyncRelayCommand : ICommand
{
    private readonly Func<object?, Task> _execute;
    private readonly Func<object?, bool>? _canExecute;
    private bool _isExecuting;

    public AsyncRelayCommand(Func<object?, Task> execute, Func<object?, bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public AsyncRelayCommand(Func<Task> execute, Func<bool>? canExecute = null)
        : this(_ => execute(), canExecute != null ? _ => canExecute() : null)
    {
    }

    public event EventHandler? CanExecuteChanged;

    public bool CanExecute(object? parameter) => !_isExecuting && (_canExecute?.Invoke(parameter) ?? true);

    public async void Execute(object? parameter)
    {
        if (_isExecuting) return;

        _isExecuting = true;
        RaiseCanExecuteChanged();

        try
        {
            await _execute(parameter);
        }
        finally
        {
            _isExecuting = false;
            RaiseCanExecuteChanged();
        }
    }

    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}

/// <summary>
/// Generic async relay command that accepts a typed parameter.
/// </summary>
public class AsyncRelayCommand<T> : ICommand
{
    private readonly Func<T?, Task> _execute;
    private readonly Func<T?, bool>? _canExecute;
    private bool _isExecuting;

    public AsyncRelayCommand(Func<T?, Task> execute, Func<T?, bool>? canExecute = null)
    {
        _execute    = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged;

    public bool CanExecute(object? parameter)
        => !_isExecuting && (_canExecute?.Invoke(parameter is T t ? t : default) ?? true);

    public async void Execute(object? parameter)
    {
        if (_isExecuting) return;
        _isExecuting = true;
        RaiseCanExecuteChanged();
        try
        {
            await _execute(parameter is T typed ? typed : default);
        }
        finally
        {
            _isExecuting = false;
            RaiseCanExecuteChanged();
        }
    }

    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}
