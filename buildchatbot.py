# coding: utf-8
#
# buildchatbot - Monitors Jenkins builds and sends notifications to a Skype chat
#
# Copyright (c) 2012 Mirko Nasato - All rights reserved.
# Licensed under the BSD 2-clause license; see LICENSE.txt
#
import platform
from time import sleep
from urllib import urlopen
from Skype4Py import Skype, errors
from xml.etree import ElementTree
from settings import *

class Build:
  def __init__(self, attrs):
    self.name = attrs['name']
    self.number = attrs['lastBuildLabel']
    self.status = attrs['lastBuildStatus']
    self.activity = attrs['activity']
  def __str__(self):
    return "{} - {} - {} - {}".format(self.name, self.number, self.status, self.activity)

class BuildMonitor:

  def __init__(self, listener):
    self.builds = None
    self.listener = listener

  def loop(self):
    while True:
      try:
        self.check_for_new_builds()
      except IOError as e:
        print 'WARNING! update failed:', e.strerror
      sleep(UPDATE_INTERVAL)

  def check_for_new_builds(self):
    builds = self.fetch_builds()
    if self.builds is not None:
      for build in builds.values():
        name = build.name
        if name in EXCLUDE:
          continue
        if not self.builds.has_key(name):
          self.handle_new_build(build, None)
        elif build.number != self.builds[name].number:
          self.handle_new_build(build, self.builds[name].status)
        if self.builds[name].activity != 'Building' and build.activity == 'Building':
          #increase build number, because Jenkins give only lastBuild
          build.number = str(int(build.number) + 1)
          self.listener.notify(build, 'Building')
    self.builds = builds

  def handle_new_build(self, build, old_status):
    transition = (old_status, build.status)
    if transition == ('Failure', 'Failure'):
      self.listener.notify(build, '(rain) Still failing')
    elif transition == ('Failure', 'Success'):
      self.listener.notify(build, '(sun) Fixed')
    elif build.status == 'Failure':
      self.listener.notify(build, '(rain) Failed')
    #elif transition == ('Success', 'Success'):
    #  self.listener.notify(build, '(sun) Success')

  def fetch_builds(self):
    builds = {}
    response = urlopen(JENKINS_URL +'/cc.xml')
    projects = ElementTree.parse(response).getroot()
    for project in projects.iter('Project'):
      build = Build(project.attrib)
      builds[build.name] = build
    return builds

class BuildNotifier:

  def __init__(self):
    if platform.system() == 'Windows':
      skype = Skype()
    else:
      skype = Skype(Transport='x11')
    skype.Attach()
    self.chat = None
    for chat in skype.RecentChats:
      if chat.FriendlyName == SKYPE_CHAT:
        self.chat = skype.Chat(chat.Name)
        break
    if(self.chat == None):
      raise errors.SkypeError(105, "Cannot find chat. Please, use listrecentchats.py for correct chat name")


  def notify(self, build, event):
    message = event +': '+ build.name +' - '+ JENKINS_URL +'/job/'+ build.name +'/'+ build.number +'/'
    print message
    self.chat.SendMessage(MESSAGE_PREFIX + message)

if __name__ == '__main__':
  try:
    BuildMonitor(BuildNotifier()).loop()
  except KeyboardInterrupt:
    pass
