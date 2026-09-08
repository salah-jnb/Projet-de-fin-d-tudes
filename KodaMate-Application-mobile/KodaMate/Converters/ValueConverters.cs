using System.Globalization;

namespace KodaMate.Converters;

/// <summary>
/// Converts a boolean to its inverse.
/// </summary>
public class InvertedBoolConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool boolValue)
            return !boolValue;
        return value;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool boolValue)
            return !boolValue;
        return value;
    }
}

/// <summary>
/// Converts connection status to color.
/// </summary>
public class BoolToColorConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isConnected)
        {
            return isConnected
                ? Color.FromArgb("#00E676") // AccentGreen
                : Color.FromArgb("#FF5252"); // AccentRed
        }
        return Colors.Gray;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts integer (0-100) to progress (0.0-1.0).
/// </summary>
public class IntToProgressConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is int intValue)
            return intValue / 100.0;
        return 0.0;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts power state to gradient start color.
/// </summary>
public class BoolToGradientStartConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isPoweredOn)
        {
            return isPoweredOn
                ? Color.FromArgb("#00E5FF") // Cyan
                : Color.FromArgb("#37474F"); // Dark gray
        }
        return Color.FromArgb("#37474F");
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts power state to gradient end color.
/// </summary>
public class BoolToGradientEndConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isPoweredOn)
        {
            return isPoweredOn
                ? Color.FromArgb("#2979FF") // Blue
                : Color.FromArgb("#263238"); // Darker gray
        }
        return Color.FromArgb("#263238");
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts boolean to opacity value.
/// </summary>
public class BoolToOpacityConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool boolValue)
        {
            // For completed items, return lower opacity
            return boolValue ? 0.5 : 1.0;
        }
        return 1.0;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts power state to button text.
/// </summary>
public class BoolToPowerTextConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isPoweredOn)
            return isPoweredOn ? "TAP TO STOP" : "TAP TO START";
        return "TAP TO START";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts power state to status text.
/// </summary>
public class BoolToStatusTextConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isPoweredOn)
            return isPoweredOn ? "Koda is Active" : "Koda is Sleeping";
        return "Koda is Sleeping";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts integer to boolean (for visibility when count > 0).
/// </summary>
public class IntToBoolConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is int intValue)
        {
            if (parameter != null && int.TryParse(parameter.ToString(), out int compareValue))
                return intValue == compareValue;

            return intValue > 0;
        }
        return false;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts boolean to font family (for read/unread state).
/// </summary>
public class BoolToFontFamilyConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isRead)
            return isRead ? "OpenSansRegular" : "OpenSansSemibold";
        return "OpenSansRegular";
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts tab index to background color.
/// </summary>
public class TabIndexToColorConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is int selectedIndex && parameter is string indexParam)
        {
            if (int.TryParse(indexParam, out int tabIndex))
            {
                return selectedIndex == tabIndex
                    ? Color.FromArgb("#2979FF") // AccentBlue
                    : Colors.Transparent;
            }
        }
        return Colors.Transparent;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts boolean to text decoration (strikethrough for completed).
/// </summary>
public class BoolToTextDecorationConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is bool isCompleted)
            return isCompleted ? TextDecorations.Strikethrough : TextDecorations.None;
        return TextDecorations.None;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts string to boolean (for visibility when string is not empty).
/// </summary>
public class StringToBoolConverter : IValueConverter
{
    public object? Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value is string stringValue)
            return !string.IsNullOrWhiteSpace(stringValue);
        return false;
    }

    public object? ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}
