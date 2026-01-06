def layout_direction(request):
    lang = request.session.get("django_language", "ar")
    direction = "rtl" if lang in ["ar", "fa", "ur"] else "ltr"
    return {
        "active_language": lang,
        "direction": direction,
    }
