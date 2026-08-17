import pytest
from django.urls import reverse  # noqa:F401
from rest_framework import status
from rest_framework.test import APIClient

from client.models import Notificacion, Pago, Plan, Rol, Usuario

pytestmark = pytest.mark.django_db


class TestSubscriptionPlanChangeHU8:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()

        self.admin_role = Rol.objects.create(
            nombre="Administrador", descripcion="Administrador del sistema"
        )
        self.user_role = Rol.objects.create(
            nombre="Profesional", descripcion="Usuario profesional"
        )

        self.admin = Usuario.objects.create_user(
            email="admin@legalfile.com",
            password="adminpass123",
            nombre="Admin Test",
            oid_rol=self.admin_role,
            is_staff=True,
            is_superuser=True,
        )
        self.user = Usuario.objects.create_user(
            email="usuario@legalfile.com",
            password="userpass123",
            nombre="Usuario Test",
            oid_rol=self.user_role,
        )

        self.plan_actual = Plan.objects.create(
            nombre="Básico",
            precio_mensual=39.99,
            precio_anual=399.99,
            descripcion="Plan base",
            estado=True,
        )
        self.plan_nuevo = Plan.objects.create(
            nombre="Premium",
            precio_mensual=89.99,
            precio_anual=899.99,
            descripcion="Plan premium",
            estado=True,
        )
        self.pago = Pago.objects.create(
            oid_usuario=self.user,
            oid_plan=self.plan_nuevo,
            monto=89.99,
            metodo_pago="Tarjeta de crédito",
            estado_pago="Pendiente",
            referencia_externa="REF-PLAN-001",
        )

    def test_hu8_admin_approves_subscription_plan_and_returns_expected_message(self):  # noqa:E501
        self.client.force_authenticate(user=self.admin)

        url = f"/api/pagos/{self.pago.pk}/aprobar/"
        response = self.client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "message": "Plan aprobado exitosamente y usuario notificado."
        }

        self.pago.refresh_from_db()
        assert self.pago.estado_pago == "Completado"
        assert Notificacion.objects.filter(
            oid_usuario=self.user,
            titulo="¡Cambio de Plan Aprobado!",
            mensaje__icontains="ha sido aprobada exitosamente",
        ).exists()
