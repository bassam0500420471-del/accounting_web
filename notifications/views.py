from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def mark_notification_read(request, pk):

    print("=" * 50)
    print("MARK READ")
    print("PK:", pk)

    try:
        company = request.user.profile.company
        store = company.store
        print("STORE:", store)
    except Exception as e:
        print("STORE ERROR:", e)
        store = None

    notification = Notification.objects.filter(
        id=pk,
        store=store
    ).first()

    print("NOTIFICATION:", notification)

    if notification:
        notification.is_read = True
        notification.save()
        print("UPDATED")

    print("=" * 50)

    next_url = request.GET.get("next")

    if next_url:
        return redirect(next_url)

    return redirect("/")