from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.serializers import UserSerializer
from business.models import Business, Employee
from business.serializers import EmployeeSerializer

from .models import (
    Conversation,
    ConversationInvitation,
    ConversationParticipant,
    Message,
    MessageStatus,
)

User = get_user_model()


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = [
            "id",
            "user",
            "employee",
            "role",
            "joined_at",
            "last_read_at",
            "is_muted",
            "is_active",
        ]
        read_only_fields = ["id", "joined_at"]


class MessageStatusSerializer(serializers.ModelSerializer):
    participant = ConversationParticipantSerializer(read_only=True)

    class Meta:
        model = MessageStatus
        fields = ["id", "participant", "status", "status_changed_at"]
        read_only_fields = ["id", "status_changed_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    sender_employee = EmployeeSerializer(read_only=True)
    statuses = MessageStatusSerializer(many=True, read_only=True)
    reply_to = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender",
            "sender_employee",
            "content",
            "message_type",
            "attachment",
            "reply_to",
            "replies_count",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "created_at",
            "updated_at",
            "statuses",
        ]
        read_only_fields = [
            "id",
            "sender",
            "sender_employee",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "created_at",
            "updated_at",
        ]

    def get_reply_to(self, obj):
        if obj.reply_to:
            return {
                "id": obj.reply_to.id,
                "content": (
                    obj.reply_to.content[:100] + "..."
                    if len(obj.reply_to.content) > 100
                    else obj.reply_to.content
                ),
                "sender": obj.reply_to.sender.first_name
                + " "
                + obj.reply_to.sender.last_name,
                "created_at": obj.reply_to.created_at,
            }
        return None

    def get_replies_count(self, obj):
        return obj.replies.filter(is_deleted=False).count()

    def validate(self, data):
        # Ensure user is part of the conversation
        conversation = data.get("conversation")
        request = self.context.get("request")

        if request and hasattr(request, "user"):
            user = request.user
            if not conversation.participants.filter(user=user, is_active=True).exists():
                raise serializers.ValidationError(
                    {"detail": "You are not a participant in this conversation."}
                )

        return data


