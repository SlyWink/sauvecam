#!/usr/bin/python
# -*- coding: utf-8 -*-

#import pexpect
import glob
import os
import time
import sys
import stat
# Version modifiée comportant codes 204 et 501 si collection existe (ano 4shared)
sys.path.append('/home/pi/easywebdav-master_SL')
import easywebdav
import subprocess
import base64

DEBUG = 1
HOSTNAME = os.uname()[1].upper()
DISTANT = '/' + 'Config/'
LOCAL = '/tmp/picam/'

execfile('/home/pi/cloudconf.py')

def debug(msg):
  if DEBUG:
    print time.strftime("%d/%m/%y-%H:%M:%S",time.localtime()) + " - " + msg


time.sleep(5)

SCRIPT_D = DISTANT + 'sauvecam.py'
SCRIPT_L = LOCAL + 'sauvecam.py'
CONFIG_D = DISTANT + HOSTNAME + '_motion.conf'
CONFIG_L = LOCAL + 'motion.conf'
MASQUE_D = DISTANT + HOSTNAME + '_masque.pgm'
MASQUE_L = LOCAL + 'masque.pgm'

while True:

  try:
    # Paramétrage connexion webdav
    debug("Paramétrage connexion " + CLOUD)
    wd = easywebdav.connect(host=CLOUD,username=USERNAME,password=base64.decodestring(PASSWORD),protocol=PROTO)

    debug("Téléchargement " + SCRIPT_D + " en " + SCRIPT_L)
    wd.download(SCRIPT_D,SCRIPT_L)
    os.chmod(SCRIPT_L,stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

    debug("Téléchargement " + CONFIG_D + " en " + CONFIG_L)
    wd.download(CONFIG_D,CONFIG_L)

    if wd.exists(MASQUE_D):
      debug("Téléchargement " + MASQUE_D + " en " + MASQUE_L)
      wd.download(MASQUE_D,MASQUE_L)

    break

  except:
    debug("Anomalie téléchargement, nouvel essai dans 30s")
    time.sleep(30)
