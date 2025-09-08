#!/usr/bin/env python3
"""
Test script to verify Docker setup
"""

import subprocess
import time
import requests
import sys

def run_command(cmd):
    """Run a shell command and return output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.returncode == 0

def test_docker_build():
    """Test Docker image build"""
    print("\n1. Testing Docker build...")
    return run_command("docker-compose build --no-cache api")

def test_docker_up():
    """Test Docker compose up"""
    print("\n2. Starting services...")
    return run_command("docker-compose up -d api")

def test_api_health():
    """Test API health endpoint"""
    print("\n3. Testing API health...")
    time.sleep(5)  # Wait for API to start
    
    try:
        response = requests.get("http://localhost:8001/health")
        if response.status_code == 200:
            print(f"✓ API is healthy: {response.json()}")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to API: {e}")
        return False

def test_docker_down():
    """Stop Docker services"""
    print("\n4. Stopping services...")
    return run_command("docker-compose down")

def main():
    """Run all tests"""
    print("Docker Setup Test Suite")
    print("=" * 50)
    
    tests = [
        ("Docker Build", test_docker_build),
        ("Docker Up", test_docker_up),
        ("API Health", test_api_health),
        ("Docker Down", test_docker_down)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"✗ {name} failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()