from django.db import models

class Brand(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)

    def __str__(self):
            return self.name


class Car(models.Model):
    id = models.AutoField(primary_key=True)
    model = models.CharField(max_length=60)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='car_brand')
    model_year = models.IntegerField()
    plate = models.CharField(max_length=60)
    seats = models.IntegerField()
    photo = models.ImageField(upload_to='cars/', null=True, blank=True)

    def __str__(self):
        return self.model