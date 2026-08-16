import pytest
from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from client.models import (
    Rol,
    Usuario,
    CodigoLegal,
    Caso,
    EstadoCaso,
    TipoCaso,
    Documento,
)

pytestmark = pytest.mark.django_db


class TestHU16NavigableSideIndexService:
    """Pruebas automatizadas para HU-16: Mostrar un índice
    lateral navegable para códigos o documentos."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.client = APIClient()
        self.rol = Rol.objects.create(
            nombre="Profesional", descripcion="Usuario regular"
        )
        self.user = Usuario.objects.create_user(
            email="abogado_index@gmail.com",
            password="Password123",
            nombre="Abogado Index",
            oid_rol=self.rol,
        )

        self.estado = EstadoCaso.objects.create(nombre="Activo")
        self.tipo = TipoCaso.objects.create(nombre="Civil",
                                            descripcion="Casos Civiles")

        # Datos de prueba para Códigos Legales
        CodigoLegal.objects.create(
            nombre_norma="COIP",
            numero_articulo="144",
            texto_contenido="Homicidio",
            vigencia=True,
        )
        CodigoLegal.objects.create(
            nombre_norma="COIP",
            numero_articulo="145",
            texto_contenido="Homicidio culposo",
            vigencia=True,
        )
        CodigoLegal.objects.create(
            nombre_norma="Código Civil",
            numero_articulo="1",
            texto_contenido="La ley es...",
            vigencia=True,
        )

        # Código legal sin índices (para TC-30)
        self.articulo_sin_indices = CodigoLegal.objects.create(
            nombre_norma="Ley Especial",
            numero_articulo="999",
            texto_contenido="Artículo sin estructura",
            vigencia=True,
        )

        # Datos de prueba para Caso y Documentos
        self.caso = Caso.objects.create(
            titulo="Caso Herencia Civil",
            oid_abogado=self.user,
            oid_estado=self.estado,
            oid_tipo_caso=self.tipo,
            numero_expediente="EXP-CIV-2026",
            fecha_inicio=date(2026, 4, 1),
        )

        Documento.objects.create(
            oid_caso=self.caso,
            nombre_archivo="Escritura_Publica",
            tipo_documento="Evidencia",
            ruta_archivo=None,
        )

    # TC-25: Equivalence Partitioning / Happy Path -
    # Índice navegable de códigos legales por norma
    def test_get_legal_codes_navigable_index_returns_grouped_structure(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("codigo-legal-indice-navegable")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "indice" in data
        assert data["total_normas"] == len(data["indice"])
        assert data["total_normas"] >= 2

        # Verificar que la norma COIP contenga sus 2
        # artículos para el índice lateral
        coip_entry = next(
            (item for item in data["indice"] if item["norma"] == "COIP"), None
        )
        assert coip_entry is not None
        assert coip_entry["total_articulos"] == 2
        articulos_nums = [art["numero_articulo"] for art in coip_entry["articulos"]]  # noqa: E501
        assert "144" in articulos_nums
        assert "145" in articulos_nums

    # TC-26: Equivalence Partitioning / Happy Path -
    # Índice navegable de documentos agrupados por caso
    def test_get_documents_navigable_index_returns_case_tree(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("documento-indice-navegable")

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "indice_documentos" in data

        # Verificar que el documento de prueba
        # aparezca bajo su caso correspondiente
        keys = list(data["indice_documentos"].keys())
        assert len(keys) == 1
        assert "Caso Herencia Civil" in keys[0]
        assert (
            data["indice_documentos"][keys[0]][0]["nombre_archivo"]
            == "Escritura_Publica"
        )

    # TC-27: Boundary Value Analysis -
    # Manejo seguro de índice navegable sin registros en BD
    def test_navigable_index_empty_database_returns_clean_empty_structure(self):  # noqa: E501
        CodigoLegal.objects.all().delete()
        Documento.objects.all().delete()

        self.client.force_authenticate(user=self.user)

        url_codigos = reverse("codigo-legal-indice-navegable")
        res_codigos = self.client.get(url_codigos)
        assert res_codigos.status_code == status.HTTP_200_OK
        assert res_codigos.json()["total_normas"] == 0
        assert len(res_codigos.json()["indice"]) == 0

        url_docs = reverse("documento-indice-navegable")
        res_docs = self.client.get(url_docs)
        assert res_docs.status_code == status.HTTP_200_OK
        assert len(res_docs.json()["indice_documentos"]) == 0

    # TC-28: Security / Decision Table - Intento de
    # consultar índice lateral sin estar autenticado
    def test_unauthenticated_user_cannot_access_navigable_index(self):
        url_codigos = reverse("codigo-legal-indice-navegable")
        res_codigos = self.client.get(url_codigos)
        assert res_codigos.status_code == status.HTTP_401_UNAUTHORIZED

        url_docs = reverse("documento-indice-navegable")
        res_docs = self.client.get(url_docs)
        assert res_docs.status_code == status.HTTP_401_UNAUTHORIZED

    ##@pytest.mark.skip(reason="codigolegal-side-index endpoint not yet implemented in CodigoLegalViewSet")  # noqa:E501
    def test_get_side_index_document_without_structure_returns_empty_nodes(self):  # noqa: E501
        """
        HU-16: Show a navigable side index
        TC-30: Retorna lista de nodos vacía cuando
        el código legal no posee estructura jerárquica.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "codigo-legal-side-index",
            args=[self.articulo_sin_indices.oid_codigo]
        )

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        resultados = data.get("results", data) if isinstance(data, dict) else data  # noqa: E501
        assert len(resultados) == 0

    ###@pytest.mark.skip(reason="codigolegal-side-index endpoint not yet implemented in CodigoLegalViewSet")  # noqa: E501
    def test_get_side_index_invalid_document_returns_404(self):
        """
        HU-16: Show a navigable side index
        TC-38: Retorna 404 al solicitar el
        índice lateral de un código legal inexistente.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("codigo-legal-side-index", args=[99999])

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
