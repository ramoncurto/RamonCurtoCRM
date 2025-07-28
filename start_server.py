#!/usr/bin/env python3
"""
Elite Athlete CRM - Server Startup Script
A simple script to start the FastAPI server with proper configuration
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        print("📄 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment variables loaded successfully")
    else:
        print("⚠️  No .env file found - using system environment variables")

def check_dependencies():
    """Check if all required dependencies are installed"""
    # Map package names to their import names
    required_packages = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn', 
        'jinja2': 'jinja2',
        'fuzzywuzzy': 'fuzzywuzzy',
        'python-Levenshtein': 'Levenshtein'
    }
    
    missing = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    if missing:
        print("❌ Missing dependencies:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nRun: pip install -r requirements.txt")
        return False
    
    return True

def create_directories():
    """Create necessary directories if they don't exist"""
    directories = ['uploads', 'templates']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directory '{directory}' ready")

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting Elite Athlete CRM Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("\n🔗 Quick Links:")
    print("   Dashboard: http://localhost:8000/dashboard")
    print("   Athletes: http://localhost:8000/athletes")
    print("   History: http://localhost:8000/history")
    print("   Communication Hub: http://localhost:8000/communication-hub")
    print("\n⚡ Press Ctrl+C to stop the server\n")
    
    # Wait a moment before opening browser
    time.sleep(2)
    
    # Open browser
    try:
        webbrowser.open('http://localhost:8000/dashboard')
    except:
        pass
    
    # Start the server
    cmd = [
        sys.executable, '-m', 'uvicorn',
        'main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Thank you for using Elite Athlete CRM!")

def main():
    """Main startup function"""
    print("🏆 Elite Athlete CRM - Advanced Audio Processing System")
    print("=" * 60)
    
    # Load environment variables
    load_env_file()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()
