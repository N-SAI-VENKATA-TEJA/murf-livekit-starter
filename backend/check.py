import asyncio, motor.motor_asyncio, os
from dotenv import load_dotenv

load_dotenv('.env.local')
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ['MONGODB_URI'])
db = client['bolobuddy']

async def main():
    doc = await db.children.find_one({'name': 'Hari'})
    print("Hari Doc:", doc)

asyncio.run(main())
