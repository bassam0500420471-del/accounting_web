from django.http import HttpResponse
from django.contrib.staticfiles import finders


def service_worker(request):

    file_path = finders.find(
        "ecommerce/service-worker.js"
    )

    if not file_path:
        return HttpResponse(
            "Service Worker not found",
            status=404
        )

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()

    response = HttpResponse(
        content,
        content_type="application/javascript"
    )

    response["Service-Worker-Allowed"] = "/"

    return response