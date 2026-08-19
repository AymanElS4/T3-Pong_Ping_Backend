import pytest
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from client.models import Rol, Usuario, Caso, EstadoCaso, TipoCaso

pytestmark = pytest.mark.django_db


class TestHU12CaseCustomization:
    """Tests for HU-12: Case Customization
      (categorization using case types)."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.client = APIClient()
        self.list_url = reverse("caso-list")

        # Set up a lawyer role and lawyer user
        self.rol = Rol.objects.create(
            nombre="Abogado", descripcion="Abogado firma"
        )
        self.lawyer = Usuario.objects.create_user(
            email="lawyer_hu12@x.com",
            password="password123",
            nombre="Abogado HU12",
            oid_rol=self.rol,
        )

        self.estado_open = EstadoCaso.objects.create(nombre="OPEN")

        # Create different custom case types
        #  (representing customization categories)
        self.tipo_civil = TipoCaso.objects.create(
            nombre="Civil", descripcion="Casos Civiles"
        )
        self.tipo_penal = TipoCaso.objects.create(
            nombre="Penal", descripcion="Casos Penales"
        )

    def test_hu12_filter_cases_by_case_type(self):
        """TC-HU12-01: Verifies that filtering by a specific case type

        returns only the corresponding cases.
        """
        self.client.force_authenticate(user=self.lawyer)

        # Create two cases with different custom case types
        Caso.objects.create(
            titulo="Caso de Herencia",
            oid_abogado=self.lawyer,
            oid_estado=self.estado_open,
            oid_tipo_caso=self.tipo_civil,
            numero_expediente="EXP-HU12-CIV",
            fecha_inicio=date(2026, 1, 1),
            descripcion="Expediente de litigio sucesorio familiar.",
        )
        Caso.objects.create(
            titulo="Caso de Hurto",
            oid_abogado=self.lawyer,
            oid_estado=self.estado_open,
            oid_tipo_caso=self.tipo_penal,
            numero_expediente="EXP-HU12-PEN",
            fecha_inicio=date(2026, 1, 2),
            descripcion="Expediente por delito de hurto agravado.",
        )

        # Filter for "Civil" case type
        response = self.client.get(
            self.list_url, {"oid_tipo_caso": self.tipo_civil.pk}
        )
        assert response.status_code == status.HTTP_200_OK

        resultados = response.json().get("results", response.json())
        assert len(resultados) == 1
        assert resultados[0]["titulo"] == "Caso de Herencia"

        # Filter for "Penal" case type
        response = self.client.get(
            self.list_url, {"oid_tipo_caso": self.tipo_penal.pk}
        )
        assert response.status_code == status.HTTP_200_OK

        resultados = response.json().get("results", response.json())
        assert len(resultados) == 1
        assert resultados[0]["titulo"] == "Caso de Hurto"

    def test_hu12_update_case_type_customization(self):
        """TC-HU12-02: Verifies that updating a case's custom type

        successfully changes the categorization.
        """
        self.client.force_authenticate(user=self.lawyer)

        # Create a case with Civil type
        case = Caso.objects.create(
            titulo="Caso de Disputa Sucesoria",
            oid_abogado=self.lawyer,
            oid_estado=self.estado_open,
            oid_tipo_caso=self.tipo_civil,
            numero_expediente="EXP-HU12-UPD",
            fecha_inicio=date(2026, 1, 3),
            descripcion="Disputa sobre partición de propiedad.",
        )

        # Confirm the case is currently classified under Civil type
        response = self.client.get(
            self.list_url, {"oid_tipo_caso": self.tipo_civil.pk}
        )
        assert response.status_code == status.HTTP_200_OK
        resultados = response.json().get("results", response.json())
        assert len(resultados) == 1

        # Perform a PATCH update to change case type to Penal
        detail_url = reverse("caso-detail", kwargs={"pk": case.pk})
        payload = {"oid_tipo_caso": self.tipo_penal.pk}
        patch_response = self.client.patch(detail_url, payload, format="json")
        assert patch_response.status_code == status.HTTP_200_OK

        # Verify it is no longer listed under Civil
        response = self.client.get(
            self.list_url, {"oid_tipo_caso": self.tipo_civil.pk}
        )
        assert response.status_code == status.HTTP_200_OK
        resultados = response.json().get("results", response.json())
        assert len(resultados) == 0

        # Verify it is now listed under Penal
        response = self.client.get(
            self.list_url, {"oid_tipo_caso": self.tipo_penal.pk}
        )
        assert response.status_code == status.HTTP_200_OK
        resultados = response.json().get("results", response.json())
        assert len(resultados) == 1
        assert resultados[0]["titulo"] == "Caso de Disputa Sucesoria"
