from django import forms
from datetime import datetime, time
from halls.models import Hall


HOUR_CHOICES = [(f"{h:02}:00", f"{h:02}:00") for h in range(9, 21)]  # 09:00–20:00


class BookingForm(forms.Form):
    hall = forms.ModelChoiceField(queryset=Hall.objects.all(), label="Зал")
    date = forms.DateField(label="Дата", widget=forms.DateInput(attrs={"type": "date"}))

    start_time = forms.ChoiceField(
        label="Время начала",
        choices=HOUR_CHOICES,
    )

    duration_hours = forms.IntegerField(
        label="Длительность (часы)",
        min_value=1,
        max_value=12,
        initial=1,
    )

    customer_name = forms.CharField(label="Имя", max_length=100)
    customer_phone = forms.CharField(label="Телефон", max_length=50)
    customer_email = forms.EmailField(label="Email")

    comment = forms.CharField(
        label="Комментарий",
        widget=forms.Textarea,
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        start_time_str = cleaned_data.get("start_time")  # строка вида "10:00"

        if date and start_time_str:
            hours, minutes = map(int, start_time_str.split(":"))
            t = time(hour=hours, minute=minutes)
            start_dt = datetime.combine(date, t)
            cleaned_data["start_datetime"] = start_dt

        return cleaned_data
