import flet as ft
from typing import Optional # Added Optional for type hinting

class NumberDecimalField(ft.TextField):
    def __init__(self,
                 label: str = "Enter number",
                 hint_text: Optional[str] = None,  # Allow None
                 is_money_field: bool = False,
                 currency_symbol: str = "$",
                 is_integer_only: bool = False,
                 **kwargs):

        self.is_integer_only = is_integer_only
        self.is_money_field = is_money_field
        self.currency_symbol = currency_symbol # Store for potential use
        self.last_valid_value = "" # Stores the last known good value

        current_regex_string = r"[0-9]" if self.is_integer_only else r"[0-9.]"

        if hint_text is None:
            if self.is_integer_only:
                default_hint = "e.g., 123"
            elif self.is_money_field:
                # For money, hint usually includes symbol and decimal format
                default_hint = f"e.g., {self.currency_symbol}10.50" if not self.is_integer_only else f"e.g., {self.currency_symbol}10"
            else: # Generic decimal
                default_hint = "e.g., 10.99 or 10"
        else:
            default_hint = hint_text

        prefix_widget = None
        if self.is_money_field: # Show currency symbol for money fields (int or decimal)
            prefix_widget = ft.Text(self.currency_symbol, weight=ft.FontWeight.BOLD, size=16, text_align=ft.TextAlign.CENTER)


        super().__init__(
            label=label,
            hint_text=default_hint,
            # Remove the input_filter as it's causing the backspace issue
            # We'll handle validation purely in the on_change event
            keyboard_type=ft.KeyboardType.NUMBER, # Suggests numeric keyboard
            on_change=self._validate_input_on_change, # Changed to more descriptive name
            prefix=prefix_widget, # Use prefix for currency symbol
            **kwargs
        )

    def _is_valid_current_format(self, value: str) -> bool:
        """Checks if the current string value is a valid number format based on field type."""
        if not value: # Empty is valid during typing
            return True
        if self.is_integer_only:
            return value.isdigit()
        # Decimal or money (which is also decimal unless specified as integer only, handled above)
        if value.count('.') > 1:
            return False
        if value == ".": # A single dot is not a valid number
            return False
        try:
            float(value) # Check if convertible to float
            return True
        except ValueError:
            return False

    def _validate_input_on_change(self, e: ft.ControlEvent):
        """Validates the input on each change event."""
        current_value = e.control.value

        # Check for non-numeric characters (except '.' if decimals allowed)
        if current_value:
            # Filter characters that don't match our pattern
            valid_chars = "0123456789" if self.is_integer_only else "0123456789."
            filtered_value = ''.join(c for c in current_value if c in valid_chars)

            # If decimal, handle multiple dots
            if not self.is_integer_only and filtered_value.count('.') > 1:
                dots = [i for i, c in enumerate(filtered_value) if c == '.']
                # Keep only the first dot
                for i in reversed(dots[1:]):
                    filtered_value = filtered_value[:i] + filtered_value[i+1:]

            # If we had to filter something, update the field
            if filtered_value != current_value:
                e.control.value = filtered_value
                current_value = filtered_value
                e.control.update()

        # Always allow empty field
        if not current_value:
            self.last_valid_value = ""
            if e.control.error_text:
                e.control.error_text = None
            return

        # Now handle validation of the format
        if self._is_valid_current_format(current_value):
            # For money fields, check decimal places
            if self.is_money_field and not self.is_integer_only and '.' in current_value:
                parts = current_value.split('.')
                if len(parts) > 1 and len(parts[1]) > 2:  # Max 2 decimal places
                    # Truncate to 2 decimal places instead of reverting
                    e.control.value = parts[0] + '.' + parts[1][:2]
                    e.control.update()
                    current_value = e.control.value

            # Update last valid value
            self.last_valid_value = current_value
            if e.control.error_text:  # Clear error if input becomes valid
                e.control.error_text = None
        else:
            # Single dot is not valid as a number but valid during typing
            if current_value == ".":
                self.last_valid_value = current_value
            else:
                # Invalid format but we'll let user continue typing
                # for now, just update the last_valid_value if it's empty
                if not self.last_valid_value:
                    self.last_valid_value = current_value

    def get_value_as_int(self) -> Optional[int]:
        """Returns the current value as an integer, or None if invalid or not an integer."""
        if self.value and self._is_valid_current_format(self.value):
            try:
                if self.is_integer_only:
                    return int(self.value)
                # For decimal fields, return int if it's a whole number
                f_val = float(self.value)
                if f_val == int(f_val):
                    return int(f_val)
            except ValueError:
                return None # Should ideally be caught by _is_valid_current_format
        return None

    def get_value_as_float(self) -> Optional[float]:
        """Returns the current value as a float, or None if invalid."""
        if self.value and self._is_valid_current_format(self.value):
            try:
                # Ensure money format (2 decimal places) isn't violated on final get
                if self.is_money_field and not self.is_integer_only and '.' in self.value:
                    parts = self.value.split('.')
                    if len(parts) > 1 and len(parts[1]) > 2:
                        # This state should ideally be prevented by on_change, but as a safeguard
                        return None
                return float(self.value)
            except ValueError:
                return None
        return None

    def get_value_as_str(self) -> str:
        """Returns the raw string value."""
        return self.value if self.value else ""

    def clear(self):
        """Clears the input field."""
        self.value = ""
        self.last_valid_value = ""
        self.error_text = None
        self.update()