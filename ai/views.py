from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from openai import OpenAI

from .models import Conversation, Message


@login_required
@require_POST
def chat(request):

    question = request.POST.get("question", "").strip()
    conversation_id = request.POST.get("conversation_id", "").strip()

    # الملف المرفق
    uploaded_file = request.FILES.get("file")

    if not question:
        return JsonResponse(
            {"error": "الرجاء كتابة السؤال."},
            status=400
        )

    if not settings.OPENAI_API_KEY:
        return JsonResponse(
            {
                "error":
                    "مفتاح OpenAI غير مُعد في إعدادات المشروع."
            },
            status=500
        )

    # =====================================================
    # الحصول على المحادثة الحالية أو إنشاء محادثة جديدة
    # =====================================================

    if conversation_id:

        conversation = Conversation.objects.filter(
            id=conversation_id,
            user=request.user,
        ).first()

        if not conversation:
            return JsonResponse(
                {"error": "المحادثة غير موجودة."},
                status=404
            )

    else:

        conversation = Conversation.objects.create(
            user=request.user,
            title=question[:60],
        )

    # =====================================================
    # حفظ رسالة المستخدم والملف المرفق
    # =====================================================

    user_message = Message.objects.create(
        conversation=conversation,
        role="user",
        content=question,
        attachment=uploaded_file,
        attachment_name=(
            uploaded_file.name
            if uploaded_file
            else ""
        ),
        attachment_type=(
            uploaded_file.content_type
            if uploaded_file
            else ""
        ),
    )

    # =====================================================
    # إرسال المحادثة إلى OpenAI
    # =====================================================

    try:

        client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

        messages = []

        previous_messages = (
            conversation.messages
            .order_by("created_at")
        )

        for message in previous_messages:

            # -------------------------------------------------
            # رسالة المستخدم التي تحتوي على صورة
            # -------------------------------------------------

            if (
                message.role == "user"
                and message.attachment
                and message.attachment_type.startswith("image/")
            ):

                import base64

                message.attachment.open("rb")

                image_bytes = (
                    message.attachment.read()
                )

                message.attachment.close()

                image_base64 = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                image_url = (
                    "data:"
                    + message.attachment_type
                    + ";base64,"
                    + image_base64
                )

                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": message.content,
                            },
                            {
                                "type": "input_image",
                                "image_url": image_url,
                            },
                        ],
                    }
                )

            # -------------------------------------------------
            # الرسائل العادية
            # -------------------------------------------------

            else:

                messages.append(
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                )

        # =====================================================
        # إرسال المحادثة إلى OpenAI
        # =====================================================

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=messages,
        )

        answer = response.output_text

    except Exception as e:

        return JsonResponse(
            {
                "error":
                    "حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: "
                    + str(e)
            },
            status=500
        )

    # =====================================================
    # حفظ رد المساعد
    # =====================================================

    Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=answer,
    )

    # =====================================================
    # تحديث المحادثة
    # =====================================================

    conversation.save()

    # =====================================================
    # إرسال النتيجة للواجهة
    # =====================================================

    return JsonResponse(
        {
            "conversation_id": conversation.id,
            "answer": answer,
            "title": conversation.title,
        }
    )

@login_required
def conversations(request):

    items = Conversation.objects.filter(
        user=request.user
    ).values(
        "id",
        "title",
        "updated_at",
    )

    return JsonResponse(
        {
            "conversations": list(items)
        }
    )


@login_required
def conversation_messages(
    request,
    conversation_id
):

    conversation = Conversation.objects.filter(
        id=conversation_id,
        user=request.user,
    ).first()

    if not conversation:

        return JsonResponse(
            {
                "error":
                    "المحادثة غير موجودة."
            },
            status=404
        )

    messages = (
        conversation.messages
        .order_by("created_at")
    )

    return JsonResponse(
        {
            "conversation_id":
                conversation.id,

            "title":
                conversation.title,

            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
        }
    )
