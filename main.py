#!/usr/bin/python3

from flask import Flask, escape, request, json, redirect, url_for, render_template#, flash
import os
import sys
import urllib.request
import json
import re
from pymongo import MongoClient
import bson
import urllib.parse
from urllib.parse import urlencode
import base64
import json as pythonjson
import requests
from urllib.parse import urlencode
import spotipy

from spotipy.oauth2 import SpotifyClientCredentials
from pymongo import MongoClient

import datetime

app = Flask(__name__)

# Form imports
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

#import musicbrainzngs

API_KEY = '' # API for lastfm
CLIENT_ID = '' # SPOTIFY client ID
CLIENT_SECRET = '' # Spotify client secret

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

CLIENT_SIDE_URL = "cruzhacks-2020-uniaux.appspot.com"
PORT = 443
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
SCOPE = "playlist-modify-public playlist-modify-private"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}

#REFRESH_URL = "https://accounts.spotify.com/api/token"


app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SECRET_KEY'] = SECRET_KEY
# app.config.from_object(Config)

def get_recent_api_url(username):
    return 'https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={}&api_key={}&format=json'.format(username, API_KEY)

def get_artist_api_url(artist, username):
    artist_no_space = artist.replace(' ', '+')
    return 'http://ws.audioscrobbler.com/2.0/?method=artist.getInfo&api_key={}&autocorrect=1&artist={}&user={}&format=json'.format(API_KEY, artist_no_space,username)

def get_top_songs_for_tag_url(tag, limit):
    tag_no_space = tag.replace(' ', '+')
    return 'http://ws.audioscrobbler.com/2.0/?method=tag.gettoptracks&api_key={}&limit={}&tag={}&format=json'.format(API_KEY, limit,tag_no_space)

def do_api_call(api_url):
    with urllib.request.urlopen(api_url) as url:
        data = json.loads(url.read().decode())
        return data

def get_recent_tracks_by_user(username):
    api_url = get_recent_api_url(username)
    json_data = do_api_call(api_url)
    json_tracks = json_data['recenttracks']['track']
    return json_tracks

def get_tags_from_artist(artist_json):
    artist_name = artist_json['artist']['name']
    tags_data = artist_json['artist']['tags']['tag']
    artist_tags = {artist_name: []}
    #print(artist_name, end=": ")
    for j in range(0, len(tags_data)):
        artist_tags[artist_name].append(tags_data[j]['name'])
        #print(tags_data[j]['name'], end='')
        #if j < len(tags_data) - 1:
        #    print(', ', end='')
    #print()
    return artist_tags

def get_genres_for_top_artists_by_user(username):
    json_tracks = get_recent_tracks_by_user(username)
    #print(json_tracks)
    num_tracks = len(json_tracks)
    artists_with_tags = list()
    for i in range(0, num_tracks):
        song_artist_name = json_tracks[i]['artist']['#text']
        #print(song_artist_name)
        try:
            artist_api_url = get_artist_api_url(song_artist_name, username)
            #print(artist_api_url)
            json_artist_data = do_api_call(artist_api_url)
            artists_with_tags.append(get_tags_from_artist(json_artist_data))
        except Exception as e:
            print(e)
    return artists_with_tags

def return_artist_list_dict_as_str(artist_with_tags):
    string_return = ''
    for artist_tag in artist_with_tags:
        #print(artist_tag)
        for key,val in artist_tag.items():
            string_return += key + ": " + str(val) + "<br>"
            #print(key + ": " + str(val))
            #print(key)
    return string_return[:-2]

def count_tags(total_artist_data):
    aggregate_tags = dict()
    for entry in total_artist_data:
        for artist in entry:
            tags = artist[list(artist.keys())[0]]
            for tag in tags:
                tag_normalized = re.sub('[^A-Za-z0-9]+', '', tag).lower()
                if tag_normalized in aggregate_tags:
                    aggregate_tags[tag_normalized]['count'] = aggregate_tags[tag_normalized]['count'] + 1
                else:
                    tag_data = dict()
                    tag_data['tag_name'] = tag
                    tag_data['count'] = 1
                    aggregate_tags[tag_normalized] = tag_data
                #print(tag_normalized, end=' ')
            #print(str(tags))
            #print()
    sorted_agr_tags = list(reversed(sorted(aggregate_tags, key=lambda x: (aggregate_tags[x]['count']))))
    cutoff = aggregate_tags[sorted_agr_tags[0]]['count'] * 0.05
    total_tags_saved = 0
    tags_to_save = dict()
    for tag in sorted_agr_tags:
        if aggregate_tags[tag]['count'] > cutoff:
            total_tags_saved += aggregate_tags[tag]['count']
            tags_to_save[aggregate_tags[tag]['tag_name']] =  aggregate_tags[tag]['count']
    for tag in tags_to_save:
        curr_tag_count = int(tags_to_save[tag])
        tags_to_save[tag] = curr_tag_count/total_tags_saved
    #print(str(tags_to_save))
    return tags_to_save

    #print(str(aggregate_tags.items()))