class MessageCreateSerializer(serializers.ModelSerializer):
    """Specialized serializer for creating messages"""

    class Meta:
        model = Message
        fields = ["conversation", "content", "message_type", "attachment", "reply_to"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        # Get the user's employee record for the conversation's business
        conversation = validated_data["conversation"]
        try:
            employee = Employee.objects.get(
                user=user, business=conversation.business, role__isnull=False
            )
        except Employee.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "You are not an employee of this business."}
            )

        validated_data["sender"] = user
        validated_data["sender_employee"] = employee

        with transaction.atomic():
            message = super().create(validated_data)

            # Update conversation's last_message_at
            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=["last_message_at"])

            # Create message status for all participants
            participants = conversation.participants.filter(is_active=True)
            statuses = []
            for participant in participants:
                if participant.user != user:  # Don't create status for sender
                    statuses.append(
                        MessageStatus(
                            message=message, participant=participant, status="sent"
                        )
                    )
            MessageStatus.objects.bulk_create(statuses)

        return message


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for listing conversations with summary info"""

    participants_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "conversation_type",
            "business",
            "created_by",
            "is_active",
            "last_message_at",
            "created_at",
            "participants_count",
            "last_message",
            "unread_count",
        ]

    def get_participants_count(self, obj):
        return obj.participants.filter(is_active=True).count()

    def get_last_message(self, obj):
        last_message = (
            obj.messages.filter(is_deleted=False).order_by("-created_at").first()
        )
        if last_message:
            return {
                "id": last_message.id,
                "content": (
                    last_message.content[:100] + "..."
                    if len(last_message.content) > 100
                    else last_message.content
                ),
                "sender_name": last_message.sender.first_name
                + " "
                + last_message.sender.last_name,
                "message_type": last_message.message_type,
                "created_at": last_message.created_at,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
            participant = obj.participants.filter(user=user, is_active=True).first()
            if participant:
                if participant.last_read_at:
                    return (
                        obj.messages.filter(
                            created_at__gt=participant.last_read_at, is_deleted=False
                        )
                        .exclude(sender=user)
                        .count()
                    )
                else:
                    return (
                        obj.messages.filter(is_deleted=False)
                        .exclude(sender=user)
                        .count()
                    )
        return 0


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual conversation view"""

    participants = ConversationParticipantSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "title",
            "conversation_type",
            "business",
            "created_by",
            "created_by_name",
            "is_active",
            "last_message_at",
            "created_at",
            "updated_at",
            "participants",
            "messages",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.first_name + " " + obj.created_by.last_name
        return None

    def get_messages(self, obj):
        # Get recent messages (last 50) for the conversation
        messages = obj.messages.filter(is_deleted=False).order_by("-created_at")[:50]
        return MessageSerializer(messages, many=True, context=self.context).data


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new conversations"""

    participant_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        help_text="List of user IDs to add as participants",
    )

    class Meta:
        model = Conversation
        fields = ["title", "conversation_type", "business", "participant_user_ids"]

    def validate_participant_user_ids(self, value):
        if len(value) < 1:
            raise serializers.ValidationError(
                {"detail": ["At least one participant is required."]}
            )

        business = self.initial_data.get("business")
        if business:
            # Check if all users are employees of the business
            employee_users = Employee.objects.filter(
                business=business, user__id__in=value
            ).values_list("user_id", flat=True)

            invalid_users = set(value) - set(employee_users)
            if invalid_users:
                raise serializers.ValidationError(
                    {
                        "detail": f"Users {invalid_users} are not employees of this business."
                    }
                )

        return value

    def create(self, validated_data):
        participant_user_ids = validated_data.pop("participant_user_ids")
        request = self.context.get("request")
        user = request.user

        validated_data["created_by"] = user

        with transaction.atomic():
            conversation = super().create(validated_data)

            # Add creator as participant if not already included
            if user.id not in participant_user_ids:
                participant_user_ids.append(user.id)

            # Create participants
            participants = []
            for user_id in participant_user_ids:
                employee = Employee.objects.get(
                    user_id=user_id, business=conversation.business
                )
                # Creator gets admin role for group conversations
                role = (
                    "admin"
                    if (
                        user_id == user.id and conversation.conversation_type == "group"
                    )
                    else "member"
                )

                participants.append(
                    ConversationParticipant(
                        conversation=conversation,
                        user_id=user_id,
                        employee=employee,
                        role=role,
                    )
                )

            ConversationParticipant.objects.bulk_create(participants)

        return conversation


class ConversationInvitationSerializer(serializers.ModelSerializer):
    invited_by_name = serializers.SerializerMethodField()
    invited_user_name = serializers.SerializerMethodField()
    conversation_title = serializers.SerializerMethodField()

    class Meta:
        model = ConversationInvitation
        fields = [
            "id",
            "conversation",
            "conversation_title",
            "invited_by",
            "invited_by_name",
            "invited_user",
            "invited_user_name",
            "invited_employee",
            "status",
            "message",
            "expires_at",
            "responded_at",
            "created_at",
        ]
        read_only_fields = ["id", "responded_at", "created_at"]

    def get_invited_by_name(self, obj):
        return obj.invited_by.first_name + " " + obj.invited_by.last_name

    def get_invited_user_name(self, obj):
        return obj.invited_user.first_name + " " + obj.invited_user.last_name

    def get_conversation_title(self, obj):
        return (
            obj.conversation.title
            or f"{obj.conversation.get_conversation_type_display()}"
        )


class MarkAsReadSerializer(serializers.Serializer):
    """Serializer for marking messages as read"""

    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific message IDs to mark as read (optional)",
    )
    mark_all = serializers.BooleanField(
        default=False, help_text="Mark all messages in conversation as read"
    )

    def validate(self, data):
        if not data.get("mark_all") and not data.get("message_ids"):
            raise serializers.ValidationError(
                {"detail": "Either provide message_ids or set mark_all to true"}
            )
        return data
