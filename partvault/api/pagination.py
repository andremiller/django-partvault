from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


def positive_integer(value, field, maximum=9223372036854775807):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValidationError({field: ["Use a positive integer."]})
    # Bound before int conversion (including Python's maximum integer-string length).
    if len(value) > 19 or not 1 <= int(value) <= maximum:
        raise ValidationError({field: [f"Use an integer from 1 to {maximum}."]})
    return int(value)


def validate_query(params, allowed, repeated=()):
    errors = {}
    for key in params:
        if key not in allowed:
            errors[key] = ["Unsupported query parameter."]
        elif key not in repeated and len(params.getlist(key)) != 1:
            errors[key] = ["Supply this parameter only once."]
    if errors:
        raise ValidationError(errors)


class StrictPageNumberPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100
    last_page_strings = ()

    def get_page_size(self, request):
        if self.page_size_query_param in request.query_params:
            return positive_integer(
                request.query_params[self.page_size_query_param],
                self.page_size_query_param,
                self.max_page_size,
            )
        return self.page_size

    def get_page_number(self, request, paginator):
        if self.page_query_param in request.query_params:
            return positive_integer(
                request.query_params[self.page_query_param], self.page_query_param
            )
        return 1
