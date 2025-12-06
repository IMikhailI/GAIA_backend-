# menus/models.py
from django.db import models
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path


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

    def regenerate_pages(self):
        """Разбивает PDF на PNG-страницы и пересоздаёт MenuPage."""
        if not self.file:
            return

        pdf_path = Path(self.file.path)
        if not pdf_path.exists():
            return

        # удалить старые страницы
        self.pages.all().delete()

        images = convert_from_path(str(pdf_path), dpi=200)

        for index, pil_image in enumerate(images, start=1):
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            buffer.seek(0)

            page = MenuPage(menu_file=self, page_number=index)
            filename = f"menu_{self.pk}_page_{index}.png"
            page.image.save(filename, ContentFile(buffer.read()), save=True)


class MenuPage(models.Model):
    menu_file = models.ForeignKey(
        MenuFile,
        on_delete=models.CASCADE,
        related_name="pages",
        verbose_name="Меню (PDF)",
    )
    page_number = models.PositiveIntegerField("Номер страницы")
    image = models.ImageField("PNG-страница", upload_to="menus/pages/")

    class Meta:
        verbose_name = "Страница меню"
        verbose_name_plural = "Страницы меню"
        ordering = ["menu_file", "page_number"]
        unique_together = ("menu_file", "page_number")

    def __str__(self):
        return f"{self.menu_file.title} — стр. {self.page_number}"


@receiver(post_save, sender=MenuFile)
def generate_menu_pages_on_save(sender, instance: MenuFile, created, **kwargs):
    """
    Автоматически генерим PNG-страницы при каждом сохранении MenuFile,
    если есть прикреплённый PDF.
    """
    if instance.file:
        instance.regenerate_pages()

