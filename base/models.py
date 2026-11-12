from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_salon(self, salon):
        if salon is None:
            return self.none()
        salon_id = getattr(salon, 'pk', salon)
        return self.filter(salon_id=salon_id)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_salon(self, salon):
        return self.get_queryset().for_salon(salon)


class TenantScopedModel(TimeStampedModel):
    salon = models.ForeignKey(
        'salons.Salon',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        verbose_name='Salão',
    )

    objects = TenantManager()

    class Meta:
        abstract = True
