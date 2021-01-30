import os
from functools import wraps
import json
import shutil
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, send_file
from flask_cors import cross_origin
import pandas as pd

app = Flask(__name__)
app.secret_key = 'os.urandom(24)'

bucket_url = 'https://storage.googleapis.com/enagage-invites.appspot.com'

password = "I3253aAd%Btw"

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': 'enagage-invites', 'storageBucket': 'enagage-invites.appspot.com'
})

bucket = storage.bucket()
db = firestore.client()

games = ['image_puzzle', 'image_quiz',
         'memory_match', 'creative_page', 'image_trivia', 'crossword', 'hashtag']


def get_bucket_link(game_id, filename):
    return f'{bucket_url}/{game_id}/{filename}.png'


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin' in session:
            return f(*args, **kwargs)
        else:
            return redirect(('/'))
    return wrap


@app.route('/')
def index():
    try:
        if session['admin']:
            return redirect('/manage_sessions')
    except Exception:
        pass
    return render_template('index.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect('/')


@app.route('/', methods=['POST'])
def login():
    if request.form['password'] == password:
        session['admin'] = True
        return redirect('/manage_sessions')
    else:
        flash('Invalid credentials')
        return redirect('/')


@app.route('/create_sessions', methods=['GET'])
@login_required
def create_session_view():
    return render_template('create_session.html', games=games)


@app.route('/create_session', methods=['POST'])
@login_required
def create_session():
    formData = json.loads(request.data)
    formData['id'] = formData['sessionName']
    formData['loginBackground'] = get_bucket_link(
        formData['id'], formData['loginBackground'].strip())
    formData['logoImg'] = get_bucket_link(
        formData['id'], formData['logoImg'].strip())
    formData['loginCreative'] = get_bucket_link(
        formData['id'], formData['loginCreative'].strip())
    formData['endCreative'] = get_bucket_link(
        formData['id'], formData['endCreative'].strip())
    formData['endDownloadCreative'] = f'{bucket_url}/{formData["id"]}/{formData["endDownloadCreative"]}'
    formData['endBackground'] = get_bucket_link(
        formData['id'], formData['endBackground'].strip())
    temp = []
    for g in formData['gamesAdded']:
        temp.append(db.collection('games').document(g).get().to_dict())
    formData['gamesData'] = temp
    formData['loadingSpinner'] = f'{bucket_url}/{formData["id"]}/{formData["loadingSpinner"]}'
    formData['gameSound'] = f'{bucket_url}/{formData["id"]}/{formData["gameSound"]}'
    formData['active'] = True
    db.collection('sessions').document(formData['id']).set(formData)
    return {'status': 'success'}


@app.route('/hydrate/<session_id>')
@login_required
def hydrate_session(session_id):
    formData = db.collection('sessions').document(session_id).get().to_dict()
    temp = []
    for g in formData['gamesAdded']:
        temp.append(db.collection('games').document(g).get().to_dict())
    formData['gamesData'] = temp
    db.collection('sessions').document(formData['id']).set(formData)
    flash(f'{session_id} hydrated sucessfully', category='alert-info')
    return redirect('/manage_sessions')


@app.route('/download/<session_id>')
@login_required
def download_session(session_id):
    shutil.rmtree('/tmp/reports/', ignore_errors=True)
    ids = [i.to_dict() for i in db.collection(u'sessions').document(session_id).collection(
        'users').stream()]
    df = pd.DataFrame([[key['name'], key['rsvp'], key['feedback']]for key in ids], columns=[
                      'name', 'rsvp', 'feedback'])
    os.mkdir('/tmp/reports')
    df.to_csv(
        f'/tmp/reports/{session_id}-time-{int(datetime.now().timestamp())}.csv', encoding='utf-8')
    return send_file(f'/tmp/reports/{session_id}-time-{int(datetime.now().timestamp())}.csv', attachment_filename=f'{session_id}-{int(datetime.now().timestamp())}.csv', cache_timeout=-1, as_attachment=True)


@app.route('/status/<session_id>')
@login_required
def toggle_session(session_id):
    formData = db.collection('sessions').document(session_id).get().to_dict()
    formData['active'] = not formData['active']
    db.collection('sessions').document(formData['id']).set(formData)
    flash(
        f'{session_id} toggled active to {formData["active"]} sucessfully', category='alert-info')
    return redirect('/manage_sessions')


@app.route('/manage_sessions')
@login_required
def manage_session_view():
    sessionInfo = [i.to_dict() for i in db.collection(
        'sessions').stream()]
    return render_template('manage_session.html', sessionInfo=sessionInfo)


@app.route('/game/image_puzzle', methods=['GET'])
@login_required
def create_image_puzzle_view():
    return render_template('games/image_puzzle.html')


@app.route('/game/image_puzzle', methods=['POST'])
@login_required
def create_image_puzzle():
    formData = request.form.to_dict()
    if len(formData['gameName']) < 3:
        flash('Game name too small', category='alert-danger')
        return redirect('/game/image_puzzle')
    if not formData['img'].strip() or ' ' in formData['img']:
        flash('Image name should not contain spaces', category='alert-danger')
        return redirect('/game/image_puzzle')
    formData['id'] = f'image_puzzle-{formData["gameName"].strip()}'
    formData['img'] = get_bucket_link(formData['id'], formData['img'].strip())
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['hintImg'] = get_bucket_link(
        formData['id'], formData['hintImg'].strip())
    formData['borderImg'] = get_bucket_link(
        formData['id'], formData['borderImg'].strip())
    formData['type'] = 'image_puzzle'
    formData['emojiList'] = formData['emojiList'].split(',')
    db.collection('games').document(formData['id']).set(formData)
    flash(f'Created game {formData["id"]}', category='alert-info')
    flash('Upload images for '+formData['id'], category='alert-warning')
    return redirect('/')


@app.route('/game/image_quiz', methods=['GET'])
@login_required
def create_image_quiz_view():
    return render_template('games/image_quiz.html')


@app.route('/game/image_quiz', methods=['POST'])
@login_required
def create_image_quiz():
    formData = json.loads(request.data)
    if len(formData['gameName']) < 3:
        flash('Game name too small', category='alert-danger')
        return {'status': 'error'}
    if not formData['img'].strip() or ' ' in formData['img']:
        flash('Image name should not contain spaces', category='alert-danger')
        return {'status': 'error'}
    formData['id'] = f'image_quiz-{formData["gameName"].strip()}'
    formData['img'] = get_bucket_link(formData['id'], formData['img'].strip())
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    formData['hintImg'] = get_bucket_link(
        formData['id'], formData['hintImg'].strip())
    formData['backImg'] = get_bucket_link(
        formData['id'], formData['backImg'].strip())
    formData['optionsBackImg'] = get_bucket_link(
        formData['id'], formData['optionsBackImg'].strip())
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['borderImg'] = get_bucket_link(
        formData['id'], formData['borderImg'].strip())
    formData['type'] = 'image_quiz'
    formData['emojiList'] = formData['emojiList'].split(',')
    db.collection('games').document(formData['id']).set(formData)
    flash(f'Created game {formData["id"]}', category='alert-info')
    flash('Upload images for '+formData['id'], category='alert-warning')
    return {'status': 'success'}


@app.route('/game/image_trivia', methods=['GET'])
@login_required
def create_image_trivia_view():
    return render_template('games/image_trivia.html')


@app.route('/game/image_trivia', methods=['POST'])
@login_required
def create_image_trivia():
    formData = json.loads(request.data)
    if len(formData['gameName']) < 3:
        flash('Game name too small', category='alert-danger')
        return {'status': 'error'}
    formData['id'] = f'image_trivia-{formData["gameName"].strip()}'
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    for i in range(len(formData['levels'])):
        formData['levels'][i]['images'] = [get_bucket_link(
            formData['id'], u) for u in formData['levels'][i]['images']]
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['hintImg'] = get_bucket_link(
        formData['id'], formData['hintImg'].strip())
    formData['type'] = 'image_trivia'
    formData['emojiList'] = formData['emojiList'].split(',')
    db.collection('games').document(formData['id']).set(formData)
    flash(f'Created game {formData["id"]}', category='alert-info')
    flash('Upload images for '+formData['id'], category='alert-warning')
    return {'status': 'success'}


@app.route('/game/memory_match', methods=['GET'])
@login_required
def create_memory_match_view():
    return render_template('games/memory_match.html')


@app.route('/game/memory_match', methods=['POST'])
@login_required
def create_memory_match():
    formData = request.form.to_dict()
    if len(formData['gameName']) < 3:
        flash('Game name too small', category='alert-danger')
        return redirect('/game/memory_match')
    if not formData['titleImg'].strip() or ' ' in formData['titleImg']:
        flash('Image name should not contain spaces', category='alert-danger')
    if not formData['bgImg'].strip() or ' ' in formData['bgImg']:
        flash('Image name should not contain spaces', category='alert-danger')
        return redirect('/game/memory_match')
    formData['id'] = f'memory_match-{formData["gameName"].strip()}'
    formData['hintImg'] = get_bucket_link(
        formData['id'], formData['hintImg'].strip())
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['backImg'] = get_bucket_link(
        formData['id'], formData['backImg'].strip())
    formData['type'] = 'memory_match'
    for k in formData.keys():
        if 'pair' in k:
            if not formData[k].strip() or ' ' in formData[k]:
                flash('Image name should not contain spaces',
                      category='alert-danger')
                return redirect('/game/memory_match')
            formData[k] = get_bucket_link(
                formData['id'], formData[k].strip())
    formData['emojiList'] = formData['emojiList'].split(',')
    db.collection('games').document(formData['id']).set(formData)
    flash(f'Created game {formData["id"]}', category='alert-info')
    flash('Upload images for '+formData['id'], category='alert-warning')
    return redirect('/manage_sessions')


@app.route('/game/creative_page', methods=['GET'])
@login_required
def create_creative_page_view():
    return render_template('games/creative_page.html')


@app.route('/game/creative_page', methods=['POST'])
@login_required
def create_creative_page():

    formData = request.form.to_dict()
    formData['id'] = 'creative_page-'+formData['name']
    formData['type'] = 'creative_page'
    for k in formData.keys():
        print(k)
        if not formData[k].strip() or ' ' in formData[k].strip():
            flash(f'{k} cannot contain spaces', category='alert-danger')
            return redirect('/game/creative_page')
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    if formData['primaryMediaType'] == 'img':
        formData['primaryMediaUrl'] = get_bucket_link(
            formData['id'], formData['primaryMediaUrl'].strip())
    if formData['secondaryImg'].strip():
        formData['secondaryImg'] = get_bucket_link(
            formData['id'], formData['secondaryImg'].strip())
    db.collection('games').document(formData['id']).set(formData)
    flash('Upload images for '+formData['id'], category='alert-warning')
    return redirect('/game/creative_page')


@app.route('/game/crossword', methods=['GET'])
@login_required
def create_crossword_view():
    return render_template('games/crossword.html')


@app.route('/game/crossword', methods=['POST'])
@login_required
def create_crossword():

    formData = json.loads(request.data)
    print(formData)
    formData['id'] = 'crossword-'+formData['gameName']
    formData['type'] = 'crossword'
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    formData['hintImg'] = get_bucket_link(
        formData['id'], formData['hintImg'].strip())
    formData['emojiList'] = formData['emojiList'].split(',')
    db.collection('games').document(formData['id']).set(formData)
    flash(f'Created game {formData["id"]}', category='alert-info')
    flash('Upload images for '+formData['id'], category='alert-warning')
    return {'status': 'success'}


@app.route('/game/hashtag', methods=['GET'])
@login_required
def create_hashtag_view():
    return render_template('games/hashtag.html')


@app.route('/game/hashtag', methods=['POST'])
@login_required
def create_hashtag():

    formData = json.loads(request.data)
    print(formData)
    formData['id'] = 'hashtag-'+formData['gameName']
    formData['type'] = 'hashtag'
    formData['titleImg'] = get_bucket_link(
        formData['id'], formData['titleImg'].strip())
    formData['bgImg'] = get_bucket_link(
        formData['id'], formData['bgImg'].strip())
    formData['hintImg'] = get_bucket_link(
        formData['id'], formData['hintImg'].strip())
    db.collection('games').document(formData['id']).set(formData)
    formData['emojiList'] = formData['emojiList'].split(',')
    flash(f'Created game {formData["id"]}', category='alert-info')
    flash('Upload images for '+formData['id'], category='alert-warning')
    return {'status': 'success'}


@app.route('/upload', methods=['GET'])
@login_required
def upload_view():
    return render_template('upload.html', games=games)


@app.route('/upload', methods=['POST'])
@login_required
def upload_files():
    files = request.files.getlist('files')
    name = request.form['gameName']
    if name == '':
        flash('Select a game', category='alert-danger')
        return redirect('/upload')

    for f in files:
        blob = bucket.blob(f'{name}/{f.filename}')
        blob.upload_from_file(f)
    flash(f'uploaded {len(files)} files for game {name}',
          category='alert-info')
    return redirect('/upload')


@app.route('/delete', methods=['GET'])
@login_required
def delete_view():
    return render_template('delete.html', games=games)


@app.route('/delete', methods=['POST'])
@login_required
def delete_files():
    name = request.form['gameName']
    game = request.form['gameType']
    if name == '':
        flash('Select a game', category='alert-danger')
        return redirect('/delete')
    if game != 'sessions':
        db.collection(
            'games').document(name).delete()
    else:
        db.collection(
            'sessions').document(name).delete()
    for blob in bucket.list_blobs(prefix=name):
        blob.delete()
    flash(f'deleted game {name}',
          category='alert-info')
    return redirect('/delete')


@app.route('/api/<session_id>')
@cross_origin()
def get_session(session_id):
    res = db.collection('sessions').document(session_id).get().to_dict()
    if res['active']:
        return res
    return {'error': 'invalid session id'}


@app.route('/api/<session_id>', methods=['POST'])
@cross_origin()
def set_score(session_id):
    formData = json.loads(request.data)
    db.collection('sessions').document(
        session_id).collection('users').document(formData['name']).set(formData)
    return {'result': 'sucess'}


@app.route('/list/<game>')
def get_game_list(game):
    if game != 'sessions':
        gamesInfo = [i.to_dict()['id'] for i in db.collection(
            'games').where(u'type', '==', game).stream()]
    else:
        gamesInfo = [i.to_dict()['id'] for i in db.collection(
            'sessions').stream()]
    return {'games': gamesInfo}


@app.route('/test')
def tt():
    return render_template('test.html')


if __name__ == "__main__":
    app.secret_key = 'os.urandom(24)'
    app.run(host='127.0.0.1', port=8081, debug=True)
