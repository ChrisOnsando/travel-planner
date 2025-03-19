import logging
import os
import requests
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .models import Trip, LogEntry, DriverProfile
from .serializers import TripSerializer
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

class TripPlannerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            logger.info(f"Received POST request with data: {request.data}")
            driver, created = DriverProfile.objects.get_or_create(user=request.user)
            logger.info(f"Driver profile: {driver.id}, created: {created}")
            data = request.data.copy()
            data['driver'] = driver.id
            serializer = TripSerializer(data=data)
            if serializer.is_valid():
                trip = serializer.save()
                logger.info(f"Trip saved: {trip.id}")
                route = self.get_route_with_traffic(trip)
                logger.info(f"Route fetched: {route}")
                plan = self.plan_trip(route, trip.cycle_used)
                logger.info(f"Plan generated: {plan}")
                self.save_logs(trip, plan)
                logger.info("Logs saved")
                pdf_path = self.generate_detailed_logs(trip, plan)
                logger.info(f"PDF generated at: {pdf_path}")
                driver.cycle_hours_remaining -= sum(day['driving'] for day in plan)
                driver.save()
                logger.info(f"Driver updated, remaining hours: {driver.cycle_hours_remaining}")
                return Response({
                    'route': route,
                    'plan': plan,
                    'pdf_path': pdf_path,
                    'remaining_hours': driver.cycle_hours_remaining
                })
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=400)
        except Exception as e:
            logger.error(f"Error in TripPlannerView: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)

    def get_route_with_traffic(self, trip):
        access_token = os.getenv('MAPBOX_ACCESS_TOKEN')
        if not access_token:
            raise ValueError("MAPBOX_ACCESS_TOKEN is not set")

        locations = [trip.current_location, trip.pickup_location, trip.dropoff_location]
        coordinates = []
        for loc in locations:
            geo_url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{loc}.json?access_token={access_token}"
            geo_response = requests.get(geo_url).json()
            if not geo_response.get('features'):
                raise ValueError(f"Geocoding failed for location: {loc}")
            coordinates.append(geo_response['features'][0]['center'])

        coords_str = ';'.join(f"{lon},{lat}" for lon, lat in coordinates)
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving-traffic/{coords_str}?access_token={access_token}&geometries=geojson"
        response = requests.get(url).json()
        
        if 'routes' not in response or not response['routes']:
            raise ValueError(f"Directions API failed: {response.get('message', 'No routes found')}")
        
        distance = response['routes'][0]['distance'] / 1609.34  # Convert meters to miles
        duration = response['routes'][0]['duration'] / 3600     # Convert seconds to hours
        route = {
            'distance': distance,
            'duration': duration,
            'path': {
                'geometry': response['routes'][0]['geometry'],
                'legs': [{'end_location': coord} for coord in coordinates[1:]]
            }
        }
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
            if not days:
                day['on_duty'] += 1
                current_time += 1

            daily_driving = min(11, total_time - current_time)
            day['driving'] = daily_driving
            day['on_duty'] += daily_driving
            current_time += daily_driving
            current_distance += (daily_driving / driving_time) * total_distance

            if current_distance >= 1000:
                day['stops'].append(f"Fueling at mile {int(current_distance)}")
                day['on_duty'] += 0.5
                current_time += 0.5
                current_distance %= 1000

            if current_time >= total_time - 1:
                day['on_duty'] += 1
                current_time += 1

            if day['on_duty'] > 14:
                day['on_duty'] = 14
                current_time = len(days) * 24 + 14
            days.append(day)
            current_time += 10
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
        static_dir = os.path.join(settings.STATIC_ROOT or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'), 'logs')
        os.makedirs(static_dir, exist_ok=True)
        
        pdf_path = os.path.join(static_dir, f"logs_trip_{trip.id}.pdf")
        logger.info(f"Generating PDF at: {pdf_path}")
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 780, "Trip Planner Pro - ELD Log")
        c.setFont("Helvetica", 10)
        c.drawString(50, 760, f"Trip ID: {trip.id} | Driver: {trip.driver.user.username}")
        c.line(50, 755, 550, 755)

        total_time = sum(day['driving'] + (0.5 * len(day['stops'])) + (1 if i == 0 or i == len(plan) - 1 else 0) for i, day in enumerate(plan))
        for i, day in enumerate(plan):
            c.setFont("Helvetica", 12)
            c.drawString(50, 730 - i * 100, f"Day {i+1}")
            for x in range(50, 650, 6):
                c.line(x, 700 - i * 100, x, 650 - i * 100)
            for hour in range(0, 25, 2):
                c.drawString(50 + hour * 24, 635 - i * 100, f"{hour}:00")
            y = 700 - i * 100
            current_x = 50
            if i == 0:
                c.setFillColorRGB(0, 0, 1)
                c.rect(current_x, y-50, 24, 50, fill=1)
                current_x += 24
            driving_segments = int(day['driving'] * 4)
            c.setFillColorRGB(0, 1, 0)
            c.rect(current_x, y-50, driving_segments * 6, 50, fill=1)
            current_x += driving_segments * 6
            for stop in day['stops']:
                c.setFillColorRGB(1, 1, 0)
                c.rect(current_x, y-50, 2 * 6, 50, fill=1)
                current_x += 12
            if i == len(plan) - 1: 
                c.setFillColorRGB(0, 0, 1)
                c.rect(current_x, y-50, 24, 50, fill=1)
            if i < len(plan) - 1:
                c.showPage()
        c.save()
        return f"static/logs/logs_trip_{trip.id}.pdf"
