#!/usr/bin/env python
# coding: utf-8

# ## Import libraries

# In[1]:


import pandas as pd
import numpy as np
import os, json, logging, threading
from requests import get, post
from time import time, sleep
from random import randint
from bs4 import BeautifulSoup
global stop_thread
stop_thread = "1"

# initialize log settings for error
logging.basicConfig(filename="error.log", level=logging.INFO)


# ## Obtain token and prepare headers to access Spotify's APIs.

# In[2]:


# post Client Credentials to Spotify's Token API to obtain Token
with open("./token/token.json", "r") as token_file:
    token_file = json.load(token_file)
res = post('https://accounts.spotify.com/api/token', headers = {'Authorization': '{}'.format(token_file["token"])}, data= {'grant_type': 'client_credentials'})
token = 'Bearer {}'.format(res.json()['access_token'])

# define headers to include Token
headers = {'Authorization': token, "Accept": 'application/json', 'Content-Type': "application/json"}


# ## Function that tracks progress of specified task.

# In[3]:

class Scraper():
    def __init__(self):
        self.task = ""
        self.value = 0
        self.max = 0
    def track_progress(self, task, step, num, i, start_time):
        """
        Function that helps track progress of specified task.
        Args:
            task: the task to track
            step: the increment between each for loop
            num: number of songs to track
            i: current iteration of the loop
            start_time: time to start tracking from
        """
        self.task = task
        self.value = i+step
        self.max = num
        try:
            print("{}: [{}{}] {}/{} songs completed. Approx time left: {} minutes.".format(task, "#"*round(((i+step)/(num/20))), "-"*round((num/(num/20)-((i+step)/(num/20)))), i+step, num, round(((time()-start_time)/i)*(num-i)/60, 2)), end="\r", flush=True)
        except:
            print("{}: [{}{}] {}/{} songs completed. Approx time left: {}".format(task, "#"*round(((i+step)/(num/20))), "-"*round((num/(num/20)-((i+step)/(num/20)))), i+step, num, "-"), end="\r", flush=True)


    # ## Function that extracts basic info of songs from specified year (name, id, popularity, release date) and stores them in dataframe songs_info.
    # 
    # approx. 5secs per 50 songs

    # In[4]:


    def extract_songs(self, year, num):
        """
        Function to extract specified number of songs from a specified year.
        Args:
            year: year to extract songs from
            num: number of songs to extract
        """
        global stop_thread
        # for songs released in specified year, create data frame for songs' basic info
        songs_info = pd.DataFrame(columns=["name", "id", "popularity", "release_date"])

        # set start_time and songs_extracted to track progress
        start_time = time()
        songs_extracted = 0

        # from Spotify API, get songs and basic info released in specified year, in batches of 50, with rate limit of 1-3 secs between batches
        # maximum songs per year is 10k
        for i in range(0, num, 50):
            url="https://api.spotify.com/v1/search?q=%20year:{}&limit=50&offset={}&type=track".format(year, i)
            r=get(url, headers=headers)
            
            # to ensure response contains track details, which is not the case sometimes
            while "tracks" not in r.json():
                r=get(url, headers=headers)

            for item in r.json()["tracks"]["items"]:
                songs_info = songs_info.append({"name": item["name"], "id": item["id"], "popularity": item["popularity"],
                                               "release_date": item["album"]["release_date"]}, ignore_index = True)
            
            # track progress
            self.track_progress("Extracting songs", 50, num, i, start_time)

            sleep(randint(1,3))
            songs_extracted = i + 50

            if stop_thread == "0":
                break

        print("")
        print("EXTRACTION COMPLETE. Songs extracted: {}; Elapsed Time: {} minutes.".format(songs_extracted, round((time()-start_time)/60, 2)))
        return songs_info
        


    # ## Function that labels data with hit/miss and balance datasets.

    # In[5]:


    def label_songs(self, songs_info, year):
        """
        Function to label songs with hit/miss.
        Args:
            songs_info: dataframe containing songs' basic info
        """
        # number of songs to label
        global stop_thread
        num = len(songs_info["popularity"])
        
        # using cutoff_popularity, classify songs as hit or miss using hit_miss list, then add hit_miss list to DataFrame
        hit_miss = []
        hit_count = 0
        
        # set start_time and songs_labeled to track progress
        start_time = time()
        songs_labeled = 0

        for i in range(num):

            if songs_info["popularity"][i] >= 70:
                hit_count += 1
                hit_miss.append("hit")

            else:
                hit_miss.append("miss")
                
            # track progress
            self.track_progress("Labeling songs", 1, num, i, start_time)
                
            songs_labeled = i + 1

            if stop_thread == "0":
                break
        
        print("")
        print("LABELING COMPLETE. Songs labeled: {}; Elapsed Time: {} minutes.".format(songs_labeled, round((time()-start_time)/60, 2)))
        
        songs_info["hit_miss"] = hit_miss
                
        if hit_count < len(songs_info["popularity"])/2:
            drop_count = len(songs_info["popularity"]) - 2*hit_count
            songs_info = songs_info.drop(songs_info[songs_info["hit_miss"]=="miss"].sample(n=drop_count).index)
            songs_info = songs_info.reset_index(drop=True)
            
        # save temp song list in case analysis later fails
        songs_info.to_csv("./temp/{}_{}_song_list.csv".format(year, num), index=False)

        return songs_info


    # ## On songs extracted, conduct audio analysis (e.g. duration, loudness, tempo etc.), stored in dataframe songs_analysis.
    # 
    # approx. 3mins per 10 songs

    # In[6]:


    def audio_analysis(self, songs_info, year, half_analyzed):
        """
        Function to conduct audio analysis on extracted songs.
        Args:
            songs_info: dataframe containing songs' basic info
            half_analyzed: determines number of pre-analyzed songs if applicable
        """
        # number of songs for audio analysis
        global stop_thread
        num = len(songs_info["hit_miss"])
        
        # create data frame for songs' audio analysis
        songs_analysis = pd.DataFrame(columns=["duration", "loudness", "tempo", "tempo_confidence", "time_signature", 
                                                    "time_signature_confidence", "key", "key_confidence", "mode", "mode_confidence"])

        # set start_time and songs_analyzed to track progress
        start_time = time()
        songs_analyzed = 0
        
        # write headings for new file
        if half_analyzed == 0:
            with open("./temp/{}_temp_audio_analysis.csv".format(year), "w+") as file:
                file.write(",duration,loudness,tempo,tempo_confidence,time_signature,time_signature_confidence,key,key_confidence,mode,mode_confidence\n")

        # from Spotify API, get songs' audio analysis with rate limit of 1-2 secs between songs
        # maximum songs per year is 10k
        for i in range(num):
            url="https://api.spotify.com/v1/audio-analysis/{}".format(songs_info["id"][i])
            r=get(url, headers=headers)

            # to ensure response contains track details, which is not the case sometimes
            while "track" not in r.json():
                r=get(url, headers=headers)

            r=r.json()["track"]

            # track progress
            self.track_progress("Conducting audio analysis", 1, num, i, start_time)

            # write analyzed songs to temp file in case analysis fails halfway
            with open("./temp/{}_temp_audio_analysis.csv".format(year), "a") as file:
                file.write("{},{},{},{},{},{},{},{},{},{},{}\n".format(half_analyzed+i, r["duration"], r["loudness"], r["tempo"], r["tempo_confidence"], r["time_signature"], 
                                                                 r["time_signature_confidence"], r["key"],r["key_confidence"], r["mode"], r["mode_confidence"]))

            sleep(randint(1,2))
            songs_analyzed = i + 1

            if stop_thread == "0":
                break
            
        songs_analysis = pd.read_csv("./temp/{}_temp_audio_analysis.csv".format(year), index_col=0)

        print("")
        print("AUDIO ANALYSIS COMPLETE. Songs analyzed: {}; Elapsed Time: {} minutes.".format(songs_analyzed, round((time()-start_time)/60, 2)))
        return songs_analysis


    # ## On songs extracted, conduct audio feature analysis (e.g. acousticness, danceability, energy etc.), stored in dataframe songs_features.
    # 
    # approx. 15secs per 10 songs

    # In[7]:


    def features_analysis(self, songs_info, year, half_analyzed):
        """
        Function to conduct features analysis on extracted songs.
        Args:
            songs_info: dataframe containing songs' basic info
            half_analyzed: determines number of pre-analyzed songs if applicable
        """
        # number of songs for features analysis
        global stop_thread
        num = len(songs_info["hit_miss"])
        
        # create data frame for songs' audio analysis
        songs_features = pd.DataFrame(columns=["acousticness", "danceability", "energy", "instrumentalness", "liveness", 
                                                    "speechiness", "valence"])

        # set start_time and songs_analyzed to track progress
        start_time = time()
        songs_analyzed = 0
        
        # write headings for new file
        if half_analyzed == 0:
            with open("./temp/{}_temp_features_analysis.csv".format(year), "w+") as file:
                file.write(",acousticness,danceability,energy,instrumentalness,liveness,speechiness,valence\n")

        # get songs' audio features with rate limit of 1-2 secs between songs
        # maximum songs per year is 10k
        for i in range(num):
            url="https://api.spotify.com/v1/audio-features/{}".format(songs_info["id"][i])
            r=get(url, headers=headers)
            
            # to ensure response contains features details, which is not the case sometimes
            while "acousticness" not in r.json():
                r=get(url, headers=headers)

            r=r.json()

            # track progress
            self.track_progress("Conducting features analysis", 1, num, i, start_time)
            
            # write analyzed songs to temp file in case analysis fails halfway
            with open("./temp/{}_temp_features_analysis.csv".format(year), "a") as file:
                file.write("{},{},{},{},{},{},{},{}\n".format(half_analyzed+i, r["acousticness"], r["danceability"], r["energy"], r["instrumentalness"], r["liveness"], 
                                                                 r["speechiness"], r["valence"]))

            sleep(randint(1,2))
            songs_analyzed = i + 1

            if stop_thread == "0":
                break
            
        songs_features = pd.read_csv("./temp/{}_temp_features_analysis.csv".format(year), index_col=0)

        print("")
        print("FEATURES ANALYSIS COMPLETE. Songs analyzed: {}; Elapsed Time: {} minutes.".format(songs_analyzed, round((time()-start_time)/60, 2)))
        return songs_features


    # ## Link up above processes through a single function for easier management.

    # In[8]:


    def get_data(self, year, num, resume=[]):
        """
        Function that initiates entire process of extracting specified number of song data from specified year.
        Args:
            year: year to extract songs from
            num: number of songs to extract
            resume: list of year(s) to resume audio analysis from, defaults to an empty list
        """
        global stop_thread
        try:
            # check whether to execute a fresh start or resume for current year
            if year not in resume:
                print("Obtaining data from {}...".format(year))
                if stop_thread == "1":
                    # obtain data
                    songs_info = self.extract_songs(year, num)
                if stop_thread == "1":
                    # label songs
                    songs_info = self.label_songs(songs_info, year)
                if stop_thread == "1":
                    # audio analyze songs
                    songs_analysis = self.audio_analysis(songs_info, year, half_analyzed=0)
                if stop_thread == "1":
                    # features analyze songs
                    songs_features = self.features_analysis(songs_info, year, half_analyzed=0)
            # else:
            #     print("Resuming analysis from {}...".format(year))
            #     # read in song list
            #     song_list = pd.read_csv("./temp/{}_{}_song_list.csv".format(year, num))
            #     # read in half-analyzed audio data
            #     half_audio_analyzed_songs = pd.read_csv("./temp/{}_temp_audio_analysis.csv".format(year))
            #     songs_info = song_list.iloc[len(half_audio_analyzed_songs):]
            #     songs_info = songs_info.reset_index(drop=True)
            #     # audio analyze songs
            #     songs_analysis = self.audio_analysis(songs_info, year, half_analyzed=len(half_audio_analyzed_songs))
            #     if os.path.isfile("./temp/{}_temp_features_analysis.csv".format(year)):
            #         # read in half-analyzed features data
            #         half_features_analyzed_songs = pd.read_csv("./temp/{}_temp_features_analysis.csv".format(year))
            #         songs_info = song_list.iloc[len(half_features_analyzed_songs):]
            #         songs_info = songs_info.reset_index(drop=True)
            #         # features analyze songs
            #         songs_features = self.features_analysis(songs_info, year, half_analyzed=len(half_features_analyzed_songs))
            #     else:
            #         songs_info = song_list
            #         songs_features = self.features_analysis(songs_info, year, half_analyzed=0)
            #     songs_info = pd.read_csv("./temp/{}_{}_song_list.csv".format(year, num))
            # combine all 3 data frames to obtain songs, a dataframe which contains metadata for songs released in specified year.
            if stop_thread == "1":
                songs = pd.concat([songs_info, songs_analysis, songs_features], axis = 1)
                # save results to csv file
                songs.to_csv("./song_features/{}_{}_song_features.csv".format(year, num), index=False)
                # remove temp files on success
                if len(songs) != 0:
                    os.remove("./temp/{}_temp_audio_analysis.csv".format(year))
                    os.remove("./temp/{}_temp_features_analysis.csv".format(year))
                    os.remove("./temp/{}_{}_song_list.csv".format(year, num))
        except Exception as ex:
            print("")
            print("Error for scraping from year {} with num {} and exception: {}".format(year, num, ex))
            logging.exception(str(ex) + " (Year: {} - Num: {})".format(year, num))


    # ## Where it all begins

    # In[ ]:


    # edit the range values in the for loop to input the range of years to scrape from
    # edit the second parameter in the get_data function to input the number of songs to scrape from each year
    # edit the resume list to add or remove years which was half analyzed previously
    def begin(self):
        threading.Thread(target=self.check_state).start()
        global stop_thread
        stop_thread = "1"
        for year in range(2010, 2019):
            if stop_thread == "1":
                self.get_data(year, 200, resume=[])
            else:
                return None

    def check_state(self):
        mtime = os.stat("./settings/config.json").st_mtime
        cmtime = mtime
        while cmtime == mtime:
            sleep(0.01)
            mtime = os.stat("./settings/config.json").st_mtime
        global stop_thread
        stop_thread = "0"

