"""
Trial Management API Views
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated

from api.models import User


class TrialViewSet(ViewSet):
    """
    Trial management endpoints
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def info(self, request):
        """Get current user's trial information"""
        try:
            user = request.user
            
            # Calculate days remaining if trial is active
            days_remaining = None
            trial_status = 'inactive'
            
            if user.is_trial_active and user.trial_end:
                now = timezone.now()
                if now < user.trial_end:
                    days_remaining = (user.trial_end - now).days
                    trial_status = 'active'
                else:
                    trial_status = 'expired'
                    # Update trial status if expired
                    user.is_trial_active = False
                    user.save(update_fields=['is_trial_active'])
            
            trial_info = {
                'trial_start': user.trial_start.isoformat() if user.trial_start else None,
                'trial_end': user.trial_end.isoformat() if user.trial_end else None,
                'is_trial_active': user.is_trial_active,
                'days_remaining': days_remaining,
                'trial_status': trial_status
            }
            
            return Response(trial_info)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get trial info: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """Start a trial for the current user"""
        try:
            user = request.user
            days = request.data.get('days', 7)  # Default 7 days
            
            if user.is_trial_active:
                return Response(
                    {'error': 'User already has an active trial'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Start trial
            user.trial_start = timezone.now()
            user.trial_end = user.trial_start + timedelta(days=days)
            user.is_trial_active = True
            user.save(update_fields=['trial_start', 'trial_end', 'is_trial_active'])
            
            trial_info = {
                'trial_start': user.trial_start.isoformat(),
                'trial_end': user.trial_end.isoformat(),
                'is_trial_active': user.is_trial_active,
                'days_remaining': days,
                'trial_status': 'active',
                'message': f'Trial started for {days} days'
            }
            
            return Response(trial_info, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to start trial: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def extend(self, request):
        """Extend the current trial"""
        try:
            user = request.user
            days = request.data.get('days', 7)
            
            if not user.is_trial_active:
                return Response(
                    {'error': 'No active trial to extend'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extend trial
            if user.trial_end:
                user.trial_end = user.trial_end + timedelta(days=days)
            else:
                user.trial_end = timezone.now() + timedelta(days=days)
            
            user.save(update_fields=['trial_end'])
            
            # Calculate new days remaining
            days_remaining = (user.trial_end - timezone.now()).days
            
            trial_info = {
                'trial_start': user.trial_start.isoformat() if user.trial_start else None,
                'trial_end': user.trial_end.isoformat(),
                'is_trial_active': user.is_trial_active,
                'days_remaining': days_remaining,
                'trial_status': 'active',
                'message': f'Trial extended by {days} days'
            }
            
            return Response(trial_info)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to extend trial: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def end(self, request):
        """End the current trial"""
        try:
            user = request.user
            
            if not user.is_trial_active:
                return Response(
                    {'error': 'No active trial to end'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # End trial
            user.is_trial_active = False
            user.save(update_fields=['is_trial_active'])
            
            trial_info = {
                'trial_start': user.trial_start.isoformat() if user.trial_start else None,
                'trial_end': user.trial_end.isoformat() if user.trial_end else None,
                'is_trial_active': user.is_trial_active,
                'days_remaining': 0,
                'trial_status': 'inactive',
                'message': 'Trial ended'
            }
            
            return Response(trial_info)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to end trial: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
