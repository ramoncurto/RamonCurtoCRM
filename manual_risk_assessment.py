#!/usr/bin/env python3
"""
Script to manage manual risk assessment
"""

import os
import requests
import json
from typing import List, Dict

def check_server_status():
    """Check if the server is running"""
    try:
        response = requests.get("http://localhost:8000/system/status", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_athletes() -> List[Dict]:
    """Get list of athletes from the server"""
    try:
        response = requests.get("http://localhost:8000/api/athletes/enhanced")
        if response.status_code == 200:
            data = response.json()
            return data.get('athletes', [])
        else:
            print(f"❌ Error getting athletes: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return []

def assess_risk_for_athlete(athlete_id: int) -> Dict:
    """Assess risk for a specific athlete"""
    try:
        response = requests.get(f"http://localhost:8000/api/athletes/{athlete_id}/risk")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def assess_risk_for_all_athletes():
    """Assess risk for all athletes"""
    athletes = get_athletes()
    
    if not athletes:
        print("❌ No athletes found or server not running")
        return
    
    print(f"🏆 Assessing risk for {len(athletes)} athletes...")
    print("=" * 50)
    
    results = []
    
    for i, athlete in enumerate(athletes, 1):
        print(f"[{i}/{len(athletes)}] Assessing {athlete.get('name', 'Unknown')}...")
        
        result = assess_risk_for_athlete(athlete['id'])
        
        if 'error' in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            risk_level = result.get('level', 'unknown')
            risk_score = result.get('score', 0)
            print(f"   ✅ Risk: {risk_level} (Score: {risk_score})")
        
        results.append({
            'athlete': athlete,
            'result': result
        })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    
    successful = [r for r in results if 'error' not in r['result']]
    failed = [r for r in results if 'error' in r['result']]
    
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if successful:
        risk_levels = {}
        for r in successful:
            level = r['result'].get('level', 'unknown')
            risk_levels[level] = risk_levels.get(level, 0) + 1
        
        print("\nRisk Distribution:")
        for level, count in risk_levels.items():
            print(f"   {level.upper()}: {count}")

def assess_risk_for_specific_athlete():
    """Assess risk for a specific athlete by ID"""
    athletes = get_athletes()
    
    if not athletes:
        print("❌ No athletes found")
        return
    
    print("Available athletes:")
    for athlete in athletes:
        print(f"   {athlete['id']}: {athlete['name']}")
    
    try:
        athlete_id = int(input("\nEnter athlete ID: "))
        result = assess_risk_for_athlete(athlete_id)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Risk Assessment Complete:")
            print(f"   Level: {result.get('level', 'unknown')}")
            print(f"   Score: {result.get('score', 0)}")
            print(f"   Color: {result.get('color', 'unknown')}")
            
            if result.get('evidence'):
                print(f"   Evidence: {', '.join(result['evidence'][:3])}")
    
    except ValueError:
        print("❌ Invalid athlete ID")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main function"""
    print("🏆 Elite Athlete CRM - Manual Risk Assessment")
    print("=" * 50)
    
    if not check_server_status():
        print("❌ Server not running. Please start the server first:")
        print("   python start_server.py")
        return
    
    print("✅ Server is running")
    print()
    
    while True:
        print("Options:")
        print("1. Assess risk for all athletes")
        print("2. Assess risk for specific athlete")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            assess_risk_for_all_athletes()
        elif choice == '2':
            assess_risk_for_specific_athlete()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")
        
        print("\n" + "-" * 30 + "\n")

if __name__ == "__main__":
    main()