"""
FCM (Firebase Cloud Messaging) Push Notification Service — FCM v1 API

Uses the firebase-admin SDK with a service account key.
Sends hybrid notification+data messages so Android's OS displays the
notification even when the app is killed or dozing — data-only messages
get deprioritized by Doze mode and can silently fail to deliver.

In the foreground the Flutter app receives only the `data` block (OS does
not display the `notification` block), so it renders its own styled local
notification. In the background / terminated state the OS displays the
`notification` block directly; the Flutter background isolate is instructed
to skip showing a local notification to avoid duplicates.
"""

import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

_app = None


def _get_firebase_app():
    """Initialize Firebase Admin SDK once per process."""
    global _app
    if _app is None:
        cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_KEY)
        _app = firebase_admin.initialize_app(cred)
    return _app


class FCMNotificationError(Exception):
    pass


def _deactivate_token(token):
    """Mark a device as inactive when its FCM token is no longer valid."""
    from api_v1.models import Device
    Device.objects.filter(registration_id=token).update(active=False)


def send_push_notification(
    registration_ids,
    data_message,
    notification_title=None,
    notification_body=None,
    channel_id=None,
):
    """
    Send an FCM message to one or more device tokens.

    If `notification_title` is provided, a `notification` block is attached
    so the Android OS can display the notification directly even when the
    app is terminated or dozing. Omit it to send data-only.

    All values in data_message must be strings (FCM v1 requirement).
    """
    _get_firebase_app()

    if not registration_ids:
        raise FCMNotificationError("No registration IDs provided")

    if isinstance(registration_ids, str):
        registration_ids = [registration_ids]

    str_data = {k: str(v) for k, v in data_message.items()}

    # Build Android config. When a notification block is attached we also
    # pin the notification to a specific channel so the OS renders it with
    # the correct importance/sound on Android 8+.
    android_notification = None
    if notification_title and channel_id:
        android_notification = messaging.AndroidNotification(
            channel_id=channel_id,
            default_sound=True,
            default_vibrate_timings=True,
        )
    android_config = messaging.AndroidConfig(
        priority='high',
        notification=android_notification,
    )

    top_notification = None
    if notification_title:
        top_notification = messaging.Notification(
            title=notification_title,
            body=notification_body or '',
        )

    results = []
    for token in registration_ids:
        msg = messaging.Message(
            data=str_data,
            token=token,
            notification=top_notification,
            android=android_config,
        )
        try:
            message_id = messaging.send(msg)
            logger.info('FCM sent to %s (msg_id=%s)', token[:12], message_id)
            results.append({'token': token, 'success': True, 'message_id': message_id})
        except messaging.UnregisteredError:
            _deactivate_token(token)
            results.append({'token': token, 'success': False, 'error': 'unregistered'})
        except Exception as e:
            logger.exception('FCM send failed for token %s', token)
            results.append({'token': token, 'success': False, 'error': str(e)})

    return results


def send_to_user(user, data_message, **kwargs):
    """Send a push notification to all active devices for a user."""
    from api_v1.models import Device

    tokens = list(
        Device.objects.filter(user=user, active=True)
        .values_list('registration_id', flat=True)
    )
    if not tokens:
        logger.warning('No active devices for user %s — notification will not be delivered', user.id)
        return []
    return send_push_notification(tokens, data_message, **kwargs)


def send_ring_notification(user, caller_name, message, ring_id):
    """
    Send a ring push notification using keys the Flutter app expects.

    Flutter fcm_service.dart switches on data['event'] == 'ring'
    and reads: ringId, callerName, message.
    """
    data = {
        'event': 'ring',
        'ringId': str(ring_id),
        'callerName': caller_name,
        'message': message,
    }
    return send_to_user(
        user,
        data,
        notification_title=f'Ring from {caller_name}',
        notification_body=message or 'Incoming call',
        channel_id='rings',
    )


def send_message_notification(user, sender_name, content, message_id, message_type='text'):
    """
    Send a new_message push notification using keys the Flutter app expects.

    Flutter fcm_service.dart switches on data['event'] == 'new_message'
    and reads: messageId, senderName, preview, type.
    """
    preview = content or ''
    if not preview:
        if message_type == 'audio':
            preview = '🎤 Audio message'
        elif message_type == 'video':
            preview = '🎥 Video message'
    data = {
        'event': 'new_message',
        'messageId': str(message_id),
        'senderName': sender_name,
        'preview': preview[:100],
        'type': message_type,
    }
    return send_to_user(
        user,
        data,
        notification_title=sender_name,
        notification_body=preview[:100] or 'New message',
        channel_id='messages',
    )
