import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from zatca.models import ZatcaSettings

@login_required
def settings_view(request):
    company = request.company
    zatca_settings, created = ZatcaSettings.objects.get_or_create(company=company)

    if request.method == 'POST':
        action = request.POST.get('action') 

        if action == 'save':
            zatca_settings.environment = request.POST.get('environment')
            zatca_settings.is_enabled = (request.POST.get('is_active') == 'on')
            zatca_settings.save()
            messages.success(request, "تم حفظ الإعدادات بنجاح.")
        
        elif action == 'start_onboarding':
            otp = request.POST.get('otp_code')
            if otp:
                # رابط API الهيئة (Sandbox)
                url = "https://gw-fatoora.zatca.sa/e-invoicing/developer-portal/compliance"
                
                # إعداد الترويسات المطلوبة للاتصال
                headers = {
                    "OTP": otp,
                    "Accept-Language": "en"
                }
                
                # يجب جلب ملف الـ CSR الخاص بالشركة من نظامك (تأكد من المسار أو الحقل الصحيح)
                # مثال: csr = zatca_settings.csr_content 
                payload = {
                    "csr": "---BEGIN CERTIFICATE REQUEST---...---END CERTIFICATE REQUEST---" 
                }
                
                try:
                    # إرسال الطلب للهيئة
                    response = requests.post(url, json=payload, headers=headers)
                    
                    # طباعة الرد في الترمينال للمتابعة (مهم جداً للتصحيح)
                    print(f"DEBUG: Response Status: {response.status_code}")
                    print(f"DEBUG: Response Content: {response.text}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        zatca_settings.compliance_request_id = data.get('requestID')
                        zatca_settings.binary_security_token = data.get('binarySecurityToken')
                        zatca_settings.save()
                        messages.success(request, "تم بنجاح ربط النظام مع هيئة الزكاة!")
                    else:
                        messages.error(request, f"فشل الربط: تلقينا رمز خطأ {response.status_code} من الهيئة.")
                        
                except Exception as e:
                    messages.error(request, f"حدث خطأ أثناء الاتصال: {str(e)}")
            else:
                messages.error(request, "يرجى إدخال رمز OTP أولاً.")
        
        return redirect('zatca:settings') 

    context = {
        "company": company,
        "zatca_settings": zatca_settings,
    }
    return render(request, "zatca/settings.html", context)