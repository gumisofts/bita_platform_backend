from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from .models import FileModel


class FileUploadDownloadTests(APITestCase):

    def setUp(self):
        """Set up the test with an image file."""
        self.upload_url = reverse("file-upload-list")  # Update this if needed
        # self.download_url_template = reverse('file-download', kwargs={'stored_as': 'test_stored_as'})  # Placeholder

        def generate_test_image():
            """Generate a simple in-memory image for testing"""
            image = Image.new("RGB", (100, 100), color=(255, 0, 0))
            image_io = BytesIO()
            image.save(image_io, format="JPEG")
            image_io.seek(0)
            return image_io

        self.sample_file = SimpleUploadedFile(
            "test_image.jpg", generate_test_image().read(), content_type="image/jpeg"
        )

    def test_upload_file(self):
        """Test that a file can be uploaded successfully."""
        data = {"file": self.sample_file, "alt_text": "Test Image Alt Text"}

        response = self.client.post(self.upload_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("stored_as", response.data)  # Ensure stored_as is in response

        # Check that the file was actually stored in the database
        stored_as = response.data["stored_as"]
        self.assertTrue(FileModel.objects.filter(stored_as=stored_as).exists())

    def test_download_file(self):
        """Test that an uploaded file can be retrieved successfully."""
        # Create a file instance in the DB
        file_instance = FileModel.objects.create(
            name="Test Image",
            stored_as="test_stored_as",
            file=self.sample_file,
            alt_text="Test Image Alt Text",
        )

        # Construct the download URL with the stored_as value
        download_url = reverse(
            "file-download", kwargs={"stored_as": file_instance.stored_as}
        )

        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "File retrieved successfully")
        self.assertIn("file_url", response.data)  # Ensure file URL is returned

    def test_download_non_existing_file(self):
        """Test that trying to retrieve a non-existing file returns a 404 error."""
        download_url = reverse(
            "file-download", kwargs={"stored_as": "non_existing_file"}
        )

        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
