"""
FCM (Firebase Cloud Messaging) Push Notification Service

This module provides functions to send push notifications to registered devices.
"""

import os
import requests
from django.conf import settings


class FCMNotificationError(Exception):
    """Custom exception for FCM notification errors"""
    pass


def get_fcm_server_key():
    """Get FCM server key from settings or environment"""
    return getattr(settings, 'FCM_SERVER_KEY', os.environ.get('FCM_SERVER_KEY', ''))


def send_push_notification(registration_ids, data_message, notification_payload=None):
    """
    Send push notification to one or more devices via FCM.
    
    Args:
        registration_ids: List of FCM device tokens
        data_message: Dictionary of data payload (key-value pairs)
        notification_payload: Optional dictionary with 'title' and 'body' for notification
    
    Returns:
        dict: FCM response containing success/failure counts
    
    Raises:
        FCMNotificationError: If FCM server key is not configured or request fails
    """
    server_key = get_fcm_server_key()
    
    if not server_key:
        raise FCMNotificationError("FCM_SERVER_KEY is not configured")
    
    if not registration_ids:
        raise FCMNotificationError("No registration IDs provided")
    
    # Ensure registration_ids is a list
    if isinstance(registration_ids, str):
        registration_ids = [registration_ids]
    
    url = 'https://fcm.googleapis.com/fcm/send'
    
    payload = {
        'registration_ids': registration_ids,
        'data': data_message,
    }
    
    # Add notification payload if provided
    if notification_payload:
        payload['notification'] = {
            'title': notification_payload.get('title', ''),
            'body': notification_payload.get('body', ''),
            'sound': 'default',
            'badge': '1',
        }
    
    # Add priority for immediate delivery
    payload['priority'] = 'high'
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'key={server_key}',
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Check for errors in the response
        if result.get('error'):
            raise FCMNotificationError(f"FCM Error: {result['error']}")
        
        return {
            'success': result.get('success', 0),
            'failure': result.get('failure', 0),
            'message_id': result.get('message_id'),
            'results': result.get('results', []),
        }
        
    except requests.exceptions.RequestException as e:
        raise FCMNotificationError(f"Failed to send FCM notification: {str(e)}")


def send_to_user(user, data_message, notification_payload=None):
    """
    Send push notification to all devices belonging to a user.
    
    Args:
        user: Django User instance
        data_message: Dictionary of data payload
        notification_payload: Optional notification payload
    
    Returns:
        dict: Result from send_push_notification
    """
    from api_v1.models import Device
    
    # Get all active devices for the user
    devices = Device.objects.filter(user=user, active=True)
    
    if not devices:
        return {
            'success': 0,
            'failure': 0,
            'message': 'No active devices found for user',
        }
    
    registration_ids = list(devices.values_list('registration_id', flat=True))
    
    return send_push_notification(registration_ids, data_message, notification_payload)


def send_ring_notification(user, caller_name, message, ring_id):
    """
    Send a ring notification to a user.
    
    Args:
        user: Django User instance
        caller_name: Name of the caller
        message: Message to display
        ring_id: Unique ring identifier
    
    Returns:
        dict: Result from send_push_notification
    """
    data_message = {
        'type': 'ring',
        'ringId': ring_id,
        'callerName': caller_name,
        'message': message,
    }
    
    notification_payload = {
        'title': f'📞 {caller_name}',
        'body': message,
    }
    
    return send_to_user(user, data_message, notification_payload)


def send_message_notification(user, sender_name, content):
    """
    Send a message notification to a user.
    
    Args:
        user: Django User instance
        sender_name: Name of the message sender
        content: Message content
    
    Returns:
        dict: Result from send_push_notification
    """
    data_message = {
        'type': 'new_message',
        'senderName': sender_name,
        'content': content,
    }
    
    notification_payload = {
        'title': f'💬 {sender_name}',
        'body': content[:100] if len(content) > 100 else content,
    }
    
    return send_to_user(user, data_message, notification_payload)