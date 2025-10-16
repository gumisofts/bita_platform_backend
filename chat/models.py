from django.contrib.auth import get_user_model
from django.db import models

from core.models import BaseModel

User = get_user_model()


class ConversationType(models.TextChoices):
    DIRECT = "direct", "Direct Message"
    GROUP = "group", "Group Chat"
    BUSINESS = "business", "Business"


class ConversationParticipantRole(models.TextChoices):
    MEMBER = "member", "Member"
    ADMIN = "admin", "Admin"
    OWNER = "owner", "Owner"


# Group Chat
# Direct Message(employee-employee)
# External Message(customer-business)
#
class Conversation(BaseModel):
    """
    Represents a conversation between business participants
    """

    title = models.CharField(
        max_length=255, blank=True, help_text="Optional title for group conversations"
    )
    conversation_type = models.CharField(
        max_length=20, choices=ConversationType.choices, default=ConversationType.DIRECT
    )
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="conversations",
        help_text="Business context for the conversation",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_conversations"
    )
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_conversation"
        indexes = [
            models.Index(fields=["business", "conversation_type"]),
            models.Index(fields=["last_message_at"]),
        ]

    def __str__(self):
        if self.title:
            return f"{self.title} ({self.business.name})"
        participants = self.participants.count()
        return f"{self.get_conversation_type_display()} - {participants} participants"


class ConversationParticipant(BaseModel):
    """
    Links users to conversations with their participation detailsss
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversation_participations"
    )
    employee = models.ForeignKey(
        "business.Employee",
        on_delete=models.CASCADE,
        related_name="conversation_participations",
        help_text="Employee record for business context",
    )
    role = models.CharField(
        max_length=10,
        choices=ConversationParticipantRole.choices,
        default=ConversationParticipantRole.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "chat_conversation_participant"
        unique_together = ["conversation", "user"]
        indexes = [
            models.Index(fields=["conversation", "is_active"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.first_name} in {self.conversation}"


class Message(BaseModel):
    """
    Represents individual messages in conversations
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    sender_employee = models.ForeignKey(
        "business.Employee",
        on_delete=models.CASCADE,
        related_name="sent_messages",
        help_text="Employee record for sender",
    )
    content = models.TextField(help_text="Message content")
    message_type = models.CharField(
        max_length=20,
        choices=[
            ("text", "Text"),
            ("image", "Image"),
            ("file", "File"),
            ("system", "System Message"),
        ],
        default="text",
    )
    attachment = models.ForeignKey(
        "files.FileMeta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_messages",
    )
    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_message"
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return f"{self.sender.first_name}: {content_preview}"


class MessageStatus(BaseModel):
    """
    Tracks the delivery and read status of messages for each participant
    """

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="statuses"
    )
    participant = models.ForeignKey(
        ConversationParticipant,
        on_delete=models.CASCADE,
        related_name="message_statuses",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("read", "Read"),
        ],
        default="sent",
    )
    status_changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_message_status"
        unique_together = ["message", "participant"]
        indexes = [
            models.Index(fields=["message", "status"]),
            models.Index(fields=["participant", "status"]),
        ]

    def __str__(self):
        return f"{self.message} - {self.participant.user.first_name}: {self.status}"


class ConversationInvitation(BaseModel):
    """
    Handles invitations to join conversations
    """

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="invitations"
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_conversation_invitations"
    )
    invited_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_conversation_invitations"
    )
    invited_employee = models.ForeignKey(
        "business.Employee",
        on_delete=models.CASCADE,
        related_name="conversation_invitations",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("expired", "Expired"),
        ],
        default="pending",
    )
    message = models.TextField(blank=True, help_text="Optional invitation message")
    expires_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_conversation_invitation"
        unique_together = ["conversation", "invited_user"]
        indexes = [
            models.Index(fields=["invited_user", "status"]),
            models.Index(fields=["conversation", "status"]),
        ]

    def __str__(self):
        return f"Invitation to {self.conversation} for {self.invited_user.first_name}"
