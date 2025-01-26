import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import pandas as pd
import hashlib

class FlightDatabase:
    def __init__(self):
        self.flights = {
            "london": {"economy": 799, "business": 2399, "first": 4999},
            "paris": {"economy": 899, "business": 2699, "first": 5399},
            "tokyo": {"economy": 1400, "business": 4200, "first": 8400},
            "berlin": {"economy": 499, "business": 1499, "first": 2999}
        }
        self.seat_availability = self._initialize_seats()
        
    def _initialize_seats(self):
        availability = {}
        today = datetime.now()
        for city in self.flights:
            availability[city] = {}
            for i in range(30):  # Next 30 days
                date = today + timedelta(days=i)
                date_str = date.strftime('%m-%d')
                availability[city][date_str] = {
                    "economy": 100,
                    "business": 20,
                    "first": 10
                }
        return availability
    
    def check_availability(self, city, date_str, ticket_class):
        date_str = date_str[5:] #hack to avoid year
        if city.lower() in self.seat_availability:
            if date_str in self.seat_availability[city.lower()]:
                return self.seat_availability[city.lower()][date_str][ticket_class.lower()]
        return 0
    
    def get_price(self, city, ticket_class):
        city = city.lower()
        ticket_class = ticket_class.lower()
        return self.flights.get(city, {}).get(ticket_class, None)

class BookingSystem:
    def __init__(self):
        self.db = pd.DataFrame()
        self.counter = 0
        self.flight_db = FlightDatabase()
        
    def generate_booking_id(self):
        self.counter += 1
        return f"BK-{self.counter:06d}"
    
    def calculate_loyalty_points(self, price):
        return int(price * 0.1)  # 10% of price as points
    
    def validate_email(self, email):
        return "@" in email and "." in email
    
    def generate_confirmation_code(self, booking_id):
        return hashlib.md5(booking_id.encode()).hexdigest()[:8].upper()
    
    def book_ticket(self, destination, num_tickets, ticket_class, email, date_str):
        city = destination.lower()
        
        # Validate inputs
        if not self.validate_email(email):
            return {"error": "Invalid email address"}
            
        price = self.flight_db.get_price(city, ticket_class)
        if price is None:
            return {"error": "Invalid destination or ticket class"}
            
        availability = self.flight_db.check_availability(city, date_str, ticket_class)
        print(availability)
        print("num")
        print(num_tickets)
        if availability < num_tickets:
            return {"error": "Not enough seats available"}
            
        total_price = price * num_tickets
        booking_id = self.generate_booking_id()
        confirmation_code = self.generate_confirmation_code(booking_id)
        loyalty_points = self.calculate_loyalty_points(total_price)
        
        booking_data = {
            "booking_id": [booking_id],
            "confirmation_code": [confirmation_code],
            "email": [email],
            "destination": [city],
            "date": [date_str],
            "num_tickets": [num_tickets],
            "ticket_class": [ticket_class],
            "total_price": [total_price],
            "loyalty_points": [loyalty_points],
            "booking_time": [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        }
        
        self.db = pd.concat([self.db, pd.DataFrame(booking_data)], ignore_index=True)
        self.db.to_csv('bookings.csv', index=False)
        
        return {
            "booking_id": booking_id,
            "confirmation_code": confirmation_code,
            "total_price": total_price,
            "loyalty_points": loyalty_points
        }

class AirlineAssistant:
    def __init__(self):
        load_dotenv()
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY', 'your-key-if-not-using-env'))
        self.model = "gpt-4o-mini"
        self.booking_system = BookingSystem()
        self.system_message = """You are FlightAI's assistant. Provide concise, accurate responses.
        Available destinations: London, Paris, Tokyo, Berlin
        Classes: Economy, Business, First
        Features: Loyalty points (10% of price), Seat availability check, Email confirmations"""
        
    def _get_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_flight",
                    "description": "Check flight availability and price",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "date": {"type": "string", "format": "date"},
                            "ticket_class": {"type": "string"}
                        },
                        "required": ["destination", "date", "ticket_class"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "book_flight",
                    "description": "Book a flight ticket",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {"type": "string"},
                            "date": {"type": "string", "format": "date"},
                            "num_tickets": {"type": "integer"},
                            "ticket_class": {"type": "string"},
                            "email": {"type": "string"}
                        },
                        "required": ["destination", "date", "num_tickets", "ticket_class", "email"]
                    }
                }
            }
        ]

    def handle_tool_call(self, message):
        tool_call = message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        
        if tool_call.function.name == "check_flight":
            availability = self.booking_system.flight_db.check_availability(
                args["destination"], args["date"], args["ticket_class"]
            )
            print(availability)
            print("num")
            price = self.booking_system.flight_db.get_price(
                args["destination"], args["ticket_class"]
            )

            print(args)
            print(price)
            return {
                "role": "tool",
                "content": json.dumps({
                    "availability": availability,
                    "price": price,
                    "loyalty_points": int(price * 0.1)
                }),
                "tool_call_id": tool_call.id
            }
            
        elif tool_call.function.name == "book_flight":
            result = self.booking_system.book_ticket(
                args["destination"],
                args["num_tickets"],
                args["ticket_class"],
                args["email"],
                args["date"]
            )
            return {
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call.id
            }

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_message}]
        for human, assistant in history:
            messages.extend([
                {"role": "user", "content": human},
                {"role": "assistant", "content": assistant}
            ])
        messages.append({"role": "user", "content": message})
        
        response = self.openai.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._get_tools()
        )
        
        if response.choices[0].finish_reason == "tool_calls":
            message = response.choices[0].message
            tool_response = self.handle_tool_call(message)
            messages.extend([message, tool_response])
            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
        return response.choices[0].message.content

def create_interface():
    assistant = AirlineAssistant()
    return gr.ChatInterface(
        fn=assistant.chat,
        title="FlightAI Booking Assistant",
        description="Book flights, check availability, and earn loyalty points!"
    )

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)