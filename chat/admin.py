from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    Conversation,
    ConversationInvitation,
    ConversationParticipant,
    Message,
    MessageStatus,
)


class ConversationParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0
    fields = [
        "user",
        "employee",
        "role",
        "joined_at",
        "last_read_at",
        "is_muted",
        "is_active",
    ]
    readonly_fields = ["joined_at"]
    raw_id_fields = ["user", "employee"]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = [
        "sender",
        "content_preview",
        "message_type",
        "created_at",
        "is_edited",
        "is_deleted",
    ]
    readonly_fields = ["content_preview", "created_at"]
    raw_id_fields = ["sender", "sender_employee"]

    def content_preview(self, obj):
        if obj.content:
            preview = (
                obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
            )
            return preview
        return "-"

    content_preview.short_description = "Content Preview"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title_display",
        "conversation_type",
        "business_link",
        "participants_count",
        "messages_count",
        "created_by_link",
        "last_message_at",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "conversation_type",
        "is_active",
        "business",
        "created_at",
        "last_message_at",
    ]
    search_fields = [
        "title",
        "business__name",
        "created_by__first_name",
        "created_by__last_name",
    ]
    ordering = ["-last_message_at", "-created_at"]
    readonly_fields = ["id", "last_message_at", "created_at", "updated_at"]
    raw_id_fields = ["business", "created_by"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "title",
                    "conversation_type",
                    "business",
                    "created_by",
                    "is_active",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("last_message_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [ConversationParticipantInline, MessageInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("business", "created_by")
            .annotate(
                participants_count=Count("participants", distinct=True),
                messages_count=Count("messages", distinct=True),
            )
        )

    def title_display(self, obj):
        if obj.title:
            return obj.title
        return f"{obj.get_conversation_type_display()} (No Title)"

    title_display.short_description = "Title"

    def business_link(self, obj):
        if obj.business:
            url = reverse("admin:business_business_change", args=[obj.business.id])
            return format_html('<a href="{}">{}</a>', url, obj.business.name)
        return "-"

    business_link.short_description = "Business"

    def created_by_link(self, obj):
        if obj.created_by:
            url = reverse("admin:accounts_user_change", args=[obj.created_by.id])
            name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
            return format_html('<a href="{}">{}</a>', url, name or obj.created_by.email)
        return "-"

    created_by_link.short_description = "Created By"

    def participants_count(self, obj):
        return obj.participants_count

    participants_count.short_description = "Participants"
    participants_count.admin_order_field = "participants_count"

    def messages_count(self, obj):
        return obj.messages_count

    messages_count.short_description = "Messages"
    messages_count.admin_order_field = "messages_count"


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "conversation_link",
        "user_link",
        "employee_link",
        "role",
        "business_name",
        "joined_at",
        "last_read_status",
        "is_muted",
        "is_active",
    ]
    list_filter = [
        "role",
        "is_muted",
        "is_active",
        "joined_at",
        "conversation__business",
        "conversation__conversation_type",
    ]
    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__email",
        "conversation__title",
        "employee__business__name",
    ]
    ordering = ["-joined_at"]
    readonly_fields = ["id", "joined_at", "created_at", "updated_at"]
    raw_id_fields = ["conversation", "user", "employee"]

    fieldsets = (
        (None, {"fields": ("id", "conversation", "user", "employee", "role")}),
        (
            "Activity",
            {"fields": ("joined_at", "last_read_at", "is_muted", "is_active")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "conversation", "user", "employee", "conversation__business"
            )
        )

    def conversation_link(self, obj):
        url = reverse("admin:chat_conversation_change", args=[obj.conversation.id])
        title = (
            obj.conversation.title
            or f"{obj.conversation.get_conversation_type_display()}"
        )
        return format_html('<a href="{}">{}</a>', url, title)

    conversation_link.short_description = "Conversation"

    def user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=[obj.user.id])
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return format_html('<a href="{}">{}</a>', url, name or obj.user.email)

    user_link.short_description = "User"

    def employee_link(self, obj):
        if obj.employee:
            url = reverse("admin:business_employee_change", args=[obj.employee.id])
            return format_html('<a href="{}">{}</a>', url, str(obj.employee))
        return "-"

    employee_link.short_description = "Employee"

    def business_name(self, obj):
        return obj.conversation.business.name if obj.conversation.business else "-"

    business_name.short_description = "Business"

    def last_read_status(self, obj):
        if obj.last_read_at:
            time_diff = timezone.now() - obj.last_read_at
            if time_diff.days > 0:
                return format_html(
                    '<span style="color: orange;">{} days ago</span>', time_diff.days
                )
            elif time_diff.seconds > 3600:
                return format_html(
                    '<span style="color: blue;">{} hours ago</span>',
                    time_diff.seconds // 3600,
                )
            else:
                return format_html('<span style="color: green;">Recently</span>')
        return format_html('<span style="color: red;">Never</span>')

    last_read_status.short_description = "Last Read"


