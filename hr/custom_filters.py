from django import template

register = template.Library()

@register.filter
def my_upper(value):
    return value.upper()
