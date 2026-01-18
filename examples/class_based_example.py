#!/usr/bin/env python3
"""
Example demonstrating the async class-based PetTracer API.

This shows the recommended way to use the library with PetTracerClient
and PetTracerDevice classes with async/await.
"""
import os
import asyncio
from datetime import datetime, timedelta
from pettracer import PetTracerClient


async def main():
    """Example usage of the async class-based PetTracer API."""
    
    # Get credentials from environment variables
    username = os.getenv("PETTRACER_USERNAME")
    password = os.getenv("PETTRACER_PASSWORD")
    
    if not username or not password:
        print("Please set PETTRACER_USERNAME and PETTRACER_PASSWORD environment variables")
        return
    
    # Option 1: Use context manager (recommended - handles session cleanup)
    print("=== Creating client and logging in ===")
    async with PetTracerClient() as client:
        await client.login(username, password)
        print(f"✓ Authenticated: {client.is_authenticated}")
        print(f"✓ Token: {client.token[:20]}...")
        print(f"✓ Token expires: {client.token_expires}")
        
        # Display user information from login response
        print("\n=== User Information (from login) ===")
        print(f"User ID: {client.user_id}")
        print(f"Name: {client.user_name}")
        print(f"Email: {client.email}")
        print(f"Language: {client.language}")
        print(f"Country: {client.country}")
        print(f"Device Count: {client.device_count}")
        
        if client.subscription_info:
            print(f"\n=== Subscription Information ===")
            print(f"Subscription ID: {client.subscription_id}")
            print(f"Expires: {client.subscription_expires}")
            print(f"Odoo ID: {client.subscription_info.odooId}")
        
        # Get user profile
        print("\n=== Getting user profile ===")
        profile = await client.get_user_profile()
        print(f"User: {profile.name}")
        print(f"Email: {profile.email}")
        print(f"City: {profile.city}")
        
        # Get all devices
        print("\n=== Getting all devices ===")
        devices = await client.get_all_devices()
        print(f"Found {len(devices)} device(s)")
        
        for device in devices:
            print(f"\nDevice: {device.details.name} (ID: {device.id})")
            print(f"  Battery: {device.bat}mV")
            print(f"  Status: {device.status}")
            print(f"  Last Contact: {device.lastContact}")
            if device.lastPos:
                print(f"  Last Position: {device.lastPos.posLat}, {device.lastPos.posLong}")
                print(f"  Position Time: {device.lastPos.timeMeasure}")
        
        # Work with a specific device
        if devices:
            device_id = devices[0].id
            print(f"\n=== Working with device {device_id} ===")
            
            # Get device-specific client
            device_client = client.get_device(device_id)
            print(f"Created device client for device {device_client.device_id}")
            
            # Get device info
            print("\n--- Getting device info ---")
            info = await device_client.get_info()
            if isinstance(info, list):
                info = info[0]
            print(f"Device name: {info.details.name}")
            print(f"Battery: {info.bat}mV")
            print(f"Mode: {info.mode}")
            
            # Get position history for the last 6 hours
            print("\n--- Getting position history (last 6 hours) ---")
            now = datetime.now()
            six_hours_ago = now - timedelta(hours=6)
            
            # Convert to milliseconds since epoch
            to_time = int(now.timestamp() * 1000)
            filter_time = int(six_hours_ago.timestamp() * 1000)
            
            positions = await device_client.get_positions(filter_time, to_time)
            print(f"Found {len(positions)} position(s)")
            
            for i, pos in enumerate(positions[:5], 1):  # Show first 5
                print(f"\n  Position {i}:")
                print(f"    Time: {pos.timeMeasure}")
                print(f"    Lat/Long: {pos.posLat}, {pos.posLong}")
                print(f"    Satellites: {pos.sat}")
                print(f"    RSSI: {pos.rssi}")
            
            if len(positions) > 5:
                print(f"\n  ... and {len(positions) - 5} more positions")
    
    # Option 2: Manual session management
    # client = PetTracerClient()
    # await client.login(username, password)
    # ... do work ...
    # await client.close()  # Important: clean up session


if __name__ == "__main__":
    asyncio.run(main())
