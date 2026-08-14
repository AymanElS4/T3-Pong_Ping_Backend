import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from client.models import Rol, Usuario, CodigoLegal, Notificacion

pytestmark = pytest.mark.django_db


class TestHU05ArticleNotificationService:
    """Pruebas automatizadas para HU-05: Notificar a los usuarios sobre cambios en un artículo legal."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.client = APIClient()
        self.admin_role = Rol.objects.create(nombre='Administrador', descripcion='Admin del sistema')
        self.user_role = Rol.objects.create(nombre='Profesional', descripcion='Usuario regular')

        self.admin = Usuario.objects.create_user(
            email='admin_hu05@gmail.com',
            password='PasswordAdmin123',
            nombre='Admin HU05',
            oid_rol=self.admin_role,
            is_staff=True,
            is_superuser=True
        )

        self.user = Usuario.objects.create_user(
            email='abogado_hu05@gmail.com',
            password='PasswordUser123',
            nombre='Abogado HU05',
            oid_rol=self.user_role
        )

        self.articulo = CodigoLegal.objects.create(
            nombre_norma='COIP',
            numero_articulo='144',
            texto_contenido='Texto original del homicidio...',
            vigencia=True
        )

    # TC-21: Equivalence Partitioning / Happy Path - Modificar artículo genera notificación automática
    def test_update_article_automatically_creates_global_notification(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('codigo-legal-detail', args=[self.articulo.oid_codigo])

        payload = {
            "nombre_norma": "COIP",
            "numero_articulo": "144",
            "texto_contenido": "Texto modificado del artículo 144 COIP...",
            "vigencia": False  # Modificamos a histórico/derogado
        }

        response = self.client.put(url, payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        
        # Verificar la creación automática de la notificación en BD (HU-05)
        notif = Notificacion.objects.filter(tipo='articulo').first()
        assert notif is not None
        assert "COIP Art. 144" in notif.titulo
        assert "Se han registrado modificaciones" in notif.mensaje
        assert notif.oid_usuario is None  # Es una notificación global para los usuarios

    # TC-22: Decision Table - Usuarios regulares consultan notificaciones de cambio de artículo
    def test_users_can_fetch_article_change_notifications(self):
        # Insertar notificación de cambio de artículo
        Notificacion.objects.create(
            oid_usuario=None,
            titulo="Modificación en artículo: Código Civil Art. 100",
            mensaje="Se ha actualizado el contenido del artículo 100.",
            tipo="articulo",
            leida=False
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('notificacion-list')

        response = self.client.get(url, {'tipo': 'articulo'})

        assert response.status_code == status.HTTP_200_OK
        resultados = response.json().get('results', response.json())
        assert len(resultados) >= 1
        assert resultados[0]['tipo'] == 'articulo'

    # TC-23: Boundary Value Analysis / Security - Intento de actualización sin autenticación rebotado
    def test_unauthenticated_user_cannot_update_article(self):
        url = reverse('codigo-legal-detail', args=[self.articulo.oid_codigo])
        payload = {"texto_contenido": "Intento de modificación maliciosa"}

        response = self.client.patch(url, payload, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Notificacion.objects.filter(tipo='articulo').count() == 0

    # TC-24: White-Box Path Testing - Verificación de no duplicidad excesiva en notificaciones
    def test_partial_update_article_triggers_notification_with_updated_metadata(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('codigo-legal-detail', args=[self.articulo.oid_codigo])

        payload = {"texto_contenido": "Actualización parcial de contenido"}
        response = self.client.patch(url, payload, format='json')

        assert response.status_code == status.HTTP_200_OK
        
        # Verificar estado del artículo actualizado
        self.articulo.refresh_from_db()
        assert self.articulo.texto_contenido == "Actualización parcial de contenido"
        
        # Verificar notificación generada
        notif = Notificacion.objects.filter(tipo='articulo').last()
        assert notif is not None
        assert "144" in notif.titulo

    def test_receive_notifications_of_changes_in_article_triggers_alert(self):
        """
        HU-05: Be able to receive notifications of changes in an article
        TC-31: Valida que la actualización de un artículo genere automáticamente 
               un registro de notificación en el sistema.
        """
        from client.models import Notificacion, CodigoLegal

        # 1. Crear el artículo inicial
        articulo = CodigoLegal.objects.create(
            nombre_norma="Código de Comercio",
            numero_articulo="Art. 10",
            texto_contenido="Texto inicial...",
            vigencia=True
        )

        # Autenticar usando el usuario configurado en el setup_method de la clase
        usuario = getattr(self, 'lawyer_1', getattr(self, 'user', getattr(self, 'admin', None)))
        if usuario:
            self.client.force_authenticate(user=usuario)

        # 2. URL de actualización del código legal (existe en tu router/views)
        url = reverse('codigo-legal-detail', args=[articulo.oid_codigo])
        payload = {
            "nombre_norma": "Código de Comercio",
            "numero_articulo": "Art. 10",
            "texto_contenido": "Texto modificado y actualizado.",
            "vigencia": True
        }

        conteo_inicial = Notificacion.objects.count()

        # 3. Modificar el artículo mediante PUT
        response = self.client.put(url, payload, format='json')

        # 4. Validar que la respuesta sea 200 OK y que se haya creado la notificación en BD
        assert response.status_code == status.HTTP_200_OK
        assert Notificacion.objects.count() > conteo_inicial