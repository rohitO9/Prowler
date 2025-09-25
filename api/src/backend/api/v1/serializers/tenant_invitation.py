from rest_framework import serializers

class TenantInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['member', 'admin'])
    expires_in_days = serializers.IntegerField(min_value=1, max_value=30, default=7)

    def validate_email(self, value):
        if value.lower().endswith(('.test', '.example')):
            raise serializers.ValidationError("Invalid email domain")
        return value.lower()