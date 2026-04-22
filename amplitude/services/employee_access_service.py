from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from amplitude.models import AllowedEmployeePageAccess, EmployeePortalPage
from utils.avatariya_client import AvatariyaClient


@dataclass(frozen=True)
class EmployeeProfile:
    iin: str
    full_name: str
    email: str
    position_guid: str
    position_name: str


class EmployeeAccessService:
    def __init__(self, avatariya_client: Optional[AvatariyaClient] = None) -> None:
        if avatariya_client is not None:
            self.avatariya_client = avatariya_client
            return

        try:
            self.avatariya_client = AvatariyaClient()
        except ValueError:
            self.avatariya_client = None

    def can_access_site(self, iin: str) -> bool:
        return self.get_employee_profile(iin) is not None

    def get_employee_profile(self, iin: str) -> Optional[EmployeeProfile]:
        normalized_iin = (iin or '').strip()
        if not normalized_iin:
            return None
        if self.avatariya_client is None:
            return None

        try:
            payload = self.avatariya_client.get_employee_by_iin(normalized_iin)
        except Exception:
            return None

        data = self._extract_employee_data(payload)
        if data is None:
            return None

        if data.get('active') is False:
            return None

        full_name = str(data.get('full_name') or data.get('name') or '').strip()
        email = str(data.get('email') or '').strip().lower()
        position_guid, position_name = self._extract_position(data)

        return EmployeeProfile(
            iin=str(data.get('iin') or normalized_iin).strip(),
            full_name=full_name,
            email=email,
            position_guid=position_guid,
            position_name=position_name,
        )

    def allowed_pages_for_iin(self, iin: str) -> List[str]:
        profile = self.get_employee_profile(iin)
        if profile is None:
            return []
        return self.allowed_pages_for_position(profile.position_guid)

    def allowed_pages_for_position(self, position_guid: str) -> List[str]:
        normalized = (position_guid or '').strip()
        if not normalized:
            return []

        allowed_set = set(
            AllowedEmployeePageAccess.objects.filter(position_guid=normalized, is_active=True)
            .values_list('page', flat=True)
        )
        if not allowed_set:
            return []

        ordered = [value for value, _ in EmployeePortalPage.choices if value in allowed_set]
        return ordered

    def can_access_page(self, iin: str, page: str) -> bool:
        return page in self.allowed_pages_for_iin(iin)

    def _extract_employee_data(self, payload: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None

        if payload.get('success') is False:
            return None

        if isinstance(payload.get('data'), dict):
            return payload['data']

        return payload

    def _extract_position(self, data: Dict[str, Any]) -> tuple[str, str]:
        raw = data.get('position')

        if isinstance(raw, dict):
            guid = str(raw.get('guid_1c') or raw.get('guid') or raw.get('id') or '').strip()
            name = str(raw.get('name') or data.get('position_name') or '').strip()
            return guid, name

        if raw is None:
            return '', ''

        guid = str(raw).strip()
        name = str(data.get('position_name') or '').strip()
        if name:
            return guid, name

        return guid, self._fetch_position_name(guid)

    def _fetch_position_name(self, position_guid: str) -> str:
        normalized = (position_guid or '').strip()
        if not normalized or self.avatariya_client is None:
            return ''

        try:
            payload = self.avatariya_client.get_position_by_guid(normalized)
        except Exception:
            return ''

        if not isinstance(payload, dict):
            return ''

        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        return str(data.get('name') or '').strip()
