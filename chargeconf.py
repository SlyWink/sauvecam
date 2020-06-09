#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import stat
import requests
import subprocess


DEBUG = 1
ESSAIS = 5
PAUSE = 30
HOSTNAME = os.uname()[1].upper()
DISTANT = 'https://raw.githubusercontent.com/SlyWink/sauvecam/master/'
LOCAL = '/tmp/picam/'
MSG_OK = ' -> OK'

SCRIPT_D = DISTANT + 'sauvecam.py'
SCRIPT_L = LOCAL + 'sauvecam.py'
CONFIG_D = DISTANT + HOSTNAME + '_motion.conf'
CONFIG_L = LOCAL + 'motion.conf'
MASQUE_D = DISTANT + HOSTNAME + '_masque.pgm.gz'
MASQUE_L = LOCAL + 'masque.pgm.gz'


def debug(msg):
  if DEBUG:
    print time.strftime("%d/%m/%y-%H:%M:%S",time.localtime()) + " - " + msg


def wget(inName, outName=''):
  r = requests.get(inName)
  if r.status_code == requests.codes.ok:
    open(outName , 'wb').write(r.content)
    return True
  return False


essai = 0

while essai < ESSAIS:
  essai += 1

  try:

    debug("Téléchargement " + SCRIPT_D + " en " + SCRIPT_L)
    if wget(SCRIPT_D,SCRIPT_L):
      debug(MSG_OK)
      os.chmod(SCRIPT_L,stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)

    debug("Téléchargement " + CONFIG_D + " en " + CONFIG_L)
    if wget(CONFIG_D,CONFIG_L):
      debug(MSG_OK)

    debug("Téléchargement " + MASQUE_D + " en " + MASQUE_L)
    if wget(MASQUE_D,MASQUE_L):
      debug(MSG_OK)
      subprocess.call(["/bin/gunzip",MASQUE_L])

    break

  except requests.exceptions.RequestException:
    debug("Anomalie téléchargement, nouvel essai dans %ds" % (PAUSE))
    time.sleep(PAUSE)
