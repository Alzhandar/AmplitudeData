import gzip
import json
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Iterator

import requests
from django.conf import settings


class AmplitudeExportClient:
    def __init__(self) -> None:
        self.url = settings.AMPLITUDE_EXPORT_URL
        self.api_key = settings.AMPLITUDE_API_KEY
        self.secret_key = settings.AMPLITUDE_SECRET_KEY
        self.timeout = settings.AMPLITUDE_TIMEOUT_SECONDS

    def fetch_events(self, start: datetime, end: datetime) -> Iterator[dict]:
        if not self.api_key or not self.secret_key:
            raise ValueError('AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY must be set')

        params = {
            'start': start.strftime('%Y%m%dT%H'),
            'end': end.strftime('%Y%m%dT%H'),
        }
        response = requests.get(
            self.url,
            params=params,
            auth=(self.api_key, self.secret_key),
            timeout=self.timeout,
        )
        response.raise_for_status()

        content = response.content

        if zipfile.is_zipfile(BytesIO(content)):
            with zipfile.ZipFile(BytesIO(content)) as archive:
                for filename in archive.namelist():
                    with archive.open(filename) as file_handle:
                        for line in file_handle:
                            line = line.decode('utf-8').strip()
                            if line:
                                yield json.loads(line)
            return

        if content[:2] == b'\x1f\x8b':
            content = gzip.decompress(content)

        for line in content.decode('utf-8').splitlines():
            line = line.strip()
            if line:
                yield json.loads(line)