def add_to_db(dict_to_add):
    client = MongoClient("mongodb+srv://vinay:cruzhacks2020@uniaux-jx8gt.gcp.mongodb.net/Playlists?retryWrites=true&w=majority")
    db = client.Playlists
    uniaux = db.Uniaux
    #song_entry = dict()
    #song_entry[artist] = title
    db_id = uniaux.insert_one(dict_to_add).inserted_id
    #serverStatusResult=db.command("serverStatus")
    print(db_id)
    return db_id

def get_songs_by_ratio(tags_with_ratios):
    song_num = 0
    db_songs = dict()
    for key in tags_with_ratios:
        limit = round(100*tags_with_ratios[key])
        url = get_top_songs_for_tag_url(key, limit)
        res = do_api_call(url)
        tracks = res['tracks']['track']
        for track in tracks:
            song_info = dict()
            song_info['artist'] = track['artist']['name']
            song_info['title'] = track['name']
            db_songs[str(song_num)] = song_info
            #print(track['name'] + '\tby\t' + track['artist']['name'])
            song_num+=1
    db_id = add_to_db(db_songs)
    #print(url)
    #print(str(res))
    return db_id

def search_songs(playlist_id, access_token):
    client = MongoClient("mongodb+srv://vinay:<password>@@uniaux-jx8gt.gcp.mongodb.net/Playlists?retryWrites=true&w=majority")
    db = client.Playlists
    uniaux = db.Uniaux

    o_id = bson.ObjectId(playlist_id)
    all_songs = uniaux.find_one({"_id": o_id})
    song_ids = list()
    for song in all_songs:
        if '_id' in song:
            continue
        artist = all_songs[song]['artist']
        title = all_songs[song]['title']
        curr_id = search_song(access_token, title, artist)
        if curr_id is not None:
            song_ids.append(curr_id)
    #for song_i in song_ids:
    #    print(song_i)
    return song_ids
        


def search_song(access_token, track, artist):
    url_end = "track:{} artist:{}".format(track, artist)
    url = "{}/search?q={}{}".format(SPOTIFY_API_URL, urllib.parse.quote(url_end), '&type=track&limit=1')
    req = urllib.request.Request(url)
    req.add_header('Accept', "Application/json")
    req.add_header('Content-Type', "Application/json")
    req.add_header('Authorization', "Bearer {}".format(access_token))
    with urllib.request.urlopen(req) as response:
        try:
            the_page = response.read()
            search_data = json.loads(the_page)
            return search_data['tracks']['items'][0]['id']
        except:
            print("Unable to find song")

def create_playlist(playlist_name, access_token):
    url = "{}/me".format(SPOTIFY_API_URL)
    req = urllib.request.Request(url)
    req.add_header('Authorization', "Bearer {}".format(access_token))
    with urllib.request.urlopen(req) as response:
        the_page = response.read()
        user_data = json.loads(the_page)
        user_id = user_data['id']

    print(user_id)
    print(access_token)
    
    url = "{}/users/{}/playlists".format(SPOTIFY_API_URL, user_id)
    auth_key = 'Bearer {}'.format(access_token)
    headers = {
        'Authorization': auth_key,
        'Content-Type': 'application/json',
    }

    data = dict()
    #data['name'] = playlist_name
    #today = date.today()
    mydate = datetime.datetime.now()
    month = mydate.strftime("%B")
    date = datetime.datetime.today().day
    data['name'] = month + " " + str(date)
    data['public'] = 'true'
    
    #print(pythonjson.dumps(data))
    response = requests.post('https://api.spotify.com/v1/users/{}/playlists'.format(user_id), headers=headers, data=pythonjson.dumps(data))

    playlist_real_id = response.json()['id']
    print(playlist_real_id)

    return playlist_real_id, user_id

