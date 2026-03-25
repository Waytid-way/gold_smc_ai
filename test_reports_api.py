#!/usr/bin/env python3
"""Test script to verify /api/reports endpoint"""

import requests
import json

BASE_URL = "http://localhost:5055"

def test_reports_endpoint():
    """Test the /api/reports endpoint"""
    try:
        print("🧪 Testing /api/reports endpoint...")
        response = requests.get(f"{BASE_URL}/api/reports?limit=10&page=1")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Endpoint responded successfully!")
            print(f"\nStatus: {data.get('status')}")
            print(f"Total Reports: {data.get('pagination', {}).get('total', 0)}")
            
            reports = data.get('reports', [])
            if reports:
                print(f"\nFound {len(reports)} reports:")
                print("-" * 80)
                for i, report in enumerate(reports, 1):
                    print(f"\n{i}. Report #{report.get('id')}")
                    print(f"   Trade ID: #{report.get('trade_id')}")
                    print(f"   Reason: {report.get('reason_label')}")
                    print(f"   Trade Result: {report.get('trade_result')}")
                    print(f"   Details: {report.get('details', '(no details)')[:50]}...")
                    print(f"   Reported At: {report.get('reported_at')}")
                print("-" * 80)
            else:
                print("\n⚠️ No reports found in database")
        else:
            print(f"❌ Error: Status {response.status_code}")
            print(response.text)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on port 5055?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_reports_endpoint()
