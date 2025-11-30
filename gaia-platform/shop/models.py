from django.db import models
from django.utils.text import slugify


class ProductCategory(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    slug = models.SlugField("Слаг", max_length=120, unique=True)
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)

    class Meta:
        verbose_name = "Категория товара"
        verbose_name_plural = "Категории товаров"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Категория",
    )
    name = models.CharField("Название", max_length=150)
    slug = models.SlugField("Слаг", max_length=160, unique=True)
    description = models.TextField("Описание", blank=True)

    price = models.DecimalField(
        "Цена",
        max_digits=10,
        decimal_places=2,
        help_text="Цена в рублях",
    )

    is_active = models.BooleanField("Показывать на сайте", default=True)

    image = models.ImageField(
        "Фото",
        upload_to="products/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
