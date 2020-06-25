#!/usr/bin/python
# -*- coding: utf-8 -*-

import glob
import os
import time
import sys
sys.path.append('/home/pi/easywebdav')
import easywebdav
import subprocess
import signal
import base64
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

DEBUG = True
HOSTNAME = os.uname()[1].upper()
CAPTURES = '/tmp/picam'
MAXFICH = 1000

execfile("/home/pi/cloudconf.py")

CONSERVER = 20 * 1024 * 1024
UPTIME_SEC = 5 * 60
TIMEOUT_SEC = 20

def debug(msg):
  if DEBUG:
    print time.strftime("%d/%m/%y-%H:%M:%S", time.localtime()) + " - " + msg

def uptime():
  with open('/proc/uptime', 'r') as f:
    seconds = float(f.readline().split()[0])
    return int(seconds)

def mailInfo():
  try:
    msg = MIMEMultipart()
    msg['From'] = FROM_ADDR
    msg['To'] = TO_ADDR
    subject = "Reboot" if (uptime() < UPTIME_SEC) else "Anomalie"
    msg['Subject'] = "[%s] -> %s" % (HOSTNAME, subject)
    body = "Voir ce qui se passe"
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP_SSL(SMTP_SRV)
    server.ehlo()
    server.login(SMTP_ID, base64.decodestring(SMTP_PWD))
    text = msg.as_string()
    server.sendmail(FROM_ADDR, TO_ADDR, text)
  except smtplib.SMTPException:
    pass

def dispo(path):
  stat = os.statvfs(path)
  return stat.f_bavail * stat.f_frsize


class MyWebdav:

  @staticmethod
  def _handler(signum, frame):
    print "** TIME OUT **"
    raise easywebdav.WebdavException("Time out")

  def __init__(self, wd):
    self._wd = wd
    self._fileCount = 0
    self._previousCollection = None
    self.lastTime = 0
    signal.signal(signal.SIGALRM, self.__class__._handler)

  def _path2Collection(self, filePath):
    fileName = os.path.basename(filePath)
    # Récupère la date du fichier et la mémorise si elle est plus récente
    # %v-%Y%m%d%H%M%S-%q
    fileTimestamp = fileName.split('-')[1]
    fileTime = time.mktime(time.strptime(fileTimestamp, "%Y%m%d%H%M%S"))
    if self.lastTime == 0 or self.lastTime < fileTime:
      self.lastTime = fileTime
    # Extrait le nom du répertoire destinataire
    fileDate = fileTimestamp[0:8]
    fileHour = int(fileTimestamp[8:10])
    collectionHour = "00-05"
    if fileHour >= 6:
      # Captures h et h+1 (h paire) dans le même répertoire
      evenHour = fileHour - fileHour % 2
      collectionHour = "%02d-%02d" % (evenHour, evenHour+1)
    return [fileDate, collectionHour, fileName]

  def upload(self, filePath):
    collectionItems = self._path2Collection(filePath)
    fileName = collectionItems.pop()
    collectionPath = "/" + HOSTNAME + "/" + collectionItems[0]
    signal.alarm(TIMEOUT_SEC)
    try:
      if collectionItems != self._previousCollection:
        self._fileCount = 0
        debug("Lecture contenu de la collection " + collectionPath)
        collectionRead = len(self._wd.ls(collectionPath))
        debug(" -> %d" % collectionRead)
        if collectionRead == 0:
          debug("Création de la collection " + collectionPath)
          self._wd.mkdir(collectionPath)
        else:
          index = 0
          while True:
            collectionSubPath = "%s/%s.%1d" % (collectionPath, collectionItems[1],index)
            debug("Lecture nombre de fichiers de la collection " + collectionSubPath)
            count = len(self._wd.ls(collectionSubPath))
            debug(" -> %d" % count)
            if count == 0:
              break
            else:
              self._fileCount += count -1
              index += 1
      collectionPath += "/%s.%1d" % (collectionItems[1], self._fileCount / MAXFICH)
      if self._fileCount % MAXFICH == 0:
        debug("Création de la collection " + collectionPath)
        self._wd.mkdir(collectionPath)
      remotePath = collectionPath + "/" + fileName
      debug("Transfert %s => %s (%d)" % (filePath, remotePath,self._fileCount))
      startTime = time.time()
      wd._wd.upload(filePath, remotePath)
      debug(" -> OK en %.2f s" % (time.time() - startTime))
      self._previousCollection = collectionItems
      self._fileCount += 1
      return True
    except easywebdav.WebdavException, texterr:
      debug("Anomalie WebDAV\n{}".format(texterr))
      return False
    finally:
      signal.alarm(0)



# Courriel d'avertissement
mailInfo()

# Paramétrage connexion webdav
debug("Paramétrage connexion " + CLOUD)
wd = MyWebdav(easywebdav.connect(host=CLOUD, username=USERNAME, password=base64.decodestring(PASSWORD), protocol=PROTO))

attente = True
startTime = time.time()
while True:

  photos = glob.glob(CAPTURES + '/[0-9]*.jpg')
  if photos:
    debug("Présence de photos")
    attente = True
    photos.sort()
    for path in photos:
      # Vérifie l'espace disque disponible
      if dispo(CAPTURES) < CONSERVER:
        debug("Plus de place, suppression photo " + path)
        os.remove(path)
      else:
        for tries in range(5):
          debug("Traitement " + path)
          if wd.upload(path):
            os.remove(path)
            break
  if attente:
    debug("En attente de captures")
    attente = False
  time.sleep(5)
  referenceTime = wd.lastTime if wd.lastTime > 0 else startTime
  if time.time() - referenceTime > 3630 :
    debug("Dernière photo antérieure à 1h05, redémarrage nécessaire")
    subprocess.call("/usr/bin/sudo /sbin/reboot", shell=True)
