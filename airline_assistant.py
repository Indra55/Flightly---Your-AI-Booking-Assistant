import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import gradio as gr
import pandas as pd
import hashlib

class FlightDatabase:
    def __init__(self):
        self.meal_options = {
            "regular": ["vegetarian", "non-vegetarian", "vegan", "halal", "kosher"],
            "special": ["diabetic", "gluten-free", "low-sodium", "low-fat"]
        }
        self.seat_preferences = {
            "location": ["window", "aisle", "middle"],
            "section": ["front", "middle", "back"],
            "special": ["extra legroom", "bassinet", "wheelchair accessible"]
        }
        self.flights = {
            "london": {
                "source_city": "New York",  
                "economy": {"price": 799, "duration": "8h 15m", "airline": "British Airways", "baggage": "1 checked bag, 1 carry-on", "currency": "GBP", "flight_type": "non-stop", "departure_airports": ["Heathrow", "Gatwick"], "arrival_airports": ["London Heathrow"]},
                "business": {"price": 2399, "duration": "8h 15m", "airline": "British Airways", "baggage": "2 checked bags, 1 carry-on", "currency": "GBP", "flight_type": "non-stop", "departure_airports": ["Heathrow", "Gatwick"], "arrival_airports": ["London Heathrow"]},
                "first": {"price": 4999, "duration": "8h 15m", "airline": "British Airways", "baggage": "3 checked bags, 2 carry-ons", "currency": "GBP", "flight_type": "non-stop", "departure_airports": ["Heathrow", "Gatwick"], "arrival_airports": ["London Heathrow"]},
                "meal_service": True,
                "special_assistance": ["wheelchair", "medical oxygen", "special meals"],
                "seat_config": {
                    "economy": {"rows": "20-50", "layout": "3-3-3"},
                    "business": {"rows": "10-19", "layout": "2-2-2"},
                    "first": {"rows": "1-9", "layout": "1-2-1"}
                }
            },
            "paris": {
                "source_city": "Los Angeles",  
                "economy": {"price": 899, "duration": "6h 30m", "airline": "Air France", "baggage": "1 checked bag, 1 carry-on", "currency": "EUR", "flight_type": "non-stop", "departure_airports": ["Charles de Gaulle", "Orly"], "arrival_airports": ["Charles de Gaulle"]},
                "business": {"price": 2699, "duration": "6h 30m", "airline": "Air France", "baggage": "2 checked bags, 1 carry-on", "currency": "EUR", "flight_type": "non-stop", "departure_airports": ["Charles de Gaulle", "Orly"], "arrival_airports": ["Charles de Gaulle"]},
                "first": {"price": 5399, "duration": "6h 30m", "airline": "Air France", "baggage": "3 checked bags, 2 carry-ons", "currency": "EUR", "flight_type": "non-stop", "departure_airports": ["Charles de Gaulle", "Orly"], "arrival_airports": ["Charles de Gaulle"]}
            },
            "tokyo": {
                "source_city": "San Francisco",   
                "economy": {"price": 1400, "duration": "12h 50m", "airline": "ANA", "baggage": "1 checked bag, 1 carry-on", "currency": "JPY", "flight_type": "non-stop", "departure_airports": ["Narita", "Haneda"], "arrival_airports": ["Narita"]},
                "business": {"price": 4200, "duration": "12h 50m", "airline": "ANA", "baggage": "2 checked bags, 1 carry-on", "currency": "JPY", "flight_type": "non-stop", "departure_airports": ["Narita", "Haneda"], "arrival_airports": ["Narita"]},
                "first": {"price": 8400, "duration": "12h 50m", "airline": "ANA", "baggage": "3 checked bags, 2 carry-ons", "currency": "JPY", "flight_type": "non-stop", "departure_airports": ["Narita", "Haneda"], "arrival_airports": ["Narita"]}
            },
            "berlin": {
                "source_city": "Chicago",   
                "economy": {"price": 499, "duration": "8h 0m", "airline": "Lufthansa", "baggage": "1 checked bag, 1 carry-on", "currency": "EUR", "flight_type": "non-stop", "departure_airports": ["Berlin Tegel", "Berlin Schönefeld"], "arrival_airports": ["Berlin Tegel"]},
                "business": {"price": 1499, "duration": "8h 0m", "airline": "Lufthansa", "baggage": "2 checked bags, 1 carry-on", "currency": "EUR", "flight_type": "non-stop", "departure_airports": ["Berlin Tegel", "Berlin Schönefeld"], "arrival_airports": ["Berlin Tegel"]},
                "first": {"price": 2999, "duration": "8h 0m", "airline": "Lufthansa", "baggage": "3 checked bags, 2 carry-ons", "currency": "EUR", "flight_type": "non-stop", "departure_airports": ["Berlin Tegel", "Berlin Schönefeld"], "arrival_airports": ["Berlin Tegel"]}
            },
            "mumbai": {
                "source_city": "Dubai",   
                "economy": {"price": 1999, "duration": "9h 30m", "airline": "Emirates", "baggage": "1 checked bag, 1 carry-on", "currency": "INR", "flight_type": "one-stop", "departure_airports": ["Chhatrapati Shivaji International"], "arrival_airports": ["Chhatrapati Shivaji International"]},
                "business": {"price": 2499, "duration": "9h 30m", "airline": "Emirates", "baggage": "2 checked bags, 1 carry-on", "currency": "INR", "flight_type": "one-stop", "departure_airports": ["Chhatrapati Shivaji International"], "arrival_airports": ["Chhatrapati Shivaji International"]},
                "first": {"price": 3999, "duration": "9h 30m", "airline": "Emirates", "baggage": "3 checked bags, 2 carry-ons", "currency": "INR", "flight_type": "one-stop", "departure_airports": ["Chhatrapati Shivaji International"], "arrival_airports": ["Chhatrapati Shivaji International"]}
            }
        }
        self.seat_availability = self._initialize_seats()
        self.date_range = {
            "min_date": datetime.now(),
            "max_date": datetime.now() + timedelta(days=365)  # Bookings up to 1 year in advance
        }
        
    def _initialize_seats(self):
        availability = {}
        today = datetime.now()
        for city in self.flights:
            availability[city] = {}
            for i in range(30):  
                date = today + timedelta(days=i)
                date_str = date.strftime('%m-%d')
                availability[city][date_str] = {
                    "economy": 100,
                    "business": 20,
                    "first": 10
                }
        return availability
    
    def check_availability(self, city, date_str, ticket_class):
        date_str = date_str[5:] 
        if city.lower() in self.seat_availability:
            if date_str in self.seat_availability[city.lower()]:
                return self.seat_availability[city.lower()][date_str][ticket_class.lower()]
        return 0
    
    def get_price(self, city, ticket_class):
        city = city.lower()
        ticket_class = ticket_class.lower()
        return self.flights.get(city, {}).get(ticket_class, {}).get('price', None)

    def is_valid_date(self, date_str):
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            return self.date_range["min_date"] <= date <= self.date_range["max_date"]
        except ValueError:
            return False

    def get_available_dates(self, city):
        available_dates = []
        now = datetime.now()
        for i in range(30):  # Show next 30 days availability
            date = now + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            if self.check_availability(city, date_str, 'economy') > 0:
                available_dates.append(date_str)
        return available_dates

