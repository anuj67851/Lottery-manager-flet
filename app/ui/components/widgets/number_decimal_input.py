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
            input_filter=ft.InputFilter(
                allow=True, # Allow based on regex
                regex_string=current_regex_string,
                replacement_string="" # Discard non-matching characters
            ),
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

        # Filter for integer-only fields (e.g., if user pastes a decimal)
        if self.is_integer_only and '.' in current_value:
            e.control.value = self.last_valid_value # Revert to last valid
            e.control.error_text = "Only whole numbers allowed."
            e.control.update()
            return

        if self._is_valid_current_format(current_value):
            # For money fields (non-integer), check decimal places
            if self.is_money_field and not self.is_integer_only and '.' in current_value:
                parts = current_value.split('.')
                if len(parts) > 1 and len(parts[1]) > 2: # Max 2 decimal places
                    e.control.value = self.last_valid_value # Revert
                    e.control.error_text = "Max 2 decimal places for money."
                    e.control.update()
                    return

            self.last_valid_value = current_value # Update last valid value
            if e.control.error_text: # Clear error if input becomes valid
                e.control.error_text = None
                e.control.update()
        else:
            # Revert to last valid value if current input is invalid
            e.control.value = self.last_valid_value
            e.control.error_text = "Invalid number format." # Generic error
            e.control.update()

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