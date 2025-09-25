from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def send_invitation_email(invitation):
    subject = f'Invitation to join {invitation.tenant.name}'
    
    context = {
        'tenant_name': invitation.tenant.name,
        'inviter_name': invitation.invited_by.get_full_name(),
        'role': invitation.role,
        'expires_at': invitation.expires_at,
        'invitation_link': _generate_invitation_link(invitation)
    }
    
    html_content = render_to_string('emails/tenant_invitation.html', context)
    text_content = render_to_string('emails/tenant_invitation.txt', context)
    
    return send_mail(
        subject=subject,
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        html_message=html_content
    )

def _generate_invitation_link(invitation):
    base_url = settings.FRONTEND_URL
    return f"{base_url}/invitations/{invitation.id}/accept"