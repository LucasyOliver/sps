from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView


class LivenessCheckView(View):
    http_method_names = ['get', 'head']

    def get(self, request, *args, **kwargs):
        return JsonResponse({'status': 'ok', 'check': 'liveness'}, status=200)


class ReadinessCheckView(View):
    http_method_names = ['get', 'head']

    def get(self, request, *args, **kwargs):
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except OperationalError:
            return JsonResponse(
                {'status': 'unavailable', 'database': 'error'},
                status=503,
            )
        return JsonResponse({'status': 'ready', 'database': 'ok'}, status=200)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'base/home.html'
