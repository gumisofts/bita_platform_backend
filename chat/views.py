from django.db.models import Count, F, Max, Prefetch, Q
from django.shortcuts import render
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet

from business.models import Employee

from .models import (
    Conversation,
    ConversationInvitation,
    ConversationParticipant,
    Message,
    MessageStatus,
)
from .serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationInvitationSerializer,
    ConversationListSerializer,
    ConversationParticipantSerializer,
    MarkAsReadSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)


class ConversationViewSet(ModelViewSet):
    """
    ViewSet for managing conversations between business employees
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Only return conversations where user is a participant
        return (
            Conversation.objects.filter(
                participants__user=user, participants__is_active=True, is_active=True
            )
            .select_related("business", "created_by")
            .prefetch_related("participants__user", "participants__employee")
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(
                        messages__created_at__gt=F("participants__last_read_at"),
                        messages__is_deleted=False,
                        participants__user=user,
                    ),
                )
            )
            .order_by("-last_message_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ConversationCreateSerializer
        elif self.action == "list":
            return ConversationListSerializer
        else:
            return ConversationDetailSerializer

    @extend_schema(
        summary="List user's conversations",
        description="Get all conversations where the authenticated user is a participant",
        parameters=[
            OpenApiParameter(
                name="business_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Filter conversations by business",
            ),
            OpenApiParameter(
                name="conversation_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by conversation type (direct, group, business_wide)",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Filter by business if provided
        business_id = request.query_params.get("business_id")
        if business_id:
            queryset = queryset.filter(business_id=business_id)

        # Filter by conversation type if provided
        conversation_type = request.query_params.get("conversation_type")
        if conversation_type:
            queryset = queryset.filter(conversation_type=conversation_type)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create a new conversation",
        description="Create a new conversation with specified participants",
        examples=[
            OpenApiExample(
                "Direct Message",
                value={
                    "title": "",
                    "conversation_type": "direct",
                    "business": "uuid-here",
                    "participant_user_ids": ["uuid1", "uuid2"],
                },
            ),
            OpenApiExample(
                "Group Chat",
                value={
                    "title": "Project Team Discussion",
                    "conversation_type": "group",
                    "business": "uuid-here",
                    "participant_user_ids": ["uuid1", "uuid2", "uuid3"],
                },
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        # Verify user is employee of the business
        business_id = request.data.get("business")
        if business_id:
            try:
                Employee.objects.get(user=request.user, business_id=business_id)
            except Employee.DoesNotExist:
                return Response(
                    {"detail": "You are not an employee of this business"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Add participants to conversation",
        description="Add new participants to an existing conversation",
    )
    @action(detail=True, methods=["post"])
    def add_participants(self, request, pk=None):
        conversation = self.get_object()
        user_ids = request.data.get("user_ids", [])

        if not user_ids:
            return Response(
                {"error": "user_ids is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has permission to add participants
        participant = conversation.participants.filter(
            user=request.user, is_active=True
        ).first()

        if not participant or participant.role not in ["admin", "owner"]:
            return Response(
                {"error": "You don't have permission to add participants"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate that users are employees of the business
        employees = Employee.objects.filter(
            user_id__in=user_ids, business=conversation.business
        )

        if employees.count() != len(user_ids):
            return Response(
                {"error": "Some users are not employees of this business"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add participants
        new_participants = []
        for employee in employees:
            if not conversation.participants.filter(user=employee.user).exists():
                new_participants.append(
                    ConversationParticipant(
                        conversation=conversation,
                        user=employee.user,
                        employee=employee,
                        role="member",
                    )
                )

        ConversationParticipant.objects.bulk_create(new_participants)

        return Response({"message": f"Added {len(new_participants)} participants"})

    @extend_schema(
        summary="Leave conversation",
        description="Remove current user from the conversation",
    )
    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        conversation = self.get_object()
        participant = conversation.participants.filter(
            user=request.user, is_active=True
        ).first()

        if not participant:
            return Response(
                {"error": "You are not a participant in this conversation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        participant.is_active = False
        participant.save()

        return Response({"message": "Left conversation successfully"})

    @extend_schema(
        summary="Mark conversation as read",
        description="Mark all messages in conversation as read",
    )
    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        conversation = self.get_object()
        participant = conversation.participants.filter(
            user=request.user, is_active=True
        ).first()

        if not participant:
            return Response(
                {"error": "You are not a participant in this conversation"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MarkAsReadSerializer(data=request.data)
        if serializer.is_valid():
            participant.last_read_at = timezone.now()
            participant.save()

            # Update message statuses
            if serializer.validated_data.get("mark_all"):
                MessageStatus.objects.filter(
                    participant=participant, status__in=["sent", "delivered"]
                ).update(status="read", status_changed_at=timezone.now())
            elif serializer.validated_data.get("message_ids"):
                MessageStatus.objects.filter(
                    participant=participant,
                    message_id__in=serializer.validated_data["message_ids"],
                    status__in=["sent", "delivered"],
                ).update(status="read", status_changed_at=timezone.now())

            return Response({"message": "Messages marked as read"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageViewSet(
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet
):
    """
    ViewSet for managing messages within conversations
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        conversation_id = self.request.query_params.get("conversation_id")

        queryset = (
            Message.objects.filter(
                is_deleted=False,
                conversation__participants__user=user,
                conversation__participants__is_active=True,
            )
            .select_related("sender", "sender_employee", "conversation", "reply_to")
            .prefetch_related("statuses__participant__user")
            .order_by("-created_at")
        )

        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    @extend_schema(
        summary="List messages",
        description="Get messages for conversations where user is a participant",
        parameters=[
            OpenApiParameter(
                name="conversation_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Filter messages by conversation",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Send a message",
        description="Send a new message in a conversation",
        examples=[
            OpenApiExample(
                "Text Message",
                value={
                    "conversation": "uuid-here",
                    "content": "Hello everyone!",
                    "message_type": "text",
                },
            ),
            OpenApiExample(
                "Reply to Message",
                value={
                    "conversation": "uuid-here",
                    "content": "Thanks for the update!",
                    "message_type": "text",
                    "reply_to": "message-uuid-here",
                },
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Edit message",
        description="Edit an existing message (only sender can edit)",
    )
    @action(detail=True, methods=["patch"])
    def edit(self, request, pk=None):
        message = self.get_object()

        if message.sender != request.user:
            return Response(
                {"error": "You can only edit your own messages"},
                status=status.HTTP_403_FORBIDDEN,
            )

        content = request.data.get("content")
        if not content:
            return Response(
                {"error": "content is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        message.content = content
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save()

        serializer = self.get_serializer(message)
        return Response(serializer.data)

    @extend_schema(
        summary="Delete message",
        description="Delete a message (only sender can delete)",
    )
    @action(detail=True, methods=["delete"])
    def delete_message(self, request, pk=None):
        message = self.get_object()

        if message.sender != request.user:
            return Response(
                {"error": "You can only delete your own messages"},
                status=status.HTTP_403_FORBIDDEN,
            )

        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save()

        return Response({"message": "Message deleted successfully"})


class ConversationParticipantViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for viewing conversation participants
    """

    serializer_class = ConversationParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        conversation_id = self.request.query_params.get("conversation_id")

        queryset = ConversationParticipant.objects.filter(
            conversation__participants__user=user,
            conversation__participants__is_active=True,
            is_active=True,
        ).select_related("user", "employee", "conversation")

        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        return queryset


class ConversationInvitationViewSet(ModelViewSet):
    """
    ViewSet for managing conversation invitations
    """

    serializer_class = ConversationInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            ConversationInvitation.objects.filter(
                Q(invited_user=user) | Q(invited_by=user)
            )
            .select_related(
                "conversation", "invited_by", "invited_user", "invited_employee"
            )
            .order_by("-created_at")
        )

    @extend_schema(
        summary="Accept invitation", description="Accept a conversation invitation"
    )
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        invitation = self.get_object()

        if invitation.invited_user != request.user:
            return Response(
                {"error": "You can only accept your own invitations"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != "pending":
            return Response(
                {"error": "This invitation is no longer pending"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add user as participant
        ConversationParticipant.objects.create(
            conversation=invitation.conversation,
            user=invitation.invited_user,
            employee=invitation.invited_employee,
            role="member",
        )

        invitation.status = "accepted"
        invitation.responded_at = timezone.now()
        invitation.save()

        return Response({"message": "Invitation accepted successfully"})

    @extend_schema(
        summary="Decline invitation", description="Decline a conversation invitation"
    )
    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        invitation = self.get_object()

        if invitation.invited_user != request.user:
            return Response(
                {"error": "You can only decline your own invitations"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != "pending":
            return Response(
                {"error": "This invitation is no longer pending"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation.status = "declined"
        invitation.responded_at = timezone.now()
        invitation.save()

        return Response({"message": "Invitation declined"})
