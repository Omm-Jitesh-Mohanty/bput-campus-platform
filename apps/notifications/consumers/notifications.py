# # """
# # Notification consumer — pushes new notifications to the logged-in user.
# # """
# # import logging

# # from .base import BaseUserConsumer
# # from .serializers import serialize_notification

# # logger = logging.getLogger(__name__)


# # class NotificationConsumer(BaseUserConsumer):
# #     """
# #     Streams notifications for the current user.
# #     Group: `user_<id>`
# #     """

# #     async def connect(self):
# #         await super().connect()
# #         # Send initial unread count
# #         count = await self.get_unread_count()
# #         await self.send_json({'type': 'unread_count', 'count': count})

# #     async def handle_mark_read(self, data):
# #         """Client asks us to mark a notification as read."""
# #         notification_id = data.get('notification_id')
# #         if notification_id:
# #             marked = await self.mark_notification_read(notification_id)
# #             if marked:
# #                 count = await self.get_unread_count()
# #                 await self.send_json({'type': 'unread_count', 'count': count})

# #     # -------- DB helpers (must be sync-to-async wrapped) --------

# #     @database_sync_to_async
# #     def get_unread_count(self):
# #         return self.user.notifications.filter(is_read=False).count()

# #     @database_sync_to_async
# #     def mark_notification_read(self, notification_id):
# #         try:
# #             n = self.user.notifications.get(id=notification_id)
# #             n.mark_read()
# #             return True
# #         except Exception:
# #             return False


# # # Import at bottom to avoid circular
# # from channels.db import database_sync_to_async  # noqa


# """
# Notification consumer — pushes new notifications to the logged-in user.
# """
# import logging

# from channels.db import database_sync_to_async

# from .base import BaseUserConsumer
# from .serializers import serialize_notification

# logger = logging.getLogger(__name__)


# class NotificationConsumer(BaseUserConsumer):
#     """
#     Streams notifications for the current user.
#     Group: `user_<id>`
#     """

#     async def connect(self):
#         await super().connect()

#         if not hasattr(self, 'user'):
#             return

#         count = await self.get_unread_count()

#         await self.send_json({
#             'type': 'unread_count',
#             'count': count,
#         })

#     async def handle_mark_read(self, data):
#         """Client asks us to mark a notification as read."""

#         notification_id = data.get('notification_id')

#         if notification_id:
#             marked = await self.mark_notification_read(
#                 notification_id
#             )

#             if marked:
#                 count = await self.get_unread_count()

#                 await self.send_json({
#                     'type': 'unread_count',
#                     'count': count,
#                 })

#     @database_sync_to_async
#     def get_unread_count(self):
#         return self.user.notifications.filter(
#             is_read=False
#         ).count()

#     @database_sync_to_async
#     def mark_notification_read(self, notification_id):
#         try:
#             notification = self.user.notifications.get(
#                 id=notification_id
#             )

#             notification.mark_read()

#             return True

#         except Exception as e:
#             logger.warning(
#                 f"Failed to mark notification {notification_id} "
#                 f"as read for user {self.user.id}: {e}"
#             )

#             return False

"""
Notification consumer — pushes new notifications to the logged-in user.
"""

import logging

from channels.db import database_sync_to_async

from .base import BaseUserConsumer


logger = logging.getLogger(__name__)


class NotificationConsumer(BaseUserConsumer):
    """
    Streams notifications for the current user.
    Group: user_<id>
    """

    async def connect(self):
        logger.info("NotificationConsumer.connect() started")

        try:
            await super().connect()

            logger.info(
                "NotificationConsumer.connect(): "
                "BaseUserConsumer.connect() completed"
            )

            if not hasattr(self, "user"):
                logger.warning(
                    "NotificationConsumer.connect(): "
                    "self.user was not set"
                )
                return

            logger.info(
                f"NotificationConsumer.connect(): "
                f"user={self.user.username}, "
                f"user_id={self.user.id}"
            )

            count = await self.get_unread_count()

            logger.info(
                f"NotificationConsumer.connect(): "
                f"unread_count={count}"
            )

            await self.send_json({
                "type": "unread_count",
                "count": count,
            })

            logger.info(
                "NotificationConsumer.connect(): "
                "initial unread count sent"
            )

        except Exception:
            logger.exception(
                "NotificationConsumer.connect() failed"
            )

            try:
                await self.close(code=1011)
            except Exception:
                pass

    async def handle_mark_read(self, data):
        """
        Client asks us to mark a notification as read.
        """

        notification_id = data.get("notification_id")

        if not notification_id:
            return

        try:
            marked = await self.mark_notification_read(
                notification_id
            )

            if marked:
                count = await self.get_unread_count()

                await self.send_json({
                    "type": "unread_count",
                    "count": count,
                })

        except Exception:
            logger.exception(
                f"Failed to process mark_read for notification "
                f"{notification_id}"
            )

    @database_sync_to_async
    def get_unread_count(self):
        """
        Return the number of unread notifications for the current user.
        """

        logger.info(
            f"Getting unread notification count for user "
            f"{self.user.id}"
        )

        count = self.user.notifications.filter(
            is_read=False
        ).count()

        logger.info(
            f"Unread notification count for user "
            f"{self.user.id}: {count}"
        )

        return count

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """
        Mark one notification as read.
        """

        try:
            notification = self.user.notifications.get(
                id=notification_id
            )

            notification.mark_read()

            logger.info(
                f"Notification {notification_id} marked as read "
                f"for user {self.user.id}"
            )

            return True

        except Exception:
            logger.exception(
                f"Failed to mark notification {notification_id} "
                f"as read for user {self.user.id}"
            )

            return False