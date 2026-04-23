from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.permissions import HasPushDispatchAccess
from notifications.serializers import NotificationCitySerializer, PushDispatchRequestSerializer
from notifications.services.push_dispatch_service import PushDispatchService


class NotificationCityViewSet(viewsets.ViewSet):
	permission_classes = [IsAuthenticated, HasPushDispatchAccess]

	def list(self, request):
		search = str(request.query_params.get('search', '')).strip()
		service = PushDispatchService()
		cities = service.list_cities(search=search)
		serializer = NotificationCitySerializer(cities, many=True)
		return Response(serializer.data)


class PushDispatchViewSet(viewsets.ViewSet):
	permission_classes = [IsAuthenticated, HasPushDispatchAccess]

	def create(self, request):
		serializer = PushDispatchRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		service = PushDispatchService()
		result = service.send_mass_push(**serializer.validated_data)

		return Response(
			{
				'target': result.target,
				'city_id': result.city_id,
				'recipients_count': result.recipients_count,
				'notification_id': result.notification_id,
				'status': result.status,
			},
			status=201,
		)
