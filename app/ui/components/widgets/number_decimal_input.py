import flet as ft

class NumberDecimalField(ft.TextField):
    def __init__(self,
                 label: str = "Enter number",
                 hint_text: str | None = None,  # Allow None to set default based on type
                 is_money_field: bool = False,
                 currency_symbol: str = "$",
                 is_integer_only: bool = False, # New argument
                 **kwargs):

        self.is_integer_only = is_integer_only # Store this early for use in defaults
        self.is_money_field = is_money_field
        self.last_valid_value = ""

        # Determine regex for input_filter
        current_regex_string = r"[0-9]" if self.is_integer_only else r"[0-9.]"

        # Determine default hint_text if not provided
        if hint_text is None:
            if self.is_integer_only:
                default_hint = "e.g., 123"
            elif self.is_money_field:
                default_hint = f"e.g., {currency_symbol}10.50"
            else:
                default_hint = "e.g., 10.99 or 10"
        else:
            default_hint = hint_text


        prefix_icon_widget = None
        if self.is_money_field and not self.is_integer_only: # Money fields are typically decimal
            prefix_icon_widget = ft.Text(currency_symbol, weight=ft.FontWeight.BOLD, size=16)
        elif self.is_money_field and self.is_integer_only: # Money field that must be integer (e.g. cents)
            prefix_icon_widget = ft.Text(currency_symbol, weight=ft.FontWeight.BOLD, size=16)


        super().__init__(
            label=label,
            hint_text=default_hint,
            input_filter=ft.InputFilter(
                allow=True,
                regex_string=current_regex_string,
                replacement_string=""
            ),
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._validate_input,
            prefix=prefix_icon_widget,
            **kwargs
        )


    def _is_valid_format(self, value: str) -> bool:
        if not value: # Empty string is valid during input
            return True

        if self.is_integer_only:
            return value.isdigit() # Checks if all characters are digits and not empty
        else: # Decimal or money (which is also decimal)
            if value.count('.') > 1:
                return False
            try:
                float(value) # Try to convert to float
                if value == ".": # Single dot is not valid
                    return False
                return True
            except ValueError:
                return False

    def _validate_input(self, e: ft.ControlEvent):
        current_value = e.control.value

        # Early exit for integer-only if a dot is present after input_filter (e.g., pasting)
        if self.is_integer_only and '.' in current_value:
            e.control.value = self.last_valid_value
            e.control.error_text = "Only whole numbers allowed"
            e.control.update()
            return

        if self._is_valid_format(current_value):
            if self.is_money_field and not self.is_integer_only and '.' in current_value:
                parts = current_value.split('.')
                if len(parts) > 1 and len(parts[1]) > 2:
                    e.control.value = self.last_valid_value
                    e.control.error_text = "Max 2 decimal places for money"
                    e.control.update()
                    return

            self.last_valid_value = current_value
            if e.control.error_text:
                e.control.error_text = None
                e.control.update()
        else:
            e.control.value = self.last_valid_value
            e.control.error_text = "Invalid number format"
            e.control.update()

    def get_value_as_int(self) -> int | None:
        if self.value and self.is_integer_only and self._is_valid_format(self.value):
            try:
                return int(self.value)
            except ValueError:
                return None
        elif self.value and not self.is_integer_only and self._is_valid_format(self.value):
            # If it's a decimal field but the value is an integer (e.g. "10")
            try:
                # Check if it's a whole number float
                f_val = float(self.value)
                if f_val == int(f_val):
                    return int(f_val)
            except ValueError:
                return None # Should not happen if _is_valid_format passed
        return None

    def get_value_as_float(self) -> float | None:
        if self.value and not self.is_integer_only and self._is_valid_format(self.value):
            if self.is_money_field and '.' in self.value:
                parts = self.value.split('.')
                if len(parts) > 1 and len(parts[1]) > 2:
                    return None
            try:
                return float(self.value)
            except ValueError:
                return None
        elif self.value and self.is_integer_only and self._is_valid_format(self.value):
            # If it's an integer field, can still be represented as float
            try:
                return float(self.value)
            except ValueError:
                return None
        return None

    def get_value_as_str(self) -> str:
        return self.value if self.value else ""