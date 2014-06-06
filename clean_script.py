import logging
import sqlite3
import transmissionrpc
import glob
import datetime
import os

TRANSMISSION_PORT = 9092
TRANSMISSION_USER = 'pi'
TRANSMISSION_PASSWORD='pi'
XBMC_DATABASES_PATH = '/home/pi/.xbmc/userdata/Database'
DATA_PATH = '/media/KINGSTON/'
UPLOAD_RATIO_TH = 1.0
ADDED_TIME_TH = datetime.timedelta(days=40)
DISK_TH = 2.0 #GB (empty space)


#1-Get the list of existing torrents
logging.basicConfig(level=logging.DEBUG)
c = transmissionrpc.Client(port=TRANSMISSION_PORT,user=TRANSMISSION_USER,password=TRANSMISSION_PASSWORD)
existing_torrents = c.get_files()
existing_files = {};
for torrent_id in existing_torrents:
    t = c.get_torrent(torrent_id)
    files = t.files()
    for file_id in files:
        #existing_files[files[file_id]['name']] = {'id':torrent_id,'download_dir':t.downloadDir,'upload_ratio':t.uploadRatio,'added_date':datetime.datetime.fromtimestamp(int(t.addedDate))}
        existing_files[os.path.basename(files[file_id]['name'])] = {'file':files[file_id]['name'],'id':torrent_id,'download_dir':t.downloadDir,'upload_ratio':t.uploadRatio,'added_date':datetime.datetime.fromtimestamp(int(t.addedDate))}


logging.debug(existing_files)

#2-Get the list of watched files
xbmc_watched_files = [];
database_files = glob.glob(XBMC_DATABASES_PATH+'/MyVideos*.db')
for database in database_files:
    sc = sqlite3.connect(database)
    sqlitec = sc.cursor()
    sqlitec.execute("""select strFilename from episodeview where playCount > 0""")
    for row in sqlitec:
        xbmc_watched_files.append(row[0])

    sqlitec.execute("""select strFilename from movieview where playCount > 0""")
    for row in sqlitec:
        xbmc_watched_files.append(row[0])

xbmc_watched_files = set(xbmc_watched_files)#Remove duplicates
logging.debug(xbmc_watched_files)

#3-Check the watched and existing files. Make a planned clean.
no_torrent_files =[];#holds files that were watched but ther is no a torrent file
torrents_id_to_delete = [];
for watched_file in xbmc_watched_files:
    if existing_files.has_key(watched_file):
        if datetime.datetime.now()-existing_files[watched_file]['added_date']>ADDED_TIME_TH:
            #Delete file
            torrents_id_to_delete.append(existing_files[watched_file]['id'])

        elif existing_files[watched_file]['upload_ratio'] >=UPLOAD_RATIO_TH:
            #Delete file
            torrents_id_to_delete.append(existing_files[watched_file]['id'])
    else:
        no_torrent_files.append(watched_file)
		
logging.debug(torrents_id_to_delete)
logging.debug(no_torrent_files)

#4-Make a forced cleaning on watched shows. It will be done if the disk free space is less than the threshold
stat = os.statvfs(DATA_PATH)
free_space_gb = (stat.f_frsize * stat.f_bavail)/float(1024*1024*1024)
logging.info('Free space (GB):'+str(free_space_gb))
if free_space_gb<DISK_TH:
    logging.debug('Forced cleaning')

