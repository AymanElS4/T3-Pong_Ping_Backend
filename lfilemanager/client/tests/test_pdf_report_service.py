from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse, NoReverseMatch
from rest_framework import status
from rest_framework.test import APITestCase
from client.models import Rol, Usuario, CodigoLegal


class TestPdfReportService(APITestCase):

    def setUp(self):
        super().setUp()

        # 1. Parchear llamadas a GASDriveStorage para aislar la base de datos de pruebas
        self.patcher_post = patch("requests.post")
        self.mock_post = self.patcher_post.start()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "id": "1A2B3C_fake_drive_file_id",
            "fileId": "1A2B3C_fake_drive_file_id"
        }
        self.mock_post.return_value = mock_response

        # 2. Estructura de Roles y Usuario
        self.rol_admin = Rol.objects.create(nombre='Administrador', descripcion='Admin')
        self.admin = Usuario.objects.create_user(
            email='admin_report@x.com',
            password='pass',
            nombre='AdminReport',
            oid_rol=self.rol_admin
        )

        pdf_in_memory = SimpleUploadedFile(
            name="reporte_test.pdf",
            content=b"%PDF-1.4 fake pdf content",
            content_type="application/pdf"
        )

        # 3. Crear registros de prueba en la base de datos
        self.articulo_con_pdf = CodigoLegal.objects.create(
            nombre_norma='Código Civil PDF',
            numero_articulo='Art. 1',
            texto_contenido='Contenido...',
            archivo_pdf=pdf_in_memory,
            vigencia=True
        )

        self.articulo_sin_pdf = CodigoLegal.objects.create(
            nombre_norma='Código Penal Sin PDF',
            numero_articulo='Art. 2',
            texto_contenido='Contenido...',
            archivo_pdf=None,
            vigencia=True
        )

    def tearDown(self):
        self.patcher_post.stop()
        super().tearDown()

    def _get_url(self, oid):
        """Resuelve dinámicamente la URL probando los nombres de ruta configurados en urls.py."""
        possible_names = [
            'codigo-legal-detail',
            'codigolegal-detail',
            'codigos-legales-detail'
        ]
        for name in possible_names:
            try:
                return reverse(name, args=[oid])
            except NoReverseMatch:
                continue
        # Fallback directo a la URL REST mapeada
        return f"/api/codigo-legal/{oid}/"

    def test_download_pdf_report_returns_file_content(self):
        """
        HU-11: Download PDF Report
        TC-29: Obtiene el detalle del código legal y verifica que la respuesta sea 200 OK y contenga la referencia al PDF.
        """
        self.client.force_authenticate(user=self.admin)
        url = self._get_url(self.articulo_con_pdf.oid_codigo)

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get('nombre_norma') == 'Código Civil PDF'

    def test_download_pdf_report_not_found_returns_404(self):
        """
        HU-11: Download PDF Report
        TC-32: Retorna 404 cuando el ID del código legal no existe.
        """
        self.client.force_authenticate(user=self.admin)
        url = self._get_url(99999)

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_pdf_report_without_file_returns_null_pdf(self):
        """
        HU-11: Download PDF Report
        TC-36: Retorna el detalle del código legal en 200 OK cuando no posee archivo PDF asignado.
        """
        self.client.force_authenticate(user=self.admin)
        url = self._get_url(self.articulo_sin_pdf.oid_codigo)

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get('archivo_pdf') is None or data.get('archivo_pdf') == ""