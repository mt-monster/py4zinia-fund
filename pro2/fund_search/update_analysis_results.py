#!/usr/bin/env python
# coding: utf-8

"""
Script to update analysis results for problematic funds
This will trigger the PUT endpoint to update the fund_analysis_results table
"""

import requests
import json

def update_fund_analysis(fund_code):
    """Update analysis results for a fund by calling the PUT endpoint"""
    url = f"http://localhost:5000/api/holdings/{fund_code}"
    
    # We'll send a minimal update that just refreshes the data
    data = {
        "user_id": "default_user",
        # We're not actually changing anything, just triggering the update
        "notes": ""
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.put(url, data=json.dumps(data), headers=headers)
        response.raise_for_status()
        result = response.json()
        if result.get('success'):
            print(f"✓ Successfully updated fund {fund_code}")
        else:
            print(f"✗ Failed to update fund {fund_code}: {result.get('error')}")
    except Exception as e:
        print(f"✗ Error updating fund {fund_code}: {str(e)}")

def main():
    """Update analysis results for all problematic funds"""
    print("Updating analysis results for problematic funds...")
    print("=" * 60)
    
    # List of problematic funds
    problematic_funds = ["021539", "012509", "008706", "025832", "012060", "000157"]
    
    for fund_code in problematic_funds:
        update_fund_analysis(fund_code)
    
    print("=" * 60)
    print("Update completed!")

if __name__ == "__main__":
    main()