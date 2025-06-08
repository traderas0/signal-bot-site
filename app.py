from flask import Flask, request, jsonify
from flask_cors import CORS
from signal_bot import analyze_pair, is_user_verified

app = Flask(__name__)
CORS(app)

@app.route('/get-signal', methods=['POST'])
def get_signal():
    data = request.get_json()
    trader_id = data.get('trader_id')
    pair = data.get('pair')

    if not is_user_verified(trader_id):
        return jsonify({'status': 'error', 'message': 'Access Denied'}), 403

    signal = analyze_pair(pair)
    if signal:
        return jsonify({'status': 'success', 'signal': signal})
    else:
        return jsonify({'status': 'none', 'message': 'No signal at the moment.'})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
