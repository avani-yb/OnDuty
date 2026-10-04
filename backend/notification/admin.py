from django.contrib import admin

from .models import FCMToken, Notification


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "utilisateur", "platform", "actif", "date_creation", "date_derniere_utilisation")
    list_filter = ("platform", "actif", "date_creation")
    search_fields = ("utilisateur__telephone", "token", "device_id")
    readonly_fields = ("date_creation", "date_derniere_utilisation")
    list_editable = ("actif",)
    date_hierarchy = "date_creation"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "utilisateur", "type_notification", "titre", "statut_envoi", "date_envoi", "date_creation")
    list_filter = ("type_notification", "statut_envoi", "date_creation")
    search_fields = ("utilisateur__telephone", "titre", "corps")
    readonly_fields = ("date_creation", "date_envoi", "fcm_message_id")
    list_editable = ("statut_envoi",)
    date_hierarchy = "date_creation"