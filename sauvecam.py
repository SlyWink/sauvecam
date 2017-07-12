#!/usr/bin/python
# -*- coding: utf-8 -*-

#import pexpect
import glob
import os
import time
import sys
# Version modifiée comportant codes 204 et 501 si collection existe (ano 4shared)
#sys.path.append('/home/steph/easywebdav-master_SL')
sys.path.append('/home/pi/easywebdav-master_SL')
import easywebdav
import subprocess
import signal

DEBUG = 1
DISTANT = '/' + os.uname()[1].upper()
CAPTURES = '/tmp/picam'
MAXFICH = 1000

execfile("/home/pi/cloudconf.py")

CONSERVER = 20 * 1024 * 1024

TRUE = 1
FALSE = 0

courant = ''
attente = 1
derdate = 0
cptphot = 0

def debug(msg):
  if DEBUG:
    print time.strftime("%d/%m/%y-%H:%M:%S",time.localtime()) + " - " + msg


def dispo(path):
  stat = os.statvfs(path)
  return stat.f_bavail * stat.f_frsize 

def handler(signum,frame):
  print "** TIME OUT **"
  raise easywebdav.WebdavException("Time out")

# Paramétrage connexion webdav
debug("Paramétrage connexion " + CLOUD)
wd = easywebdav.connect(host=CLOUD,username=USERNAME,password=PASSWORD,protocol=PROTO)

signal.signal(signal.SIGALRM,handler)
while TRUE:

  try:
    photos = glob.glob(CAPTURES + '/[0-9]*.jpg')
    if photos:
      debug("Présence de photos")
      attente = 1
      photos.sort()
      for path in photos:
        # Extrait le nom du fichier
        photo = os.path.basename(path)
        # Récupère la date du fichier et la mémorise si elle est plus récente
        # %v-%Y%m%d%H%M%S-%q
        datephot = photo.split('-')[1]
        datefich = time.mktime(time.strptime(datephot,"%Y%m%d%H%M%S"))
        if derdate == 0 or derdate < datefich:
          derdate = datefich
        # Vérifie l'espace disque disponible
        if dispo(CAPTURES) < CONSERVER:
          debug("Plus de place, suppression photo " + photo)
        else:
          debug("Traitement " + photo)
          # Extrait le nom du répertoire destinataire
          repdist_j = datephot[0:8]
          heure = int(datephot[8:10])
          repdist_h = ""
          if heure < 6:
            # Captures entre 00:00 et 05:59 dans le même répertoire
            repdist_h = "00-05"
          else:
            # Captures h et h+1 (h paire) dans le même répertoire
            hpaire = heure - heure % 2
            repdist_h = "%02d-%02d" % (hpaire,hpaire+1)
          repdist = repdist_j + '/' + repdist_h
          if courant[0:-2] <> repdist:
            cptphot = 0
          repdist += ".%1d" % (cptphot / MAXFICH)
          # 20 secondes maxi pour faire le transfert
          signal.alarm(20)
          # On vérifie si le répertoire a été traité récemment
          if repdist <> courant:
            # Vérifie l'existence du répertoire jour
            if not wd.exists(DISTANT + '/' + repdist_j):
              # Création du répertoire jour si inexistant
              debug("Création de la collection " + repdist_j)
              wd.mkdir(DISTANT + '/' + repdist_j)
            # Vérifie l'existence du répertoire jour+heure
            if not wd.exists(DISTANT + '/' + repdist):
              # Création du répertoire jour+heure si inexistant
              debug("Création de la collection " + repdist)
              wd.mkdir(DISTANT + '/' + repdist)
            courant = repdist
          debug("Transfert " + path + " => " + DISTANT + "/" + repdist)
          heure = time.time()
          wd.upload(path,DISTANT + '/' + repdist + '/' + photo)
          debug(" -> OK en %.2f s" % (time.time()-heure))
          cptphot += 1
          # Désactive l'alarme
          signal.alarm(0)
        os.remove(path)
  except easywebdav.WebdavException,texterr:
    debug("Anomalie WebDAV\n{}".format(texterr))
    courant = ''
    pass

  if attente:
    debug("En attente de captures")
    attente = 0
  time.sleep(5)
  if derdate > 0 and time.time()-derdate > 3630:
    debug("Dernière photo antérieure à 1h05, redémarrage nécessaire")
    subprocess.call("/usr/bin/sudo /sbin/reboot", shell=True)
