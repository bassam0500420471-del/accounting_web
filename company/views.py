from django.shortcuts import render, redirect
from .models import CompanyInfo

def company_settings(request):
    company = CompanyInfo.objects.first()

    if request.method == "POST":
        name = request.POST.get("name")
        commercial = request.POST.get("commercial_number")
        tax = request.POST.get("tax_number")
        address = request.POST.get("address")
        phone = request.POST.get("phone")

        # تحديث
        if company:
            company.name = name
            company.commercial_number = commercial
            company.tax_number = tax
            company.address = address
            company.phone = phone

            if 'logo' in request.FILES:
                company.logo = request.FILES['logo']

            company.save()

        # إنشاء جديد
        else:
            CompanyInfo.objects.create(
                name=name,
                commercial_number=commercial,
                tax_number=tax,
                address=address,
                phone=phone,
                logo=request.FILES.get('logo')
            )

        return redirect("company_settings")

    return render(request, "company/settings.html", {
        "company": company
    })
