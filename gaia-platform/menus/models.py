from django.db import models


class MenuFile(models.Model):
    title = models.CharField("Название", max_length=200)
    file = models.FileField("PDF файл", upload_to="menus/")
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Загружен", auto_now_add=True)

    class Meta:
        verbose_name = "Файл меню"
        verbose_name_plural = "Файлы меню"
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return self.title
