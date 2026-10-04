from rest_framework import serializers

from .models import FCMToken, Notification


class FCMTokenSerializer(serializers.ModelSerializer):
    """Sérialiseur pour token FCM."""

    class Meta:
        model = FCMToken
        fields = [
            "id",
            "token",
            "device_id",
            "platform",
            "actif",
            "date_creation",
            "date_derniere_utilisation",
        ]
        read_only_fields = ["id", "date_creation", "date_derniere_utilisation"]


class FCMTokenEnregistrerSerializer(serializers.Serializer):
    """Sérialiseur pour l'enregistrement d'un token FCM."""

    token = serializers.CharField(max_length=500)
    device_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    platform = serializers.ChoiceField(
        choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")],
        default="android",
    )


class NotificationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour lecture d'une notification."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "type_notification",
            "titre",
            "corps",
            "data",
            "statut_envoi",
            "date_envoi",
            "date_creation",
            "lue",
            "date_lecture",
        ]
        read_only_fields = fields


class NotificationCreerSerializer(serializers.Serializer):
    """Sérialiseur pour créer/envoyer une notification (admin ou système)."""

    utilisateur_id = serializers.IntegerField()
    type_notification = serializers.ChoiceField(
        choices=Notification.TypeNotification.choices,
        default=Notification.TypeNotification.GENERIQUE,
    )
    titre = serializers.CharField(max_length=200)
    corps = serializers.CharField()
    data = serializers.JSONField(default=dict, required=False)