def make_playlist(access_token, tracks, playlist_id):
    full_song_ids = list()
    for track in tracks:
        full_song_id = "spotify:track:{}".format(track)
        #full_song_id_san = urllib.parse.quote_plus(full_song_id)
        full_song_ids.append(full_song_id)
    
    for i in full_song_ids:
        print(i)
    
    
    #print(full_song_id)
    #san_song_id = urllib.parse.quote_plus(full_song_id)
    #print(san_song_id)
    url = "{}/playlists/{}/tracks".format(SPOTIFY_API_URL, playlist_id)
    #url = "{}/playlists/{}/tracks?uris={}".format(SPOTIFY_API_URL, playlist_real_id, san_song_id)

    print(url)
    req = urllib.request.Request(url)
    auth_key = 'Bearer {}'.format(access_token)
    #headers = dict()
    #headers['Authorization'] = auth_key
    #headers['Accept'] = 'application/json'
    #headers = {
    #    'Authorization': auth_key,
    #    'Content-Type': 'application/json'
    #}

    #headers = {
    #    'Accept': 'application/json',
    #    'Content-Type': 'application/json',
    #    'Authorization': 'Bearer 
    #}

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': auth_key,
    }

    #body = pythonjson.dumps(full_song_ids)
    body_to_send = dict()
    body_to_send['uris'] = full_song_ids
    #print(str(body_to_send))

    #params = (
    #    ('uris', full_song_id),
    #)
    #print(headers)
    json_body = pythonjson.dumps(body_to_send)
    print(str(json_body))
    
    response = requests.post(url, headers=headers, data=str(json_body))

    print(str(response.json()))
    return
    #print(str(pythonjson.load(response)))
    


@app.route('/')
def spotify_login():
    scopes = 'user-read-private user-read-email playlist-read-private playlist-modify-private playlist-modify-public'
    callback_url = 'https://cruzhacks-2020-uniaux.appspot.com/callback'
    #callback_url = 'http://localhost:5000/callback'
    redir_url = 'https://accounts.spotify.com/authorize?response_type=code&client_id={}&scope={}&redirect_uri={}'.format(CLIENT_ID,scopes,callback_url)
    return redirect(redir_url, code=302)

@app.route('/callback')
def callback():
    print(repr(request.args))
    print("callback received")
    spotify_code = request.args.get('code')
    #print()
    #print(spotify_code)
    #print()

    form = dict()
    form['grant_type'] = 'authorization_code'
    form['code'] = spotify_code

    #scopes = 'user-read-private user-read-email'
    callback_url = 'https://cruzhacks-2020-uniaux.appspot.com/callback'
    #callback_url = 'http://localhost:5000/callback'
    #redir_url = 'https://accounts.spotify.com/authorize?response_type=code&client_id={}&scope={}&redirect_uri={}'.format(CLIENT_ID,scopes,callback_url)

    #form['redirect_uri'] = redir_url
    form['redirect_uri'] = callback_url

    form['client_id'] = CLIENT_ID
    form['client_secret'] = CLIENT_SECRET

    data = urllib.parse.urlencode(form).encode()
    #print()
    #print()
    #print(str(data))
    #print()
    req =  urllib.request.Request(SPOTIFY_TOKEN_URL, data=data) # this will make the method "POST"
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    #client_sec = "{}:{}".format(CLIENT_ID, CLIENT_SECRET)
    #
    #b64_client = base64.b64encode(client_sec.encode())
    #
    #req.add_header("Authorization", "Basic {}".format(b64_client))
    resp = urllib.request.urlopen(req)
    access_token = pythonjson.load(resp)['access_token']
    #access_token = pythonjson.load(resp)['access_token']
    print(access_token)
    #make_playlist(access_token, "Come Together", "The Beatles", "hell_ya")
    redir_url = "{}?auth={}".format(url_for('main'), access_token)
    #return redirect(url_for('main'))
    return redirect(redir_url)
    
def get_db_id(usernames):
    artist_genre = list()
    for un in usernames:
        print(un)
        artists_with_tags = get_genres_for_top_artists_by_user(un)
        #str_artists = return_artist_list_dict_as_str(artists_with_tags)
        #print(str(artists_with_tags))
        artist_genre.append(artists_with_tags)
    tags_with_ratios = count_tags(artist_genre)
    db_id = get_songs_by_ratio(tags_with_ratios)
    return str(db_id)


