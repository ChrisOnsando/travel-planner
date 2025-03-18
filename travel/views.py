from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache
from .models import Trip, LogEntry, DriverProfile
from .serializers import TripSerializer
import requests
from decouple import config
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

class TripPlannerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        driver = DriverProfile.objects.get(user=request.user)
        data = request.data.copy()
        data['driver'] = driver.id
        serializer = TripSerializer(data=data)

        if serializer.is_valid():
            trip = serializer.save()
            route = self.get_route_with_traffic(trip)
            
            if not route:
                return Response({"error": "Could not retrieve route details"}, status=400)

            try:
                plan = self.plan_trip(route, trip.cycle_used)
            except ValueError as e:
                return Response({"error": str(e)}, status=400)

            self.save_logs(trip, plan)
            pdf_path = self.generate_detailed_logs(trip, plan)

            driver.cycle_hours_remaining -= sum(day['driving'] for day in plan)
            driver.save()

            return Response({
                'route': route,
                'plan': plan,
                'pdf_path': pdf_path,
                'remaining_hours': driver.cycle_hours_remaining
            })

        return Response(serializer.errors, status=400)

    def get_route_with_traffic(self, trip):
        api_key = config('MAP_BOX_API_KEY')
        cache_key = f"route_{trip.current_location}_{trip.pickup_location}_{trip.dropoff_location}"
        cached_route = cache.get(cache_key)

        if cached_route:
            return cached_route

        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={trip.current_location}&waypoints={trip.pickup_location}&destination={trip.dropoff_location}&departure_time=now&traffic_model=best_guess&key={api_key}"
        response = requests.get(url).json()

        if 'routes' not in response or not response['routes']:
            return None  

        distance = sum(leg['distance']['value'] for leg in response['routes'][0]['legs']) / 1609.34  # Convert meters to miles
        duration = sum(leg['duration_in_traffic']['value'] for leg in response['routes'][0]['legs']) / 3600  # Convert seconds to hours

        route = {'distance': distance, 'duration': duration, 'path': response['routes'][0]}
        cache.set(cache_key, route, timeout=3600)

        return route

    def plan_trip(self, route, cycle_used):
        total_distance = route['distance']
        driving_time = route['duration']
        fueling_stops = total_distance // 1000
        fueling_time = fueling_stops * 0.5
        total_time = driving_time + fueling_time + 2

        remaining_hours = 70 - cycle_used
        if total_time > remaining_hours:
            raise ValueError("Insufficient cycle hours remaining")

        days = []
        current_time = 0
        current_distance = 0

        while current_time < total_time:
            day = {'driving': 0, 'on_duty': 0, 'stops': []}
            
            # Start of duty (first hour)
            if not days:
                day['on_duty'] += 1
                current_time += 1

            daily_driving = min(11, total_time - current_time)
            day['driving'] = daily_driving
            day['on_duty'] += daily_driving
            current_time += daily_driving
            current_distance += daily_driving * 55

            # Fueling Stops
            if current_distance >= 1000:
                day['stops'].append(f"Fueling at mile {int(current_distance)}")
                day['on_duty'] += 0.5
                current_time += 0.5
                current_distance %= 1000

            # End of duty
            day['on_duty'] = min(day['on_duty'], 14)
            current_time += 10 

            days.append(day)

        return days

    def save_logs(self, trip, plan):
        for i, day in enumerate(plan):
            LogEntry.objects.create(
                trip=trip,
                day_number=i + 1,
                driving_hours=day['driving'],
                on_duty_hours=day['on_duty'],
                stops=day['stops']
            )

    def generate_detailed_logs(self, trip, plan):
        pdf_path = f"media/logs_trip_{trip.id}.pdf"
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True) 
        c = canvas.Canvas(pdf_path, pagesize=letter)

        total_time = sum(day['on_duty'] for day in plan) 
        current_time = 0

        for i, day in enumerate(plan):
            c.setFont("Helvetica", 12)
            c.drawString(50, 750, f"Day {i+1} - Trip ID: {trip.id}")

            for x in range(50, 650, 6):
                c.line(x, 700, x, 650)

            y = 700
            current_x = 50

            if i == 0:
                c.setFillColorRGB(0, 0, 1)
                c.rect(current_x, y-50, 24, 50, fill=1)
                current_x += 24
                current_time += 1

            driving_segments = int(day['driving'] * 4)
            c.setFillColorRGB(0, 1, 0)
            c.rect(current_x, y-50, driving_segments * 6, 50, fill=1)
            current_x += driving_segments * 6
            current_time += day['driving']

            for stop in day['stops']:
                c.setFillColorRGB(1, 1, 0)
                c.rect(current_x, y-50, 2 * 6, 50, fill=1)
                current_x += 12
                current_time += 0.5

            if current_time >= total_time - 1:
                c.setFillColorRGB(0, 0, 1)
                c.rect(current_x, y-50, 24, 50, fill=1)

            c.showPage()

        c.save()
        return pdf_path
