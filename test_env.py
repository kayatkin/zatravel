import os
from dotenv import load_dotenv

load_dotenv()

print("AMADEUS_API_KEY:", os.getenv('AMADEUS_API_KEY'))
print("AMADEUS_API_SECRET:", os.getenv('AMADEUS_API_SECRET'))
print("SECRET_KEY:", os.getenv('SECRET_KEY'))