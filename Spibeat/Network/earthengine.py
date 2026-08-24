import ee
from django.conf import settings
from google.oauth2 import service_account


def initialize_earth_engine():

    credentials = service_account.Credentials.from_service_account_file(
        settings.EE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/earthengine"]
    )

    ee.Initialize(credentials, project=settings.EE_PROJECT_ID)