import json
from flask import Flask, request, jsonify, send_from_directory
from bot import bot, process_update, db_ref, update_balance

app = Flask(__name__, static_folder='../public', static_url_path='')

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        data = request.get_data().decode('utf-8')
        process_update(json.loads(data))
        return ''
    return 'Bad request', 400

@app.route('/api/get_user', methods=['GET'])
def get_user_data():
    tg_id = request.args.get('tg_id')
    if not tg_id:
        return jsonify({'error': 'tg_id missing'}), 400
    user = db_ref.child(f'users/{tg_id}').get() or {}
    return jsonify(user)

@app.route('/api/add_points', methods=['POST'])
def add_points():
    data = request.json
    tg_id = data.get('tg_id')
    points = data.get('points')
    if not tg_id or points is None:
        return jsonify({'error': 'Invalid data'}), 400
    update_balance(tg_id, points)
    return jsonify({'success': True})

@app.route('/api/update_task', methods=['POST'])
def update_task():
    data = request.json
    tg_id = data.get('tg_id')
    task = data.get('task')
    completed = data.get('completed')
    if not tg_id or not task:
        return jsonify({'error': 'Missing fields'}), 400
    db_ref.child(f'users/{tg_id}/tasks/{task}').set(completed)
    return jsonify({'success': True})

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
