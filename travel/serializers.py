from rest_framework import serializers
from .models import Trip, LogEntry, DriverProfile

class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    logs = LogEntrySerializer(many=True, read_only=True)
    class Meta:
        model = Trip
        fields = '__all__'

class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = '__all__'
        