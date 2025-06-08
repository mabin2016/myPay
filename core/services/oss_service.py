import logging
import os
import shutil
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
# from core.models import OssFile # Manage model interactions carefully

logger = logging.getLogger(__name__)

class OssService:
    """
    Mock implementation of an Object Storage Service (OSS).
    Simulates file operations by saving to a local directory.
    """

    def __init__(self, local_base_path=None, base_url=None):
        # Use Django's MEDIA_ROOT and MEDIA_URL if available and local_base_path is not set
        if local_base_path:
            self.local_base_path = local_base_path
        elif hasattr(settings, 'MEDIA_ROOT'):
            self.local_base_path = settings.MEDIA_ROOT / 'oss_mock'
        else:
            self.local_base_path = settings.BASE_DIR / 'media' / 'oss_mock'

        if base_url:
            self.base_url = base_url.rstrip('/')
        elif hasattr(settings, 'MEDIA_URL'):
            self.base_url = settings.MEDIA_URL.rstrip('/') + '/oss_mock'
        else:
            self.base_url = '/media/oss_mock'

        os.makedirs(self.local_base_path, exist_ok=True)
        logger.info(f"MockOssService initialized. Base path: {self.local_base_path}, Base URL: {self.base_url}")

    def _generate_unique_filename(self, filename):
        # Add a timestamp or UUID to make filename unique if needed
        name, ext = os.path.splitext(filename)
        # For mock, simple timestamp is enough. Real OSS handles this.
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
        return f"{name}_{timestamp}{ext}"

    def upload_file(self, file_obj, filename, destination_path='', uploaded_by_user=None):
        """
        Simulates uploading a file.
        :param file_obj: The file object to upload (e.g., from request.FILES).
        :param filename: The desired name for the file in storage.
        :param destination_path: Optional sub-path within the OSS mock base.
        :param uploaded_by_user: Optional user instance who uploaded the file.
        :return: URL of the "uploaded" file or None on failure.
        """
        if not file_obj or not filename:
            logger.error("OSS Service: File object or filename missing.")
            return None

        unique_filename = self._generate_unique_filename(filename)
        full_destination_dir = os.path.join(self.local_base_path, destination_path.strip('/'))
        os.makedirs(full_destination_dir, exist_ok=True)

        file_path = os.path.join(full_destination_dir, unique_filename)

        try:
            # Use Django's default_storage for consistent file handling if possible,
            # though here we are writing directly to simulate a separate OSS.
            with open(file_path, 'wb+') as destination_file:
                if hasattr(file_obj, 'chunks'):
                    for chunk in file_obj.chunks():
                        destination_file.write(chunk)
                else: # In-memory file or other file-like objects
                    destination_file.write(file_obj.read())

            file_url = f"{self.base_url}/{destination_path.strip('/')}/{unique_filename}".replace('//', '/')
            file_url = file_url.replace(':/', '://') # ensure http:// or https:// is not mangled

            logger.info(f"Mock file uploaded: {file_path}, URL: {file_url}")

            # Example of creating an OssFile record (consider doing this in the calling code/view)
            # from core.models import OssFile
            # try:
            #     oss_record = OssFile.objects.create(
            #         file_name=unique_filename,
            #         file_url=file_url,
            #         file_type=file_obj.content_type if hasattr(file_obj, 'content_type') else 'application/octet-stream',
            #         uploaded_by=uploaded_by_user
            #     )
            #     logger.info(f"OssFile record created with ID: {oss_record.id}")
            # except Exception as e:
            #     logger.error(f"Failed to create OssFile record for {unique_filename}: {e}")

            return file_url
        except Exception as e:
            logger.error(f"Mock OSS upload failed for {filename}: {e}", exc_info=True)
            return None

    def download_file(self, file_path_or_url):
        """
        Simulates downloading a file. In this mock, it just returns the local path.
        A real OSS would provide a stream or temporary URL.
        :param file_path_or_url: The path or URL of the file in OSS.
        :return: Local file path or None if not found.
        """
        # Convert URL to local path for mock
        if file_path_or_url.startswith(self.base_url):
            relative_path = file_path_or_url[len(self.base_url):].lstrip('/')
            local_file_path = os.path.join(self.local_base_path, relative_path)
        else: # Assume it's a relative path already
            local_file_path = os.path.join(self.local_base_path, file_path_or_url.lstrip('/'))

        if os.path.exists(local_file_path) and os.path.isfile(local_file_path):
            logger.info(f"Mock file found for download: {local_file_path}")
            return local_file_path # Or return ContentFile(open(local_file_path, 'rb').read(), name=os.path.basename(local_file_path))
        else:
            logger.error(f"Mock OSS file not found for download: {local_file_path}")
            return None

    def delete_file(self, file_path_or_url):
        """
        Simulates deleting a file.
        :param file_path_or_url: The path or URL of the file in OSS.
        :return: True on success, False on failure.
        """
        if file_path_or_url.startswith(self.base_url):
            relative_path = file_path_or_url[len(self.base_url):].lstrip('/')
            local_file_path = os.path.join(self.local_base_path, relative_path)
        else:
            local_file_path = os.path.join(self.local_base_path, file_path_or_url.lstrip('/'))

        try:
            if os.path.exists(local_file_path) and os.path.isfile(local_file_path):
                os.remove(local_file_path)
                logger.info(f"Mock file deleted: {local_file_path}")

                # Example of deleting OssFile record (consider doing this in calling code)
                # from core.models import OssFile
                # try:
                #     OssFile.objects.filter(file_url=file_path_or_url).delete() # Or match by relative path
                #     logger.info(f"OssFile record for {file_path_or_url} deleted.")
                # except Exception as e:
                #     logger.error(f"Failed to delete OssFile record for {file_path_or_url}: {e}")
                return True
            else:
                logger.warning(f"Mock OSS file not found for deletion: {local_file_path}")
                return False
        except Exception as e:
            logger.error(f"Mock OSS delete failed for {local_file_path}: {e}", exc_info=True)
            return False

    def get_file_url(self, file_path_in_storage):
        """
        Constructs the full URL for a file path within the mock storage.
        :param file_path_in_storage: Relative path to the file within the storage.
        :return: Full URL.
        """
        return f"{self.base_url}/{file_path_in_storage.lstrip('/')}"