class BookingSystem:
    def __init__(self):
        self.db_file = 'bookings.csv'
        self.flight_db = FlightDatabase()
        self._initialize_db()

    def _initialize_db(self):
        columns = [
            "booking_id", "confirmation_code", "email", "destination", "date",
            "num_tickets", "ticket_class", "total_price", "loyalty_points",
            "seat_preferences", "meal_preferences", "medical_assistance",
            "special_requests", "booking_time"
        ]
        if not os.path.exists(self.db_file):
            pd.DataFrame(columns=columns).to_csv(self.db_file, index=False)
        
    def generate_booking_id(self):
        return f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def calculate_loyalty_points(self, price):
        return int(price * 0.1)  
    
    def validate_email(self, email):
        return "@" in email and "." in email
    
    def generate_confirmation_code(self, booking_id):
        return hashlib.md5(booking_id.encode()).hexdigest()[:8].upper()
    
    def book_ticket(self, destination, num_tickets, ticket_class, email, date_str, 
                   seat_prefs=None, meal_prefs=None, medical_needs=None, special_requests=None):
        city = destination.lower()

        # Add date validation
        if not self.flight_db.is_valid_date(date_str):
            return {"error": "Invalid date. Please select a date within the next year."}

        if not self.validate_email(email):
            return {"error": "Invalid email address"}
            
        price = self.flight_db.get_price(city, ticket_class)
        if price is None:
            return {"error": "Invalid destination or ticket class"}
            
        availability = self.flight_db.check_availability(city, date_str, ticket_class)
        if availability < num_tickets:
            return {"error": "Not enough seats available"}
            
        total_price = price * num_tickets
        booking_id = self.generate_booking_id()
        confirmation_code = self.generate_confirmation_code(booking_id)
        loyalty_points = self.calculate_loyalty_points(total_price)
        
        booking_data = {
            "booking_id": booking_id,
            "confirmation_code": confirmation_code,
            "email": email,
            "destination": city,
            "date": date_str,
            "num_tickets": num_tickets,
            "ticket_class": ticket_class,
            "total_price": total_price,
            "loyalty_points": loyalty_points,
            "seat_preferences": json.dumps(seat_prefs or {}),
            "meal_preferences": json.dumps(meal_prefs or {}),
            "medical_assistance": json.dumps(medical_needs or []),
            "special_requests": special_requests or "",
            "booking_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        df = pd.read_csv(self.db_file)
        df = pd.concat([df, pd.DataFrame([booking_data])], ignore_index=True) 
        df.to_csv(self.db_file, index=False)
        
        date_key = date_str[5:]
        self.flight_db.seat_availability[city][date_key][ticket_class.lower()] -= num_tickets
        
        return booking_data

class AirlineAssistant:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv('GOOGLE_GENAI_API_KEY', 'your-key-if-not-using-env'))
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.booking_system = BookingSystem()
        flight_db = self.booking_system.flight_db
        self.system_message = f"""You are a helpful and efficient flight booking assistant for FlightAI. Your goal is to assist users in booking flights, checking availability, and understanding pricing and loyalty points.

### **Flight Data:**
{json.dumps(flight_db.flights, indent=4)}

### **Available Options:**
**Meal Options:**
{json.dumps(flight_db.meal_options, indent=2)}

**Seat Preferences:**
{json.dumps(flight_db.seat_preferences, indent=2)}

**Medical Assistance Available:**
- Wheelchair assistance
- Medical oxygen
- Onboard medical staff
- Special medical meals
- Assistance for visual/hearing impaired
"We are in 2025"
### **Process:**

1. **Understand User Request:**  
   Carefully analyze the user's message to identify their intent (book flight, check availability, ask about price, etc.).

2. **Ask Clarifying Questions:**  
   Additional preferences to collect:
   - Seat preference (window/aisle/middle, section preference)
   - Meal preferences and dietary restrictions
   - Number of seats and seating arrangement if traveling in group
   - Any medical assistance or special needs required

3. **Validate Required Information for Booking:**  
   A booking can **only proceed** if the user provides the following:  
   - **Full Name** (Only letters and spaces)  
   - **Phone Number** (Exactly 10 digits)  
   - **Passport Number** (6-9 uppercase alphanumeric characters)  
   - **Email Address** (Valid format: example@domain.com)  

   If any of these details are missing or invalid, inform the user and request the correct details before proceeding.  

   Additional validation:
   - Meal preferences must match available options
   - Seat preferences must be available
   - Medical assistance requests must be specified in advance

4. **Provide Information:**  
   - For **availability requests**, check and clearly state availability for the requested destination, date, and class.  
   - For **price inquiries**, provide the price for the specified destination and class.  
   - Explain **loyalty points earned** (10% of the total price).  
   Also include:
   - Available meal options for the flight
   - Seat layout and availability
   - Special assistance services

5. **Booking Confirmation:**  
   - Once **all required booking details** (destination, date, number of tickets, class, name, phone number, passport number, and email) are received and validated, confirm the booking details with the user.  
   - If all details are correct, proceed with booking and provide a **confirmation message** with a **booking ID and confirmation code**.  
   - If there are any issues (e.g., invalid input, missing details, no availability), inform the user clearly and guide them on how to proceed.
   Additional confirmation details:
   - Selected seat preferences
   - Meal choices
   - Medical assistance arrangements
   - Special requests noted

### **Important Rules:**
- **A flight booking will NOT be processed unless all required details are provided and validated.**
- Be concise and professional in your responses.
- Always **check flight availability** before confirming a booking.
- Clearly present booking details, confirmations, and any validation errors.
- Confirm all special requirements and medical needs
- Verify meal preferences match dietary restrictions
- Ensure requested seats are available in chosen class

### **Booking Requirements:**
**Date Selection Rules:**
- Bookings available up to 365 days in advance
- Dates must be in YYYY-MM-DD format
- No bookings for past dates
- Subject to seat availability

### **Process:**
1. **Date Validation:**
   - Check if requested date is within valid booking window
   - Verify seat availability for selected date
   - Suggest alternative dates if requested date unavailable

2. **Understand User Request:** 
   # ...rest of existing process...

### **Important Rules:**
# ...existing rules...
- Verify date is within valid booking window
- Check seat availability for specific date
"""
    def chat(self, message, history):
        messages = [self.system_message]
        for human, assistant in history:
            messages.append(human)
            messages.append(assistant)
        messages.append(message)
        
        response = self.model.generate_content(messages)
        return response.text
    
    

def create_interface():
    assistant = AirlineAssistant()
    return gr.ChatInterface(
        fn=assistant.chat,
        title="Flightly - Your AI Booking Assistant",
        description="Book flights, check availability, and earn loyalty points!"
    )

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)