@app.route('/api', methods=['POST'])
def process_post():
    json_post = request.get_json()
    username_list = json_post['usernames']
    spotify_api = json_post['spotify']
    #for un in username_list:
    #    print(un, end=' ')
    #print(spotify_api)
    artist_genre = list()
    for un in username_list:
        print(un)
        artists_with_tags = get_genres_for_top_artists_by_user(un)
        #str_artists = return_artist_list_dict_as_str(artists_with_tags)
        #print(str(artists_with_tags))
        artist_genre.append(artists_with_tags)
    #for entry in artist_genre:
        #print(str(entry))
        #print()
        #print()
    tags_with_ratios = count_tags(artist_genre)
    db_id = get_songs_by_ratio(tags_with_ratios)
    data = dict()
    data['id'] = str(db_id)
    response = app.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json'
    )
    print("About to return some data from the post to /api")
    #return "200: " + str(db_id) + "\n"
    #return response
    return str(db_id)

@app.route('/getapi')
def process():
    #username = 'sseproboss'
    username1 = request.args.get('username')
    username2 = request.args.get('username2')
    artists_with_tags = get_genres_for_top_artists_by_user(username1)
    str_artists = return_artist_list_dict_as_str(artists_with_tags)
    artists_with_tags2 = get_genres_for_top_artists_by_user(username2)
    str_art2 = return_artist_list_dict_as_str(artists_with_tags2)
    return username1 + '<br>' + str_artists + '<br>' + username2 + '<br>' + str_art2

class UsernameForm(FlaskForm):
    usernames = StringField('Username', validators=[DataRequired(), Length(min=2, max=202)])
    @app.route('/home', methods=['POST', 'GET'])
    def main():
        #form = UsernameForm()
        auth_key = request.args.get('auth')
        print("Main auth key received " + auth_key)
        if request.method == 'POST':
            # Grab username from form
            usernames = request.form.get('user') # Confirmed usernames is correct
            # Create header for JSON
            headers = {
                'Content-Type': 'application/json',
            }
            # Parse usernames
            usernames = usernames.replace(" ", "")
            username_list = usernames.split(',')
            # Create dict for usernames
            #data_dict = dict()
            #data_dict['usernames'] = username_list
            #data_dict['spotify'] = ""
            #data = '{"usernames": ["user", "name"], "spotify": ""}'
            #data = pythonjson.dumps(data_dict)
            # Post
            #response = requests.post('https://cruzhacks-2020-uniaux.appspot.com/api', headers=headers, data=data)
            db_id = get_db_id(username_list)
            print("Response json has been received")
            #db_id=response.json()['id']
            print("About to print the db_id")
            print("DB ID is " + db_id)
            song_ids = search_songs(db_id, auth_key) # Get the Spotify ids for the songs
            print(str(song_ids))
            spotify_playlist_id, user_id = create_playlist(db_id, auth_key) # Create an empty spotify playlist
            print(str(spotify_playlist_id))
            make_playlist(auth_key, song_ids, spotify_playlist_id) # Populate the playlist
            playlist_url = "https://open.spotify.com/user/{}/playlist/{}".format(user_id, spotify_playlist_id)

            # flash('Creating playlist for {usernames}!', 'success')
            # Create redir url
            #redir_url = "{}?auth={}&users={}".format(url_for('/api'), auth_key, usernames)
            #return redirect("spotify.com")
            return redirect(playlist_url)
        
        #curl -X POST -H "Content-Type: application/json" -d '{"usernames": ["user", "name"], "spotify": ""}'
        
        #redir_url = "{}?auth={}".format(url_for('main'), auth_key)
        return render_template('home.html', title='UniAux')
        #return redirect(redir_url)

if __name__ == '__main__':
    #username = sys.argv[1]
    app.run(host='0.0.0.0', port=5000, debug=True)
    #print(json_data['recenttracks']['track'][0])
    #print(api_url)
    #playlist_id = ''
    #auth_token = '---'
    #song_ids = search_songs(playlist_id, auth_token)
    #spotify_playlist_id = create_playlist(playlist_id, auth_token)
    #make_playlist(auth_token, song_ids, spotify_playlist_id)
