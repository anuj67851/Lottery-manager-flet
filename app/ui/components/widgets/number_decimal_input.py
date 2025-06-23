import flet as ft
from typing import Optional

class NumberDecimalField(ft.TextField):
    def __init__(self,
                 label: str = "Enter number",
                 hint_text: Optional[str] = None,
                 is_money_field: bool = False,
                 currency_symbol: str = "$",
                 is_integer_only: bool = False,
                 **kwargs):

        # Store configuration
        self.is_money_field = is_money_field
        self.is_integer_only = is_integer_only

        # This internal state is ONLY for the special calculator-style money input
        self._internal_digits = ""

        # --- Set up behavior based on field type ---
        if self.is_money_field and not self.is_integer_only:
            # Special calculator-style money input
            kwargs['on_change'] = self._handle_money_change
            kwargs['value'] = "0.00" # Initial display
        else:
            # Standard behavior for integers and regular decimals
            # No input filter; we validate on blur for a better UX
            kwargs['on_blur'] = self._format_standard_on_blur

        # Common properties
        if hint_text is None:
            hint_text = "e.g., 123" if self.is_integer_only else "e.g., 10.50"

        kwargs['label'] = label
        kwargs['hint_text'] = hint_text
        kwargs['keyboard_type'] = ft.KeyboardType.NUMBER
        kwargs['prefix'] = ft.Text(currency_symbol) if is_money_field else None

        super().__init__(**kwargs)

    def _handle_money_change(self, e: ft.ControlEvent):
        """Handles the special calculator-style input for money fields."""
        new_digits = "".join(filter(str.isdigit, e.control.value))
        if new_digits == self._internal_digits:
            return
        self._internal_digits = new_digits

        if not self._internal_digits:
            formatted_value = "0.00"
        else:
            numeric_value = int(self._internal_digits)
            formatted_value = f"{numeric_value / 100.0:.2f}"

        e.control.value = formatted_value
        e.control.update()

    def _format_standard_on_blur(self, e: ft.ControlEvent):
        """Validates and formats standard integer/decimal fields when the user clicks away."""
        value = e.control.value.strip()

        # If the user cleared the field, respect that. Clear any existing error.
        if not value:
            if e.control.error_text:
                e.control.error_text = None
                e.control.update()
            return

        try:
            if self.is_integer_only:
                # Allows only whole numbers
                if not value.isdigit():
                    raise ValueError("Contains non-digit characters.")
                e.control.value = str(int(value))
            else: # Standard decimal
                # Allows a valid floating point number
                if value.count('.') > 1:
                    raise ValueError("Contains multiple decimal points.")
                float(value) # This will raise ValueError if invalid format like "1.2.3" or "."

            # If we reach here, the number is valid. Clear any previous error.
            if e.control.error_text:
                e.control.error_text = None
        except ValueError:
            e.control.error_text = "Invalid number"

        e.control.update()

    def get_value_as_float(self) -> Optional[float]:
        """Returns the current value as a float, or None if invalid."""
        if self.is_money_field and not self.is_integer_only:
            return float(self.value) if self.value else 0.0

        value = self.value.strip()
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_value_as_int(self) -> Optional[int]:
        """Returns the current value as an integer, or None if invalid."""
        float_val = self.get_value_as_float()
        if float_val is not None:
            # Check if it's a whole number before converting
            if float_val == int(float_val):
                return int(float_val)
        return None

    def get_value_as_str(self) -> str:
        """Returns the raw string value."""
        return self.value.strip() if self.value else ""

    def clear(self):
        """Clears the input field and resets its state."""
        if self.is_money_field and not self.is_integer_only:
            self.value = "0.00"
            self._internal_digits = ""
        else:
            self.value = ""
        self.error_text = None
        if self.page: # Check if page is available before updating
            self.update()