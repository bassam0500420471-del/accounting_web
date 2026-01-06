class Account(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children"   # 🔴 هذا هو المفتاح
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
