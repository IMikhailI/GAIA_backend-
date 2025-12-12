from django.db import models


class Review(models.Model):
    name = models.CharField("Имя", max_length=100)
    avatar = models.ImageField(
        "Фото",
        upload_to="reviews/avatars/",
        blank=True,
        null=True,
    )
    rating = models.PositiveSmallIntegerField(
        "Оценка",
        choices=[(i, str(i)) for i in range(1, 6)],
    )
    text = models.TextField("Отзыв")
    is_published = models.BooleanField(
        "Показывать на сайте",
        default=True,
        help_text="Если выключено — отзыв не отдаётся во фронт.",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.rating})"

