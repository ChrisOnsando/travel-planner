from django.db import models
from django.contrib.auth.models import User

class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cycle_hours_remaining = models.FloatField(default=70.0)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Trip(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE)
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    cycle_used = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('planned', 'Planned'), ('completed', 'Completed')], default='planned')

    def __str__(self):
        return f"Trip {self.id} by {self.driver.user.username}"

class LogEntry(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    day_number = models.IntegerField()
    driving_hours = models.FloatField()
    on_duty_hours = models.FloatField()
    stops = models.JSONField(default=list)

    def __str__(self):
        return f"Log Day {self.day_number} for Trip {self.trip.id}"