class MessageStatusInline(admin.TabularInline):
    model = MessageStatus
    extra = 0
    fields = ["participant", "status", "status_changed_at"]
    readonly_fields = ["status_changed_at"]
    raw_id_fields = ["participant"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "conversation_link",
        "sender_link",
        "content_preview",
        "message_type",
        "reply_status",
        "status_indicators",
        "created_at",
        "is_edited",
        "is_deleted",
    ]
    list_filter = [
        "message_type",
        "is_edited",
        "is_deleted",
        "created_at",
        "conversation__business",
        "conversation__conversation_type",
    ]
    search_fields = [
        "content",
        "sender__first_name",
        "sender__last_name",
        "conversation__title",
        "conversation__business__name",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at", "edited_at", "deleted_at"]
    raw_id_fields = [
        "conversation",
        "sender",
        "sender_employee",
        "reply_to",
        "attachment",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "conversation",
                    "sender",
                    "sender_employee",
                    "content",
                    "message_type",
                )
            },
        ),
        (
            "Attachments & Replies",
            {"fields": ("attachment", "reply_to"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("is_edited", "edited_at", "is_deleted", "deleted_at")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [MessageStatusInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("conversation", "sender", "sender_employee", "reply_to")
            .prefetch_related("replies")
        )

    def conversation_link(self, obj):
        url = reverse("admin:chat_conversation_change", args=[obj.conversation.id])
        title = (
            obj.conversation.title
            or f"{obj.conversation.get_conversation_type_display()}"
        )
        return format_html('<a href="{}">{}</a>', url, title)

    conversation_link.short_description = "Conversation"

    def sender_link(self, obj):
        url = reverse("admin:accounts_user_change", args=[obj.sender.id])
        name = f"{obj.sender.first_name} {obj.sender.last_name}".strip()
        return format_html('<a href="{}">{}</a>', url, name or obj.sender.email)

    sender_link.short_description = "Sender"

    def content_preview(self, obj):
        if obj.is_deleted:
            return format_html('<em style="color: red;">Message deleted</em>')
        preview = obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
        return preview

    content_preview.short_description = "Content"

    def reply_status(self, obj):
        if obj.reply_to:
            return format_html('<span style="color: blue;">↳ Reply to message</span>')
        replies_count = obj.replies.count()
        if replies_count > 0:
            return format_html(
                '<span style="color: green;">{} replies</span>', replies_count
            )
        return "-"

    reply_status.short_description = "Reply Status"

    def status_indicators(self, obj):
        indicators = []
        if obj.is_edited:
            indicators.append('<span style="color: orange;">✏️ Edited</span>')
        if obj.is_deleted:
            indicators.append('<span style="color: red;">🗑️ Deleted</span>')
        if obj.attachment:
            indicators.append('<span style="color: blue;">📎 Attachment</span>')
        return format_html(" ".join(indicators)) if indicators else "-"

    status_indicators.short_description = "Status"


@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "message_link",
        "participant_link",
        "status",
        "business_name",
        "status_changed_at",
    ]
    list_filter = ["status", "status_changed_at", "participant__conversation__business"]
    search_fields = [
        "message__content",
        "participant__user__first_name",
        "participant__user__last_name",
        "participant__conversation__title",
    ]
    ordering = ["-status_changed_at"]
    readonly_fields = ["id", "status_changed_at", "created_at", "updated_at"]
    raw_id_fields = ["message", "participant"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "message",
                "participant",
                "participant__user",
                "participant__conversation",
                "participant__conversation__business",
            )
        )

    def message_link(self, obj):
        url = reverse("admin:chat_message_change", args=[obj.message.id])
        preview = (
            obj.message.content[:50] + "..."
            if len(obj.message.content) > 50
            else obj.message.content
        )
        return format_html('<a href="{}">{}</a>', url, preview)

    message_link.short_description = "Message"

    def participant_link(self, obj):
        url = reverse(
            "admin:chat_conversationparticipant_change", args=[obj.participant.id]
        )
        name = f"{obj.participant.user.first_name} {obj.participant.user.last_name}".strip()
        return format_html(
            '<a href="{}">{}</a>', url, name or obj.participant.user.email
        )

    participant_link.short_description = "Participant"

    def business_name(self, obj):
        return obj.participant.conversation.business.name

    business_name.short_description = "Business"


@admin.register(ConversationInvitation)
class ConversationInvitationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "conversation_link",
        "invited_by_link",
        "invited_user_link",
        "status",
        "business_name",
        "created_at",
        "responded_at",
    ]
    list_filter = ["status", "created_at", "responded_at", "conversation__business"]
    search_fields = [
        "invited_user__first_name",
        "invited_user__last_name",
        "invited_by__first_name",
        "invited_by__last_name",
        "conversation__title",
        "message",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["id", "responded_at", "created_at", "updated_at"]
    raw_id_fields = ["conversation", "invited_by", "invited_user", "invited_employee"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "conversation",
                    "invited_by",
                    "invited_user",
                    "invited_employee",
                )
            },
        ),
        ("Invitation Details", {"fields": ("status", "message", "expires_at")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "responded_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "conversation",
                "invited_by",
                "invited_user",
                "invited_employee",
                "conversation__business",
            )
        )

    def conversation_link(self, obj):
        url = reverse("admin:chat_conversation_change", args=[obj.conversation.id])
        title = (
            obj.conversation.title
            or f"{obj.conversation.get_conversation_type_display()}"
        )
        return format_html('<a href="{}">{}</a>', url, title)

    conversation_link.short_description = "Conversation"

    def invited_by_link(self, obj):
        url = reverse("admin:accounts_user_change", args=[obj.invited_by.id])
        name = f"{obj.invited_by.first_name} {obj.invited_by.last_name}".strip()
        return format_html('<a href="{}">{}</a>', url, name or obj.invited_by.email)

    invited_by_link.short_description = "Invited By"

    def invited_user_link(self, obj):
        url = reverse("admin:accounts_user_change", args=[obj.invited_user.id])
        name = f"{obj.invited_user.first_name} {obj.invited_user.last_name}".strip()
        return format_html('<a href="{}">{}</a>', url, name or obj.invited_user.email)

    invited_user_link.short_description = "Invited User"

    def business_name(self, obj):
        return obj.conversation.business.name

    business_name.short_description = "Business"


# Enhanced admin site customization
admin.site.site_header = "Bita Platform Chat Administration"
admin.site.site_title = "Chat Admin"
admin.site.index_title = "Chat Management"
